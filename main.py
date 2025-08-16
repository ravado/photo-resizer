from __future__ import annotations
import argparse
import os

from app.config import (
    LOCATIONS, BASE, EXTS, RESIZE_WIDTH, RESIZE_HEIGHT,
    IM_QUALITY, DB_PATH, TIMEOUT_SECS
)
from app.planner import Planner
from app.imaging import ImageEngine
from app.converter import Converter
from app.logging_setup import configure_logging  # <- add this module as shown earlier


def parse_args():
    ap = argparse.ArgumentParser(description="Convert (or skip by hash) + log to SQLite.")
    ap.add_argument("location", choices=list(LOCATIONS.keys()), nargs="?", default="home")
    ap.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        help="Logging verbosity (default: %(default)s)",
    )
    return ap.parse_args()


def main():
    args = parse_args()

    # one-time logging setup; returns a logger factory
    make_logger = configure_logging(
        level=args.log_level,
        service_name="photo-resizer",
        to_stderr=True,
        to_journal=True,
    )

    planner = Planner(BASE, LOCATIONS, EXTS)
    engine = ImageEngine(timeout=TIMEOUT_SECS, quality=IM_QUALITY)

    # pass the factory into your classes (Converter updated to accept make_logger=)
    Converter(planner, engine, DB_PATH, make_logger=make_logger).run(args.location)


if __name__ == "__main__":
    main()
