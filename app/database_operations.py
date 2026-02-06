from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional

_SCHEMA = """
DROP INDEX IF EXISTS ux_conversions_src_hash;

CREATE TABLE IF NOT EXISTS conversions (
  id INTEGER PRIMARY KEY,
  converted_at INTEGER NOT NULL,
  status TEXT NOT NULL,                    -- SUCCESS | FAILED | SKIPPED_DUP | ALREADY_DONE
  src_name TEXT NOT NULL,
  src_ext TEXT NOT NULL,
  src_fullpath TEXT NOT NULL,
  dst_fullpath TEXT,
  src_hash TEXT,
  orig_width INTEGER,
  orig_height INTEGER,
  new_width INTEGER,
  new_height INTEGER,
  out_size_bytes INTEGER,
  duration_ms INTEGER,
  im_mode TEXT,
  im_args TEXT,
  error TEXT,
  src_size INTEGER,
  src_mtime INTEGER,
  saved_percent INTEGER,                   -- e.g. 90 (means 90% saved)
  saved_mb REAL,                           -- e.g. 9.25 (MB saved)
  last_checked_at INTEGER                  -- Timestamp of last verification
);
CREATE INDEX IF NOT EXISTS idx_conversions_src_hash ON conversions(src_hash);
CREATE INDEX IF NOT EXISTS idx_conversions_src_path ON conversions(src_fullpath);
CREATE INDEX IF NOT EXISTS idx_conversions_when ON conversions(converted_at);
CREATE INDEX IF NOT EXISTS idx_hash_dst ON conversions(src_hash, dst_fullpath);
"""

_INSERT_SQL = """
INSERT INTO conversions (
  converted_at, status, src_name, src_ext, src_fullpath, dst_fullpath,
  src_hash, orig_width, orig_height, new_width, new_height, out_size_bytes,
  duration_ms, im_mode, im_args, error, src_size, src_mtime,
  saved_percent, saved_mb
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""

_SELECT_EXISTING = """
SELECT dst_fullpath
FROM conversions
WHERE src_hash = ? AND status = 'SUCCESS' AND dst_fullpath IS NOT NULL
ORDER BY converted_at DESC
LIMIT 10
"""

class PhotoDB:
    def __init__(self, db_path: Path | str, read_only: bool = False):
        self.path = Path(db_path)
        self.read_only = read_only
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> "PhotoDB":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def open(self) -> None:
        if self.conn:
            return
        
        if self.read_only:
            # Open in read-only mode using URI syntax
            # file:/path/to/db?mode=ro
            uri = f"file:{self.path}?mode=ro"
            self.conn = sqlite3.connect(uri, uri=True)
            # In RO mode, we skip schema setup and migration
        else:
            self.conn = sqlite3.connect(str(self.path))
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA synchronous=NORMAL;")
            self.conn.executescript(_SCHEMA)
            
            # Migration: ensure last_checked_at column exists
            self._ensure_columns()
        
        if not self.read_only:
            self.conn.commit()

    def _ensure_columns(self):
        """Check if last_checked_at exists, invoke ALTER TABLE if not."""
        try:
            cur = self.conn.execute("PRAGMA table_info(conversions)")
            current_cols = {row[1] for row in cur.fetchall()}
            if "last_checked_at" not in current_cols:
                self.conn.execute("ALTER TABLE conversions ADD COLUMN last_checked_at INTEGER")
        except Exception:
            pass  # If table doesn't exist yet, it was just created by executescript above which has the col

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def find_existing_converted(self, src_hash: str) -> Optional[Path]:
        if not src_hash:
            return None
        cur = self.conn.execute(_SELECT_EXISTING, (src_hash,))
        for (dst,) in cur.fetchall():
            if dst and Path(dst).exists():
                return Path(dst)
        return None

    def already_done_here(self, src_hash: str, expected_dst: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM conversions WHERE src_hash=? AND dst_fullpath=? AND status='SUCCESS' LIMIT 1",
            (src_hash, expected_dst),
        )
        return cur.fetchone() is not None

    def update_last_checked(self, src_hash: str, expected_dst: str, ts: int) -> None:
        """Update the last_checked_at timestamp for an existing successful conversion."""
        self.conn.execute(
            "UPDATE conversions SET last_checked_at=? WHERE src_hash=? AND dst_fullpath=? AND status='SUCCESS'",
            (ts, src_hash, expected_dst)
        )
        self.conn.commit()

    def record(self, *, converted_at: int, status: str, src_name: str, src_ext: str,
               src_fullpath: str, dst_fullpath: str | None, src_hash: str | None,
               orig_width: int | None, orig_height: int | None, new_width: int | None, new_height: int | None,
               out_size_bytes: int | None, duration_ms: int, im_mode: str, im_args: str, error: str | None,
               src_size: int | None = None, src_mtime: int | None = None, commit: bool = True) -> None:
        # compute savings
        saved_percent = None
        saved_mb = None
        if src_size and out_size_bytes:
            if src_size > 0:
                saved_percent = int(round((src_size - out_size_bytes) / src_size * 100))
            saved_mb = round((src_size - out_size_bytes) / (1024 * 1024), 2)

        self.conn.execute(_INSERT_SQL, (
            converted_at, status, src_name, src_ext, src_fullpath, dst_fullpath,
            src_hash, orig_width, orig_height, new_width, new_height, out_size_bytes,
            duration_ms, im_mode, im_args, error, src_size, src_mtime,
            saved_percent, saved_mb
        ))
        if commit:
            self.conn.commit()