# Implementation Plan: Optimize Database Writes and Cleanup

## Goal
Reduce database growth and bloating by converting the "append-only" logging strategy for skipped files into an "update-existing" strategy. Additionally, provide a cleanup mechanism to fix existing bloated databases.

## User Review Required
> [!IMPORTANT]
> This change involves a schema migration (adding `last_checked_at` column). The cleanup script is a destructive operation that removes duplicate `ALREADY_DONE` records.

## Proposed Changes

### [app/database_operations.py](file:///Users/ivan.cherednychok/Projects/photo-resizer/app/database_operations.py)
- [ ] Update `_SCHEMA` and `open()` to ensure `last_checked_at` column exists (INTEGER/Timestamp).
- [ ] Add `update_last_checked(src_hash, dst_fullpath)` method:
    - Executes `UPDATE conversions SET last_checked_at = ? WHERE src_hash = ? AND dst_fullpath = ? AND status = 'SUCCESS'` (or matches existing ALREADY_DONE logic).
    - Uses current unix timestamp.

### [app/converter.py](file:///Users/ivan.cherednychok/Projects/photo-resizer/app/converter.py)
- [ ] Modify `process_one`:
    - In `ALREADY_DONE` block:
        - Call `db.update_last_checked(...)` instead of `_log_db`.
        - Log "ALREADY_DONE (updated timestamp)" to standard logger.
    - In `SKIPPED_DUP` block:
        - Keep existing logic (creates a new record for the new destination).

### [scripts/db_cleanup.py](file:///Users/ivan.cherednychok/Projects/photo-resizer/scripts/db_cleanup.py)
- [ ] Create new script:
    - Connects to `photo_conversions.db`.
    - Selects all `src_hash`, `dst_fullpath` having count > 1.
    - Iterates groups:
        - Identifies the "main" record (status=SUCCESS or oldest).
        - Finds `max(converted_at)` from the group.
        - Updates main record with `last_checked_at = max(converted_at)`.
        - Deletes all other records in that group.
    - Runs `VACUUM`.

## Verification
- [ ] **Test Cleanup**: Run `scripts/db_cleanup.py` on a copy of the bloated DB. Verify size reduction and that 'SUCCESS' records remain.
- [ ] **Test Bloat Prevention**:
    - Run `run.sh` once.
    - Run `run.sh` again (should be all skips).
    - Verify `SELECT count(*) FROM conversions` did not increase.
    - Verify `last_checked_at` was updated.
