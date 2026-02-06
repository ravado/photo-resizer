#!/usr/bin/env python3
"""
Database Cleanup Script for Photo Resizer

Usage:
    python3 scripts/db_cleanup.py

This script:
1. Adds the `last_checked_at` column if missing.
2. Finds valid 'SUCCESS' records for each (src_hash, dst_fullpath).
3. Updates their `last_checked_at` with the latest timestamp from any duplicate `ALREADY_DONE` records.
4. Deletes the redundant records.
5. Vacuums the database.
"""
import sys
import argparse
import sqlite3
import time
from pathlib import Path

# Fix python path to allow imports from app
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import default from config
try:
    from app.config import DB_PATH
except ImportError:
    DB_PATH = "photo_conversions.db" # Fallback

def cleanup(db_path_str: str):
    path = Path(db_path_str)
    if not path.exists():
        print(f"Error: Database not found at {path}")
        return

    print(f"Opening database: {path}")
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL;")
    
    # 1. Ensure column
    try:
        conn.execute("ALTER TABLE conversions ADD COLUMN last_checked_at INTEGER")
        print("Added 'last_checked_at' column.")
    except sqlite3.OperationalError:
        pass # already exists
    
    # Check if table exists
    try:
        conn.execute("SELECT 1 FROM conversions LIMIT 1")
    except sqlite3.OperationalError:
        print("Table 'conversions' does not exist. Initializing schema...")
        # (This script assumes the table exists, but if not we could exit)
        print("Nothing to clean in an empty/new DB.")
        return

    # 2. Identify heavy duplication
    print("Analyzing duplicates...")
    cur = conn.execute("""
        SELECT src_hash, dst_fullpath, COUNT(*) as cnt
        FROM conversions
        WHERE src_hash IS NOT NULL AND dst_fullpath IS NOT NULL
        GROUP BY src_hash, dst_fullpath
        HAVING cnt > 1
    """)
    groups = cur.fetchall()
    print(f"Found {len(groups)} distinct files with duplicate entries.")

    for i, (src_hash, dst_path, cnt) in enumerate(groups, start=1):
        # ... (rest of the logic remains roughly the same, but indented)
        rows_cur = conn.execute("""
            SELECT id, status, converted_at FROM conversions
            WHERE src_hash = ? AND dst_fullpath = ?
            ORDER BY converted_at ASC
        """, (src_hash, dst_path))
        rows = rows_cur.fetchall()
        
        # Determine primary
        success_rows = [r for r in rows if r[1] == 'SUCCESS']
        if success_rows:
            primary_id = success_rows[0][0]
        else:
            primary_id = rows[0][0] # Fallback

        # Calculate max timestamp
        latests_ts = max(r[2] for r in rows)
        
        # Collect IDs to delete
        ids_to_delete = [r[0] for r in rows if r[0] != primary_id]
        
        if not ids_to_delete:
            continue

        # Execute updates
        conn.execute(
            "UPDATE conversions SET last_checked_at = ? WHERE id = ?",
            (latests_ts, primary_id)
        )
        # Delete chunked
        conn.execute(
            f"DELETE FROM conversions WHERE id IN ({','.join('?'*len(ids_to_delete))})",
            ids_to_delete
        )
        
        if i % 100 == 0:
            print(f"Processed {i}/{len(groups)}...")
            conn.commit()

    conn.commit()
    print("Vacuuming database...")
    conn.execute("VACUUM")
    conn.close()
    print("Done.")

def main():
    parser = argparse.ArgumentParser(description="Cleanup duplicates in photo database.")
    parser.add_argument("db_path", nargs="?", default=str(DB_PATH), help="Path to sqlite database")
    args = parser.parse_args()
    
    cleanup(args.db_path)

if __name__ == "__main__":
    main()
