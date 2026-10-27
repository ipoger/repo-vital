"""repo-vital — score a repository's contributor readiness.

The public surface is intentionally small: :func:`evaluate` returns a
:class:`Report` that the CLI renders. Checks are plain functions so they can
be tested against temporary directories without touching the filesystem.
"""

from .checks import CHECKS, Check, Report, Result, evaluate

__all__ = ["CHECKS", "Check", "Report", "Result", "evaluate", "__version__"]

__version__ = "0.1.0"
