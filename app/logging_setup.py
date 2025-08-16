# app/logging_setup.py
from __future__ import annotations
import logging
from typing import Callable, Mapping, Any

try:
    from systemd.journal import JournalHandler  # apt: python3-systemd
    _HAS_JOURNAL = True
except Exception:
    _HAS_JOURNAL = False


def configure_logging(
    level: str = "INFO",
    service_name: str = "photo-resizer",
    to_stderr: bool = True,
    to_journal: bool = True,
) -> Callable[[str, Mapping[str, Any] | None], logging.Logger]:
    """
    Configure logging once and return a factory that builds child loggers:
      make_logger("converter", {"profile": "home"})
    """
    root = logging.getLogger(service_name)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.propagate = False

    if not root.handlers:
        if to_journal and _HAS_JOURNAL:
            jh = JournalHandler(SYSLOG_IDENTIFIER=service_name)
            jh.setLevel(root.level)
            # journald already timestamps; keep concise message
            jh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            root.addHandler(jh)

        if to_stderr:
            sh = logging.StreamHandler()
            sh.setLevel(root.level)
            sh.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s"
            ))
            root.addHandler(sh)

    # factory: returns a child logger; if ctx is provided, wrap in LoggerAdapter
    def make_logger(child: str = "", ctx: Mapping[str, Any] | None = None) -> logging.Logger:
        base = root if not child else root.getChild(child)
        if ctx:
            return logging.LoggerAdapter(base, extra=dict(ctx))  # type: ignore[return-value]
        return base

    return make_logger
