# repo-vital

English | [中文](README.zh-CN.md)

[![CI](https://github.com/ipoger/repo-vital/actions/workflows/ci.yml/badge.svg)](https://github.com/ipoger/repo-vital/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

**Score a repository's contributor readiness, then get a to-do list ordered by impact.**

A stranger lands on your project. Within five minutes they decide whether to
stay. repo-vital reads the working tree and tells you what that stranger is
missing — a license, a CI workflow, tests, an issue template — and which gap
costs you the most credibility.

No config files. No network calls. One command.

## Demo

```console
$ repo-vital /path/to/tiny-log

repo-vital 0.1.0  contributor readiness report
/path/to/tiny-log

  !  README              README.md is only 155 B
  ✔  License             MIT (LICENSE)
  ✘  Tests               no test files found
  ✘  CI                  no CI configuration — nothing verifies contributions
  ✘  Contributing guide  no CONTRIBUTING guide — newcomers do not know how to start
  ✔  Recent activity     committed today
  ✔  Package manifest    pyproject.toml
  ✔  Description         pyproject.toml: Structured logs for scripts, in one function.
  ✘  Code of conduct     no code of conduct
  ✔  Gitignore           2 rules
  ✘  Issue templates     no issue template — reports arrive incomplete
  ✘  PR template         no pull request template

  Score 42/100   Needs work   (42.5/100 points)

  Next steps
  1. README  +15 pts
     Explain what it is, why it matters, and how to run it.
     currently: README.md is only 155 B
  2. Tests  +15 pts
     Tests are what let a stranger change code without fear.
  3. CI  +15 pts
     Run tests automatically on every pull request.
```

## Install

repo-vital has no dependencies beyond Python 3.9+.

```sh
pip install repo-vital
```

Or run it straight from a checkout:

```sh
git clone https://github.com/ipoger/repo-vital.git
cd repo-vital
python3 -m repo_vital .
```

## Usage

```sh
repo-vital                 # scan the current directory
repo-vital path/to/repo    # scan somewhere else
repo-vital --json          # machine-readable output
repo-vital --fail-under 80 # exit 1 if the score is below 80
```

### Use it as a CI gate

```yaml
- name: Check contributor readiness
  run: |
    pip install repo-vital
    repo-vital . --no-color --fail-under 80
```

`--json` emits the score, every individual check, and the next steps, so you can
feed it into a dashboard or a bot:

```json
{
  "tool": "repo-vital",
  "score": 42,
  "band": "Needs work",
  "checks": [{ "id": "readme", "status": "warn", "weight": 15, "detail": "..." }],
  "next": [{ "id": "readme", "points": 15, "hint": "..." }]
}
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Scanned successfully (and met `--fail-under`, if given) |
| `1` | Score is below `--fail-under` |
| `2` | Usage error, or the path is not a directory |

## What it checks

Every rule is decidable from the working tree alone. Weights sum to 100.

| Rule | Weight | Passes when |
| --- | --- | --- |
| README | 15 | A README over 400 characters mentions install, usage or quick start |
| License | 15 | A `LICENSE`/`COPYING` file whose text matches a known license |
| Tests | 15 | At least 5 test cases live under a dedicated `tests/` directory |
| CI | 15 | A workflow exists under `.github/workflows/`, or another common CI file |
| Contributing guide | 10 | `CONTRIBUTING.md` mentions tests, issues, PRs, style or lint |
| Recent activity | 5 | The last commit is under 180 days old |
| Package manifest | 5 | `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, … exists |
| Description | 5 | The manifest carries a description longer than 12 characters |
| Code of conduct | 5 | `CODE_OF_CONDUCT.md` exists |
| Gitignore | 5 | `.gitignore` has at least two rules |
| Issue templates | 3 | `.github/ISSUE_TEMPLATE/` holds at least one file |
| PR template | 2 | `.github/pull_request_template.md` exists |

## How scoring works

- **pass** earns the full weight, **warn** earns half, **missing** earns nothing.
- Bands: `85+` Great, `65–84` Good, `40–64` Needs work, below that Just getting started.
- Warnings exist for the honest middle: a README that exists but says nothing,
  tests scattered outside a `tests/` directory, a dormant project.

Weights are opinionated on purpose. A license and tests are worth three times a
PR template, because they change whether someone *can* contribute at all.

## Design principles

1. **Offline and deterministic.** Same tree in, same score out. No API calls, no
   badge scraping, no guessing about stars.
2. **Zero configuration.** If a rule needs a config file to be useful, it is the
   wrong rule for a five-minute check.
3. **Advice, not judgement.** Every failure names the next action. A score
   without a next step is just a linter with extra steps.

## Roadmap

- [ ] `README.zh-CN.md`
- [ ] `--fix` for the mechanical gaps (scaffold `LICENSE`, templates, workflow)
- [ ] Per-language rule packs (Go, Rust, TypeScript)
- [ ] GitHub Action wrapper that comments the score on pull requests

Have a rule idea? Open a [Rule idea](https://github.com/ipoger/repo-vital/issues/new?template=rule_idea.yml)
issue — the template asks the only three questions that matter.

## Contributing

Contributions of every size are welcome, including wording fixes. Start with
[CONTRIBUTING.md](CONTRIBUTING.md), and note that CI runs the tool against this
repository: if the score drops below 100, the build fails.

## License

[MIT](LICENSE) © 2026 ipoger
