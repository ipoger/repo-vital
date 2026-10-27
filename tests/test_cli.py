"""Tests for the command line surface."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from repo_vital.cli import main


def run(*argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = main(list(argv))
    return code, buffer.getvalue()


class Cli(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_json_output_is_valid(self) -> None:
        code, output = run(str(self.root), "--json")
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["tool"], "repo-vital")
        self.assertEqual(payload["possible"], 100)
        self.assertEqual(payload["path"], str(self.root.resolve()))
        self.assertEqual(len(payload["checks"]), 12)

    def test_text_output_mentions_score(self) -> None:
        _, output = run(str(self.root), "--no-color")
        self.assertIn("Score", output)
        self.assertIn("0/100", output)

    def test_fail_under_returns_one(self) -> None:
        code, _ = run(str(self.root), "--fail-under", "50", "--no-color")
        self.assertEqual(code, 1)

    def test_fail_under_zero_never_fails(self) -> None:
        code, _ = run(str(self.root), "--no-color")
        self.assertEqual(code, 0)

    def test_missing_directory_returns_two(self) -> None:
        code, _ = run(str(self.root / "nope"), "--no-color")
        self.assertEqual(code, 2)

    def test_quiet_flag_disables_color_codes(self) -> None:
        _, output = run(str(self.root), "--no-color")
        self.assertNotIn("\033[", output)


if __name__ == "__main__":
    unittest.main()
