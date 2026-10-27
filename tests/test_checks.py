"""Unit tests for the rule set."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from repo_vital import checks
from repo_vital.checks import FAIL, PASS, WARN, evaluate


README_BODY = """# demo

A tiny demo project used by the test suite to prove that a well documented
repository reaches a perfect score. This paragraph is intentionally long
enough to clear the minimum length threshold.

## Install

```
pip install demo
```

## Usage

```
demo --help
```

## Contributing

Issues and pull requests are welcome. Please read CONTRIBUTING.md first, run
the test suite locally, and keep each pull request focused on a single change
so that review stays quick and the history stays readable.

## License

MIT. See LICENSE for details.
"""


def write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TempRepo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)


class ReadmeCheck(TempRepo):
    def test_missing_readme_fails(self) -> None:
        self.assertEqual(checks.check_readme(self.root).status, FAIL)

    def test_tiny_readme_warns(self) -> None:
        write(self.root, "README.md", "# hi\n")
        self.assertEqual(checks.check_readme(self.root).status, WARN)

    def test_readme_with_install_section_passes(self) -> None:
        write(self.root, "README.md", README_BODY)
        self.assertEqual(checks.check_readme(self.root).status, PASS)

    def test_long_readme_without_usage_warns(self) -> None:
        write(self.root, "README.md", "# demo\n\n" + "word " * 200)
        self.assertEqual(checks.check_readme(self.root).status, WARN)


class LicenseCheck(TempRepo):
    def test_missing_license_fails(self) -> None:
        self.assertEqual(checks.check_license(self.root).status, FAIL)

    def test_mit_license_is_recognized(self) -> None:
        write(self.root, "LICENSE", "MIT License\n\nCopyright (c) 2026 someone\n")
        result = checks.check_license(self.root)
        self.assertEqual(result.status, PASS)
        self.assertIn("MIT", result.detail)

    def test_license_declared_only_in_manifest_warns(self) -> None:
        write(self.root, "pyproject.toml", '[project]\nname = "x"\nlicense = "MIT"\n')
        self.assertEqual(checks.check_license(self.root).status, WARN)


class DescriptionCheck(TempRepo):
    def test_reads_pyproject(self) -> None:
        write(
            self.root,
            "pyproject.toml",
            '[project]\nname = "x"\ndescription = "Checks repositories for contributor readiness."\n',
        )
        self.assertEqual(checks.check_description(self.root).status, PASS)

    def test_reads_package_json(self) -> None:
        write(self.root, "package.json", '{"name": "x", "description": "A useful little tool"}')
        self.assertEqual(checks.check_description(self.root).status, PASS)

    def test_missing_manifest_fails(self) -> None:
        self.assertEqual(checks.check_description(self.root).status, FAIL)


class TestsCheck(TempRepo):
    def test_no_tests_fails(self) -> None:
        self.assertEqual(checks.check_tests(self.root).status, FAIL)

    def test_many_tests_in_directory_pass(self) -> None:
        for name in ("test_a.py", "test_b.py", "test_c.py"):
            write(self.root, f"tests/{name}", "def test_one():\n    assert True\n\ndef test_two():\n    assert True\n")
        self.assertEqual(checks.check_tests(self.root).status, PASS)

    def test_scattered_tests_warn(self) -> None:
        for name in ("test_a.py", "test_b.py", "test_c.py"):
            write(self.root, name, "def test_one():\n    assert True\n\ndef test_two():\n    assert True\n")
        self.assertEqual(checks.check_tests(self.root).status, WARN)

    def test_node_modules_is_ignored(self) -> None:
        write(self.root, "node_modules/pkg/test_thing.py", "def test():\n    pass\n")
        self.assertEqual(checks.check_tests(self.root).status, FAIL)


class CiCheck(TempRepo):
    def test_missing_ci_fails(self) -> None:
        self.assertEqual(checks.check_ci(self.root).status, FAIL)

    def test_github_workflow_passes(self) -> None:
        write(self.root, ".github/workflows/ci.yml", "on: push\njobs: {}\n")
        self.assertEqual(checks.check_ci(self.root).status, PASS)

    def test_empty_workflows_dir_fails(self) -> None:
        (self.root / ".github" / "workflows").mkdir(parents=True)
        self.assertEqual(checks.check_ci(self.root).status, FAIL)


class GitignoreCheck(TempRepo):
    def test_missing_gitignore_fails(self) -> None:
        self.assertEqual(checks.check_gitignore(self.root).status, FAIL)

    def test_two_rules_pass(self) -> None:
        write(self.root, ".gitignore", "__pycache__/\n*.pyc\n")
        self.assertEqual(checks.check_gitignore(self.root).status, PASS)

    def test_single_rule_warns(self) -> None:
        write(self.root, ".gitignore", "*.log\n")
        self.assertEqual(checks.check_gitignore(self.root).status, WARN)


class ActivityCheck(TempRepo):
    def test_non_git_tree_fails(self) -> None:
        self.assertEqual(checks.check_recent_activity(self.root).status, FAIL)

    def test_fresh_repository_passes(self) -> None:
        git(self.root, "init")
        git(self.root, "add", "-A")
        git(self.root, "commit", "--allow-empty", "-m", "init")
        self.assertEqual(checks.check_recent_activity(self.root).status, PASS)


class Scoring(unittest.TestCase):
    def test_empty_repository_scores_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate(tmp)
        self.assertEqual(report.possible, 100)
        self.assertEqual(report.score, 0)
        self.assertEqual(report.band, "Just getting started")

    def test_warning_counts_half_points(self) -> None:
        check = checks.Check("x", "X", 10, "hint", lambda root: checks.Result(WARN, "w"))
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate(tmp, checks=[check])
        self.assertEqual(report.earned, 5)
        self.assertEqual(report.score, 50)

    def test_weights_add_up_to_one_hundred(self) -> None:
        self.assertEqual(sum(check.weight for check in checks.CHECKS), 100)

    def test_next_steps_are_sorted_by_weight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate(tmp)
        weights = [check.weight for check, _ in report.next_steps]
        self.assertEqual(weights, sorted(weights, reverse=True))


class CompleteRepo(TempRepo):
    """A repository that satisfies every rule — the dogfood case."""

    def setUp(self) -> None:
        super().setUp()
        write(self.root, "README.md", README_BODY)
        write(self.root, "LICENSE", "MIT License\n\nCopyright (c) 2026\n")
        write(self.root, "CONTRIBUTING.md", "Run the tests. Open a pull request. Keep the style.\n")
        write(self.root, "CODE_OF_CONDUCT.md", "# Code of conduct\n\nBe kind.\n")
        write(self.root, ".gitignore", "__pycache__/\n*.pyc\n")
        write(self.root, ".github/workflows/ci.yml", "on: push\njobs: {}\n")
        write(self.root, ".github/ISSUE_TEMPLATE/bug.yml", "name: Bug\n")
        write(self.root, ".github/pull_request_template.md", "## What changed\n")
        write(
            self.root,
            "pyproject.toml",
            '[project]\nname = "demo"\ndescription = "A demo repository for the test suite."\n',
        )
        for name in ("test_a.py", "test_b.py", "test_c.py"):
            write(
                self.root,
                f"tests/{name}",
                "def test_ok():\n    assert True\n\ndef test_also_ok():\n    assert True\n",
            )
        git(self.root, "init")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-m", "init")

    def test_every_check_passes(self) -> None:
        report = evaluate(self.root)
        failed = [(c.id, r.status, r.detail) for c, r in report.items if r.status != PASS]
        self.assertEqual(failed, [])
        self.assertEqual(report.score, 100)
        self.assertEqual(report.band, "Great")


def git(root: Path, *args: str) -> None:
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME="repo-vital tests",
        GIT_AUTHOR_EMAIL="tests@example.com",
        GIT_COMMITTER_NAME="repo-vital tests",
        GIT_COMMITTER_EMAIL="tests@example.com",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
    )
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env=env,
    )


if __name__ == "__main__":
    unittest.main()
