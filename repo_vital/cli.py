"""Command line interface for repo-vital."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__
from .checks import FAIL, PASS, WARN, Report, evaluate

ICON = {PASS: "✔", WARN: "!", FAIL: "✘"}

COLORS = {
    PASS: "\033[32m",
    WARN: "\033[33m",
    FAIL: "\033[31m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

STATUS_LABEL = {PASS: "ok", WARN: "warn", FAIL: "missing"}


def _supports_color(stream) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return bool(getattr(stream, "isatty", lambda: False)())


class Painter:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def __call__(self, text: str, *styles: str) -> str:
        if not self.enabled:
            return text
        prefix = "".join(COLORS[style] for style in styles if style in COLORS)
        return f"{prefix}{text}{COLORS['reset']}"


def _render_text(report: Report, paint: Painter, show_next: bool = True) -> str:
    lines: List[str] = []
    lines.append(paint(f"repo-vital {__version__}", "bold") + paint("  contributor readiness report", "dim"))
    lines.append(paint(str(report.root), "dim"))
    lines.append("")

    width = max(len(check.title) for check, _ in report.items)
    for check, result in report.items:
        icon = paint(ICON[result.status], result.status)
        title = check.title.ljust(width)
        lines.append(f"  {icon}  {title}  {paint(result.detail, 'dim')}")

    lines.append("")
    score_line = f"Score {report.score}/100"
    band = report.band
    style = PASS if report.score >= 85 else WARN if report.score >= 40 else FAIL
    lines.append(
        "  "
        + paint(f"{score_line:>12}", "bold", style)
        + paint(f"   {band}", style)
        + paint(f"   ({report.earned:g}/{report.possible} points)", "dim")
    )

    if show_next and report.next_steps:
        lines.append("")
        lines.append("  " + paint("Next steps", "bold"))
        for index, (check, result) in enumerate(report.next_steps[:3], start=1):
            lines.append(f"  {index}. {paint(check.title, 'bold')}  {paint(f'+{check.weight} pts', 'dim')}")
            lines.append(f"     {check.hint}")
            if result.status == WARN:
                lines.append(paint(f"     currently: {result.detail}", "dim"))
    elif show_next:
        lines.append("")
        lines.append("  " + paint("Nothing left to fix. Ship it.", PASS))

    return "\n".join(lines)


def _render_json(report: Report) -> str:
    payload = {
        "tool": "repo-vital",
        "version": __version__,
        "path": str(report.root),
        "score": report.score,
        "band": report.band,
        "earned": report.earned,
        "possible": report.possible,
        "checks": [
            {
                "id": check.id,
                "title": check.title,
                "status": result.status,
                "weight": check.weight,
                "points": check.weight * (1.0 if result.status == PASS else 0.5 if result.status == WARN else 0.0),
                "detail": result.detail,
                "hint": check.hint,
            }
            for check, result in report.items
        ],
        "next": [
            {"id": check.id, "title": check.title, "points": check.weight, "hint": check.hint}
            for check, _ in report.next_steps
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-vital",
        description="Score a repository's contributor readiness and get a prioritized to-do list.",
        epilog="Exit codes: 0 = scanned, 1 = score below --fail-under, 2 = usage error.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="repository to scan (default: current directory)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--fail-under",
        type=int,
        default=0,
        metavar="N",
        help="exit with status 1 when the score is below N (default: 0, never fail)",
    )
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument("--version", action="version", version=f"repo-vital {__version__}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not 0 <= args.fail_under <= 100:
        parser.error("--fail-under must be between 0 and 100")

    try:
        report = evaluate(args.path)
    except NotADirectoryError as exc:
        print(f"repo-vital: {exc}", file=sys.stderr)
        return 2

    use_color = not args.no_color and not args.json and _supports_color(sys.stdout)
    if args.json:
        print(_render_json(report))
    else:
        print(_render_text(report, Painter(use_color)))

    if report.score < args.fail_under:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
