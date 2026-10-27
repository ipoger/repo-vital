# Contributing to repo-vital

Thanks for stopping by. This project is small on purpose, and every kind of
help is welcome — not just code.

## Ways to help

- **Report a gap**: a rule that should exist, or one that fires on a healthy
  repository.
- **Add a check**: each rule lives in `repo_vital/checks.py` and is usually
  under 30 lines.
- **Improve the wording**: the hint text is the product. If it reads like a
  linter, rewrite it.
- **Add a test**: every new check needs at least one pass and one fail case.
- **Translate**: a `README.zh-CN.md` is on the wish list.

## Set up

No dependencies are required beyond Python 3.9+.

```sh
git clone https://github.com/ipoger/repo-vital.git
cd repo-vital
python3 -m unittest discover -s tests -t . -v
python3 -m repo_vital .
```

Optional, if you want the `repo-vital` command on your PATH:

```sh
python3 -m pip install -e ".[dev]"
```

## What a good pull request looks like

1. **One change per pull request.** A new check plus its tests is one change.
2. **Tests come with it.** CI runs `unittest` on 3.9, 3.12 and 3.13, and then
   runs the tool against itself. If the repository no longer scores 100, the
   build fails — that is intentional.
3. **Explain the "why" in the description.** What was wrong before? Paste the
   before/after output if the change is visible.
4. **Keep the diff boring.** No drive-by reformatting, no renamed files.

## Adding a check

```python
def check_example(root: Path) -> Result:
    found = _find(root, ["EXAMPLE.md"])
    if found is None:
        return Result(FAIL, "say what a contributor should add")
    return Result(PASS, str(found.relative_to(root)))
```

Then register it in `CHECKS` with a weight, and make sure the weights still add
up to 100 — `tests/test_checks.py::Scoring::test_weights_add_up_to_one_hundred`
will tell you if they do not.

Guidelines for a rule that belongs here:

- A newcomer would notice its absence in the first five minutes.
- It can be decided from the working tree alone — no network, no guessing.
- It produces a specific next action, not "improve your docs".

## Review

I aim to respond within a few days. If you have not heard back after a week,
a polite ping on the pull request is welcome. Small PRs get merged fastest.
