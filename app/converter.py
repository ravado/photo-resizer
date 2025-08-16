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
    def __init__(self, planner: Planner, engine: ImageEngine, db_path: Path):
        self.planner = planner
        self.engine = engine
        self.db_path = db_path

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

        # ALREADY_DONE
        if src_hash and db.already_done_here(src_hash, str(output_path)) and output_path.exists():
            end_ts = time.time()
            dur = int(round(end_ts * 1000)) - start_ms
            out_size = output_path.stat().st_size if output_path.exists() else None
            print(f"[{time.strftime('%d-%m-%Y %H:%M:%S')}] #{idx} of {total}")
            print(f"[{full_path.name}] ALREADY_DONE (hash match and file present in destination)\n")
            self._log_db(db, end_ts=end_ts, status="ALREADY_DONE", filename=full_path.name, file_ext=file_ext,
                         full_path=full_path, output_path=output_path, src_hash=src_hash,
                         orig_w=None, orig_h=None, new_w=None, new_h=None, out_size=out_size,
                         duration_ms=dur, im_args="(already converted here)", error=None,
                         src_size=src_size, src_mtime=src_mtime)
            return int(time.time() - start_ts)

        # SKIPPED_DUP: reuse elsewhere
        existing_dst = db.find_existing_converted(src_hash) if src_hash else None
        if existing_dst:
            try:
                if existing_dst.resolve() == output_path.resolve():
                    end_ts = time.time()
                    dur = int(round(end_ts * 1000)) - start_ms
                    out_size = output_path.stat().st_size if output_path.exists() else None
                    print(f"[{time.strftime('%d-%m-%Y %H:%M:%S')}] #{idx} of {total}")
                    print(f"[{full_path.name}] ALREADY_DONE (dedupe hit is this destination)\n")
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
                print(f"[{time.strftime('%d-%m-%Y %H:%M:%S')}] #{time.strftime('%d-%m-%Y %H:%M:%S')} #{idx} of {total}")
                print(f"[{full_path.name}] SKIPPED (duplicate by hash). Copied from: {existing_dst}\n")
                self._log_db(db, end_ts=end_ts, status="SKIPPED_DUP", filename=full_path.name, file_ext=file_ext,
                             full_path=full_path, output_path=output_path, src_hash=src_hash,
                             orig_w=None, orig_h=None, new_w=None, new_h=None, out_size=out_size,
                             duration_ms=dur, im_args="(skipped duplicate; copied existing)", error=None,
                             src_size=src_size, src_mtime=src_mtime)
                return int(time.time() - start_ts)
            except Exception as e:
                print(f"WARNING: failed to copy existing conversion ({existing_dst}) -> {output_path}: {e}")
                # continue to full convert

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
            print(f"ERROR: Failed to auto-orient {full_path}: {e}")
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
            try: auto_oriented_path.unlink(missing_ok=True)
            except Exception: pass
            print(f"ERROR: Failed to identify size for {auto_oriented_path}: {e}")
            return int(time.time() - start_ts)

        print(f"[{time.strftime('%d-%m-%Y %H:%M:%S')}] #{idx} of {total}")
        print(f"[{filename}] of {orig_w}x{orig_h}")

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
                print(f"Resizing {full_path} to {resized_path}")
                print(f"New dimensions: {new_w}x{new_h}")
                im_args_used = self.engine.resize_percent(auto_oriented_path, resized_path, percent)
                if output_path.exists(): output_path.unlink()
                shutil.move(str(resized_path), str(output_path))
                print(f"Cleaned redundant file {resized_path}")
                print("Resized")
            else:
                print(f"Copying {full_path} without resizing")
                shutil.copy2(auto_oriented_path, resized_path)
                if output_path.exists(): output_path.unlink()
                shutil.move(str(resized_path), str(output_path))
                new_w, new_h = orig_w, orig_h
                im_args_used = "(copy without resize)"
        except Exception as e:
            status = "FAILED"
            error_text = str(e)
        finally:
            try: auto_oriented_path.unlink(missing_ok=True)
            except Exception: pass

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
            m, s = divmod(elapsed, 60); print(f"Elapsed time: {m}m {s}s")
        else:
            print(f"Elapsed time: {elapsed}s")
        print()
        return elapsed
    
    def cleanup_temp_files(self, watch_dir: pathlib.Path):
        # scan all subfolders
        for pattern in ("*_auto_oriented.*", "*_resized.*"):
            for f in watch_dir.rglob(pattern):
                name = f.name
                # derive the base *stem* before the temp marker
                if "_auto_oriented" in name:
                    base_stem = name.replace("_auto_oriented", "").rsplit(".", 1)[0]
                elif "_resized" in name:
                    base_stem = name.replace("_resized", "").rsplit(".", 1)[0]
                else:
                    continue

                # look for any plausible original with the same stem
                has_original = any((f.parent / f"{base_stem}{ext}").exists() for ext in EXTS)
                if not has_original:
                    try:
                        print(f"🧹 Removing leftover {f}")
                        f.unlink()
                    except Exception:
                        pass

    def run(self, location_key: str):
        watch_dir, out_dir = self.planner.dirs_for_location(location_key)
        print(f"[{time.strftime('%d-%m-%Y %H:%M:%S')}] Initializing resizing script...\n")

        # Clean up before doing anything
        self.cleanup_temp_files(watch_dir)

        candidates = self.planner.list_candidates(watch_dir)
        total = len(candidates)

        total_elapsed = 0
        with PhotoDB(self.db_path) as db:
            for idx, p in enumerate(candidates, start=1):
                total_elapsed += self.process_one(db=db, idx=idx, total=total,
                                                  full_path=p, watch_dir=watch_dir, out_dir=out_dir)

        # final logs
        if total_elapsed >= 3600:
            h, rem = divmod(total_elapsed, 3600); m, s = divmod(rem, 60)
            print(f"Total time: {h}h {m}m {s}s")
        elif total_elapsed >= 60:
            m, s = divmod(total_elapsed, 60); print(f"Total time: {m}m {s}s")
        else:
            print(f"Total time: {total_elapsed}s")
