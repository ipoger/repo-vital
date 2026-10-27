"""The rule set.

Every check is a pure function of a repository root: it reads files (and
optionally git metadata) and returns a :class:`Result`. Pure checks are easy
to unit test against a temporary directory, and easy to reason about when the
score looks wrong.

Rules of thumb for adding a check:

* It must describe something a *contributor* would notice in the first five
  minutes.
* It must be decidable from the working tree alone — no network calls, no
  guesses about the project's popularity.
* It must produce a specific hint, not "improve your docs".
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Sequence, Tuple

PASS = "pass"
WARN = "warn"
FAIL = "fail"

#: Multiplier applied to a check's weight for each status.
FACTOR = {PASS: 1.0, WARN: 0.5, FAIL: 0.0}

#: Directories that never contain first-party project files.
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "dist",
    "build",
    "target",
    ".next",
    "vendor",
}

TEXT_SUFFIXES = {".md", ".rst", ".txt", ".toml", ".json", ".yml", ".yaml"}


@dataclass(frozen=True)
class Result:
    """Outcome of a single check."""

    status: str
    detail: str

    def __post_init__(self) -> None:
        if self.status not in FACTOR:
            raise ValueError(f"unknown status: {self.status!r}")


@dataclass(frozen=True)
class Check:
    """A named, weighted rule."""

    id: str
    title: str
    weight: int
    hint: str
    run: Callable[[Path], Result]

    def evaluate(self, root: Path) -> Tuple["Check", Result]:
        try:
            result = self.run(root)
        except OSError as exc:  # unreadable tree: report, never crash the run
            result = Result(FAIL, f"could not read repository: {exc}")
        return self, result


@dataclass
class Report:
    """The full result of scanning one repository."""

    root: Path
    items: List[Tuple[Check, Result]] = field(default_factory=list)

    @property
    def possible(self) -> int:
        return sum(check.weight for check, _ in self.items)

    @property
    def earned(self) -> float:
        return sum(check.weight * FACTOR[res.status] for check, res in self.items)

    @property
    def score(self) -> int:
        if not self.possible:
            return 0
        return round(100 * self.earned / self.possible)

    @property
    def band(self) -> str:
        score = self.score
        if score >= 85:
            return "Great"
        if score >= 65:
            return "Good"
        if score >= 40:
            return "Needs work"
        return "Just getting started"

    @property
    def next_steps(self) -> List[Tuple[Check, Result]]:
        """Unfinished checks, most points left on the table first."""
        pending = [(c, r) for c, r in self.items if r.status != PASS]
        return sorted(pending, key=lambda item: -item[0].weight)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _find(root: Path, names: Sequence[str]) -> Path | None:
    for name in names:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def _first_line(text: str, limit: int = 120) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:limit]
    return ""


def _read(path: Path, limit: int = 200_000) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _walk_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            yield Path(dirpath) / filename


def _human_size(num: int) -> str:
    if num < 1024:
        return f"{num} B"
    if num < 1024 * 1024:
        return f"{num / 1024:.1f} KB"
    return f"{num / (1024 * 1024):.1f} MB"


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------


def check_readme(root: Path) -> Result:
    found = _find(root, ["README.md", "README.rst", "README.txt", "readme.md", "Readme.md"])
    if found is None:
        return Result(FAIL, "no README found")
    text = _read(found)
    size = len(text)
    if size == 0:
        return Result(FAIL, f"{found.name} is empty")
    if size < 400:
        return Result(WARN, f"{found.name} is only {_human_size(size)}")
    lowered = text.lower()
    if "install" not in lowered and "usage" not in lowered and "quick start" not in lowered:
        return Result(WARN, f"{found.name} has no install/usage section")
    return Result(PASS, f"{found.name} ({_human_size(size)})")


LICENSE_SIGNATURES: Sequence[Tuple[str, str]] = (
    ("MIT", "mit license"),
    ("Apache-2.0", "apache license"),
    ("GPL", "gnu general public license"),
    ("LGPL", "gnu lesser general public license"),
    ("MPL-2.0", "mozilla public license"),
    ("BSD", "redistribution and use in source and binary forms"),
    ("Unlicense", "this is free and unencumbered software released into the public domain"),
)


def check_license(root: Path) -> Result:
    found = _find(
        root,
        ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md", "LICENCE"],
    )
    if found is None:
        # A license declared only in a manifest still tells contributors something.
        declared = _manifest_license(root)
        if declared:
            return Result(WARN, f"declared as {declared} in the manifest, but no LICENSE file")
        return Result(FAIL, "no LICENSE file — contributors cannot legally reuse the code")
    head = _read(found, 6000).lower()
    for name, signature in LICENSE_SIGNATURES:
        if signature in head:
            return Result(PASS, f"{name} ({found.name})")
    return Result(WARN, f"{found.name} present, but the license could not be identified")


def _manifest_license(root: Path) -> str | None:
    pyproject = _find(root, ["pyproject.toml"])
    if pyproject:
        match = re.search(r'^\s*license\s*=\s*["{]\s*(?:text\s*=\s*)?["\']?([^"\'\n}]+)', _read(pyproject), re.M)
        if match:
            return match.group(1).strip()
    package_json = _find(root, ["package.json"])
    if package_json:
        match = re.search(r'"license"\s*:\s*"([^"]+)"', _read(package_json))
        if match:
            return match.group(1)
    return None


def check_description(root: Path) -> Result:
    pyproject = _find(root, ["pyproject.toml"])
    if pyproject:
        match = re.search(r'^\s*description\s*=\s*["\'](.+?)["\']\s*$', _read(pyproject), re.M)
        if match:
            return _judge_description(match.group(1), "pyproject.toml")
    package_json = _find(root, ["package.json"])
    if package_json:
        match = re.search(r'"description"\s*:\s*"([^"]+)"', _read(package_json))
        if match:
            return _judge_description(match.group(1), "package.json")
    cargo = _find(root, ["Cargo.toml"])
    if cargo:
        match = re.search(r'^\s*description\s*=\s*"(.+?)"', _read(cargo), re.M)
        if match:
            return _judge_description(match.group(1), "Cargo.toml")
    return Result(FAIL, "no package manifest description — search results will be blank")


def _judge_description(text: str, source: str) -> Result:
    text = text.strip()
    if len(text) < 12:
        return Result(WARN, f"{source} description is too short ({len(text)} chars)")
    return Result(PASS, f"{source}: {text[:60]}")


def check_contributing(root: Path) -> Result:
    found = _find(
        root,
        [
            "CONTRIBUTING.md",
            "CONTRIBUTING.rst",
            "CONTRIBUTING.txt",
            ".github/CONTRIBUTING.md",
            "docs/CONTRIBUTING.md",
        ],
    )
    if found is None:
        return Result(FAIL, "no CONTRIBUTING guide — newcomers do not know how to start")
    text = _read(found)
    lowered = text.lower()
    signals = ["test", "pull request", "issue", "style", "lint"]
    missing = [word for word in signals if word not in lowered]
    if len(missing) >= 3:
        return Result(WARN, f"{found.name} exists but never mentions: {', '.join(missing)}")
    return Result(PASS, str(found.relative_to(root)))


def check_code_of_conduct(root: Path) -> Result:
    found = _find(
        root,
        [
            "CODE_OF_CONDUCT.md",
            ".github/CODE_OF_CONDUCT.md",
            "CODE_OF_CONDUCT.rst",
            "docs/CODE_OF_CONDUCT.md",
        ],
    )
    if found is None:
        return Result(FAIL, "no code of conduct")
    return Result(PASS, str(found.relative_to(root)))


def check_gitignore(root: Path) -> Result:
    found = _find(root, [".gitignore"])
    if found is None:
        return Result(FAIL, "no .gitignore — build artifacts will end up in commits")
    lines = [line for line in _read(found).splitlines() if line.strip() and not line.startswith("#")]
    if len(lines) < 2:
        return Result(WARN, f".gitignore only has {len(lines)} rule(s)")
    return Result(PASS, f"{len(lines)} rules")


TEST_CASE_RE = re.compile(
    r"^\s*(?:async\s+)?def\s+test|^\s*it\(|^\s*test\(|^\s*func\s+Test|^\s*@Test",
    re.M,
)

TEST_PATTERNS = (
    re.compile(r"^test_.*\.py$"),
    re.compile(r"^.*_test\.py$"),
    re.compile(r"^.*\.test\.(js|ts|tsx|jsx)$"),
    re.compile(r"^.*\.spec\.(js|ts|tsx|jsx)$"),
    re.compile(r"^.*_test\.go$"),
    re.compile(r"^.*_spec\.rb$"),
)


def check_tests(root: Path) -> Result:
    files: List[Path] = []
    for path in _walk_files(root):
        if any(pattern.match(path.name) for pattern in TEST_PATTERNS):
            files.append(path)
            if len(files) >= 100:
                break
    if not files:
        return Result(FAIL, "no test files found")

    cases = 0
    for path in files:
        cases += len(TEST_CASE_RE.findall(_read(path, 200_000)))
    if cases == 0:
        cases = len(files)  # file names alone still signal intent

    has_dir = any(
        part in {"tests", "test", "spec", "__tests__"} for path in files for part in path.parts
    )
    summary = f"{cases} test case(s) in {len(files)} file(s)"
    if cases < 5:
        return Result(WARN, f"only {summary}")
    if not has_dir:
        return Result(WARN, f"{summary}, but no dedicated tests/ directory")
    return Result(PASS, f"{summary} under tests/")


CI_FILES = (
    ".gitlab-ci.yml",
    ".travis.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    ".circleci/config.yml",
)


def check_ci(root: Path) -> Result:
    workflows = root / ".github" / "workflows"
    if workflows.is_dir():
        files = [
            path
            for path in workflows.iterdir()
            if path.suffix.lower() in {".yml", ".yaml"} and path.is_file()
        ]
        if files:
            names = ", ".join(sorted(path.name for path in files)[:3])
            return Result(PASS, f"{len(files)} workflow(s): {names}")
        return Result(FAIL, ".github/workflows exists but holds no workflow files")
    for relative in CI_FILES:
        if (root / relative).is_file():
            return Result(PASS, relative)
    return Result(FAIL, "no CI configuration — nothing verifies contributions")


def check_issue_templates(root: Path) -> Result:
    templates = root / ".github" / "ISSUE_TEMPLATE"
    if templates.is_dir():
        files = [path for path in templates.iterdir() if path.is_file()]
        if files:
            return Result(PASS, f"{len(files)} template(s)")
        return Result(FAIL, ".github/ISSUE_TEMPLATE exists but is empty")
    for relative in (".github/issue_template.md", ".github/ISSUE_TEMPLATE.md", "docs/issue_template.md"):
        if (root / relative).is_file():
            return Result(PASS, relative)
    return Result(FAIL, "no issue template — reports arrive incomplete")


def check_pr_template(root: Path) -> Result:
    found = _find(
        root,
        [
            ".github/pull_request_template.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/PULL_REQUEST_TEMPLATE/pull_request_template.md",
            "docs/pull_request_template.md",
        ],
    )
    if found is None:
        return Result(FAIL, "no pull request template")
    return Result(PASS, found.name)


def check_recent_activity(root: Path) -> Result:
    if not (root / ".git").exists():
        return Result(FAIL, "not a git repository — there is nowhere to receive contributions")
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%ct"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Result(WARN, f"could not read git history: {exc}")
    stamp = completed.stdout.strip()
    if not stamp:
        return Result(WARN, "git repository has no commits yet")
    days = (time.time() - int(stamp)) / 86_400
    if days > 365:
        return Result(WARN, f"last commit was {int(days)} days ago")
    if days > 180:
        return Result(WARN, f"last commit was {int(days)} days ago — looks dormant")
    if days < 1:
        return Result(PASS, "committed today")
    return Result(PASS, f"last commit {int(days)} day(s) ago")


MANIFESTS = (
    "pyproject.toml",
    "setup.py",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "pom.xml",
    "build.gradle",
    "composer.json",
    "mix.exs",
)


def check_manifest(root: Path) -> Result:
    for name in MANIFESTS:
        if (root / name).is_file():
            return Result(PASS, name)
    return Result(FAIL, "no package manifest — contributors cannot install or build it")


CHECKS: Sequence[Check] = (
    Check("readme", "README", 15, "Explain what it is, why it matters, and how to run it.", check_readme),
    Check("license", "License", 15, "Pick a license so others can legally use and improve the code.", check_license),
    Check("tests", "Tests", 15, "Tests are what let a stranger change code without fear.", check_tests),
    Check("ci", "CI", 15, "Run tests automatically on every pull request.", check_ci),
    Check("contributing", "Contributing guide", 10, "Say how to set up, what to work on, and what a good PR looks like.", check_contributing),
    Check("activity", "Recent activity", 5, "A commit in the last few months signals the project is alive.", check_recent_activity),
    Check("manifest", "Package manifest", 5, "Make the project installable with one command.", check_manifest),
    Check("description", "Description", 5, "One sentence that shows up in search results and package indexes.", check_description),
    Check("conduct", "Code of conduct", 5, "Set expectations for behaviour before you need them.", check_code_of_conduct),
    Check("gitignore", "Gitignore", 5, "Keep build output and secrets out of the repository.", check_gitignore),
    Check("issues", "Issue templates", 3, "Ask for the details you always end up requesting.", check_issue_templates),
    Check("pr", "PR template", 2, "Remind contributors what a reviewable change looks like.", check_pr_template),
)


def evaluate(root: Path | str, checks: Sequence[Check] = CHECKS) -> Report:
    """Run every check against ``root`` and return the aggregated report."""

    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(f"not a directory: {root_path}")
    report = Report(root=root_path)
    for check in checks:
        report.items.append(check.evaluate(root_path))
    return report
