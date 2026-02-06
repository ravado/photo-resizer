from __future__ import annotations
import time, shutil
from pathlib import Path
from decimal import Decimal, getcontext
from app.config import RESIZE_WIDTH, RESIZE_HEIGHT, IM_MODE, EXTS
from app.planner import Planner
from app.imaging import ImageEngine
from app.database_operations import PhotoDB

getcontext().prec = 28


class Converter:
    # def __init__(self, planner: Planner, engine: ImageEngine, db_path: Path):
    #     self.planner = planner
    #     self.engine = engine
    #     self.db_path = db_path
    def __init__(self, planner, engine, db_path, make_logger):
        self.planner = planner
        self.engine = engine
        self.db_path = db_path
        # one child per class; add static context if useful
        self.log: logging.Logger = make_logger("converter")

    @staticmethod
    def _log_db(db: PhotoDB, *, end_ts: float, status: str, filename: str, file_ext: str,
                full_path: Path, output_path: Path, src_hash: str | None,
                orig_w: int | None, orig_h: int | None, new_w: int | None, new_h: int | None,
                out_size: int | None, duration_ms: int, im_args: str, error: str | None,
                src_size: int | None = None, src_mtime: int | None = None) -> None:
        db.record(
            converted_at=int(end_ts), status=status,
            src_name=filename, src_ext=file_ext,
            src_fullpath=str(full_path), dst_fullpath=str(output_path),
            src_hash=src_hash, orig_width=orig_w, orig_height=orig_h,
            new_width=new_w, new_height=new_h, out_size_bytes=out_size,
            duration_ms=duration_ms, im_mode=IM_MODE, im_args=im_args, error=error,
            src_size=src_size, src_mtime=src_mtime
        )

    def process_one(self, *, db: PhotoDB, idx: int, total: int, full_path: Path, watch_dir: Path, out_dir: Path) -> int:
        start_ts = time.time()
        start_ms = int(round(start_ts * 1000))
        st = full_path.stat()
        src_size, src_mtime = st.st_size, int(st.st_mtime)

        file_ext = full_path.suffix
        out_ext = self.planner.mapped_ext(file_ext)
        resized_path, output_path, auto_oriented_path = self.planner.expected_paths(full_path, watch_dir, out_dir, out_ext)

        try:
            src_hash = self.engine.sha256_file(full_path)
        except Exception:
            src_hash = None
            self.log.debug("SHA256 computation failed for %s (continuing without hash)", full_path)

        # ALREADY_DONE
        if src_hash and db.already_done_here(src_hash, str(output_path)) and output_path.exists():
            end_ts = time.time()
            self.log.info("#%d/%d %s: ALREADY_DONE (updating last_checked_at)", idx, total, full_path.name)
            # Instead of inserting a new row, just update the timestamp on the existing one
            db.update_last_checked(src_hash, str(output_path), int(end_ts))
            return int(time.time() - start_ts)

        # SKIPPED_DUP: reuse elsewhere
        existing_dst = db.find_existing_converted(src_hash) if src_hash else None
        if existing_dst:
            try:
                if existing_dst.resolve() == output_path.resolve():
                    end_ts = time.time()
                    dur = int(round(end_ts * 1000)) - start_ms
                    out_size = output_path.stat().st_size if output_path.exists() else None
                    self.log.info("#%d/%d %s: ALREADY_DONE (dedupe hit is this destination)", idx, total, full_path.name)
                    self._log_db(db, end_ts=end_ts, status="ALREADY_DONE", filename=full_path.name, file_ext=file_ext,
                                 full_path=full_path, output_path=output_path, src_hash=src_hash,
                                 orig_w=None, orig_h=None, new_w=None, new_h=None, out_size=out_size,
                                 duration_ms=dur, im_args="(already converted here; dedupe hit)", error=None,
                                 src_size=src_size, src_mtime=src_mtime)
                    return int(time.time() - start_ts)

                output_path.parent.mkdir(parents=True, exist_ok=True)
                if output_path.exists():
                    output_path.unlink()
                shutil.copy2(existing_dst, output_path)
                out_size = output_path.stat().st_size if output_path.exists() else None

                end_ts = time.time()
                dur = int(round(end_ts * 1000)) - start_ms
                self.log.info("#%d/%d %s: SKIPPED_DUP (copied from existing: %s)", idx, total, full_path.name, existing_dst)
                self._log_db(db, end_ts=end_ts, status="SKIPPED_DUP", filename=full_path.name, file_ext=file_ext,
                             full_path=full_path, output_path=output_path, src_hash=src_hash,
                             orig_w=None, orig_h=None, new_w=None, new_h=None, out_size=out_size,
                             duration_ms=dur, im_args="(skipped duplicate; copied existing)", error=None,
                             src_size=src_size, src_mtime=src_mtime)
                return int(time.time() - start_ts)
            except Exception as e:
                self.log.warning("Failed to copy existing conversion (%s) -> %s: %s", existing_dst, output_path, e)
                # fall through to full convert

        # Normal convert
        filename = full_path.name
        try:
            self.engine.auto_orient(full_path, auto_oriented_path)
        except Exception as e:
            end_ts = time.time()
            self._log_db(db, end_ts=end_ts, status="FAILED", filename=filename, file_ext=file_ext,
                         full_path=full_path, output_path=output_path, src_hash=src_hash,
                         orig_w=None, orig_h=None, new_w=None, new_h=None, out_size=None,
                         duration_ms=int(round(end_ts * 1000)) - start_ms,
                         im_args="-auto-orient", error=str(e),
                         src_size=src_size, src_mtime=src_mtime)
            self.log.error("Auto-orient failed for %s: %s", full_path, e)
            return int(time.time() - start_ts)

        try:
            orig_w, orig_h = self.engine.identify_size(auto_oriented_path)
        except Exception as e:
            end_ts = time.time()
            self._log_db(db, end_ts=end_ts, status="FAILED", filename=filename, file_ext=file_ext,
                         full_path=full_path, output_path=output_path, src_hash=src_hash,
                         orig_w=None, orig_h=None, new_w=None, new_h=None, out_size=None,
                         duration_ms=int(round(end_ts * 1000)) - start_ms,
                         im_args="-identify", error=str(e),
                         src_size=src_size, src_mtime=src_mtime)
            try:
                auto_oriented_path.unlink(missing_ok=True)
            except Exception:
                pass
            self.log.error("Identify size failed for %s: %s", auto_oriented_path, e)
            return int(time.time() - start_ts)

        self.log.info("#%d/%d %s: original size %dx%d", idx, total, filename, orig_w, orig_h)

        status = "SUCCESS"
        error_text = None
        new_w = new_h = None
        out_size = None
        im_args_used = ""

        try:
            if (orig_w > RESIZE_WIDTH) or (orig_h > RESIZE_HEIGHT):
                sw = Decimal(RESIZE_WIDTH) / Decimal(orig_w)
                sh = Decimal(RESIZE_HEIGHT) / Decimal(orig_h)
                scale = sh if sw < sh else sw
                scale += Decimal("0.01")
                percent = scale * Decimal("100")
                new_w = int((Decimal(orig_w) * scale).to_integral_value())
                new_h = int((Decimal(orig_h) * scale).to_integral_value())
                self.log.info("Resizing %s → %s (new %dx%d, %s%%)", full_path, resized_path, new_w, new_h, percent)
                im_args_used = self.engine.resize_percent(auto_oriented_path, resized_path, percent)
                if output_path.exists():
                    output_path.unlink()
                shutil.move(str(resized_path), str(output_path))
                self.log.debug("Removed temp resized file %s after move", resized_path)
                self.log.info("Resized → %s", output_path)
            else:
                self.log.info("Copying without resize: %s → %s", full_path, output_path)
                shutil.copy2(auto_oriented_path, resized_path)
                if output_path.exists():
                    output_path.unlink()
                shutil.move(str(resized_path), str(output_path))
                new_w, new_h = orig_w, orig_h
                im_args_used = "(copy without resize)"
        except Exception as e:
            status = "FAILED"
            error_text = str(e)
            self.log.error("Conversion failed for %s: %s", full_path, e)
        finally:
            try:
                auto_oriented_path.unlink(missing_ok=True)
            except Exception:
                pass

        if output_path.exists():
            out_size = output_path.stat().st_size

        end_ts = time.time()
        dur_ms = int(round(end_ts * 1000)) - start_ms
        elapsed = int(end_ts - start_ts)

        self._log_db(db, end_ts=end_ts, status=status, filename=filename, file_ext=file_ext,
                     full_path=full_path, output_path=output_path, src_hash=src_hash,
                     orig_w=orig_w, orig_h=orig_h, new_w=new_w, new_h=new_h,
                     out_size=out_size, duration_ms=dur_ms,
                     im_args=im_args_used, error=error_text,
                     src_size=src_size, src_mtime=src_mtime)

        if elapsed >= 60:
            m, s = divmod(elapsed, 60)
            self.log.info("Elapsed: %dm %ds", m, s)
        else:
            self.log.info("Elapsed: %ds", elapsed)

        return elapsed

    def cleanup_temp_files(self, watch_dir: Path):
        # scan all subfolders
        for pattern in ("*_auto_oriented.*", "*_resized.*"):
            for f in watch_dir.rglob(pattern):
                name = f.name
                if "_auto_oriented" in name:
                    base_stem = name.replace("_auto_oriented", "").rsplit(".", 1)[0]
                elif "_resized" in name:
                    base_stem = name.replace("_resized", "").rsplit(".", 1)[0]
                else:
                    continue

                has_original = any((f.parent / f"{base_stem}{ext}").exists() for ext in EXTS)
                if not has_original:
                    try:
                        self.log.info("Removing leftover temp file: %s", f)
                        f.unlink()
                    except Exception as e:
                        self.log.debug("Failed to remove %s: %s", f, e)

    def run(self, location_key: str):
        watch_dir, out_dir = self.planner.dirs_for_location(location_key)
        self.log.info("Initializing resizing run for location '%s'...", location_key)

        # Clean up before doing anything
        self.cleanup_temp_files(watch_dir)

        candidates = self.planner.list_candidates(watch_dir)
        total = len(candidates)
        self.log.info("Found %d candidate(s) in %s", total, watch_dir)

        total_elapsed = 0
        with PhotoDB(self.db_path) as db:
            for idx, p in enumerate(candidates, start=1):
                total_elapsed += self.process_one(db=db, idx=idx, total=total,
                                                  full_path=p, watch_dir=watch_dir, out_dir=out_dir)

        # final logs
        if total_elapsed >= 3600:
            h, rem = divmod(total_elapsed, 3600); m, s = divmod(rem, 60)
            self.log.info("Total time: %dh %dm %ds", h, m, s)
        elif total_elapsed >= 60:
            m, s = divmod(total_elapsed, 60)
            self.log.info("Total time: %dm %ds", m, s)
        else:
            self.log.info("Total time: %ds", total_elapsed)
