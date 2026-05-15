"""
Hot-reload dev launcher.
Watches gui/ and core/ for .py changes, then kills and restarts main.py.
Usage:  python dev.py
"""
import subprocess
import sys
import threading
import time
from pathlib import Path

WATCH_DIRS = ["web", "core", "workers"]
WATCH_ROOT_FILES = {"webapi.py", "main.py"}
MAIN = [sys.executable, "main.py"]


def _watch(restart_event: threading.Event, stop_event: threading.Event) -> None:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    EXTS = {".py", ".jsx", ".css", ".html"}
    cwd = Path.cwd().resolve()

    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            p = Path(event.src_path)
            if event.is_directory or p.suffix not in EXTS:
                return
            # For root-level watches only fire on specific files
            try:
                rel = p.resolve().relative_to(cwd)
            except ValueError:
                return
            parts = rel.parts
            if len(parts) == 1 and parts[0] not in WATCH_ROOT_FILES:
                return
            print(f"\n  ↻  {rel} changed — reloading…\n")
            restart_event.set()

    observer = Observer()
    for d in WATCH_DIRS:
        if Path(d).is_dir():
            observer.schedule(_Handler(), d, recursive=True)
    # Also watch root for webapi.py / main.py
    observer.schedule(_Handler(), ".", recursive=False)
    observer.start()
    stop_event.wait()
    observer.stop()
    observer.join()


def main() -> None:
    print("Warden dev server — watching web/, core/, workers/")
    print("Press Ctrl+C to quit.\n")

    restart_event = threading.Event()
    stop_event = threading.Event()

    watcher = threading.Thread(target=_watch, args=(restart_event, stop_event), daemon=True)
    watcher.start()

    try:
        while True:
            restart_event.clear()
            print("  ▶  Starting Warden…")
            proc = subprocess.Popen(MAIN)

            # Wait for either the process to exit or a file change
            while True:
                if restart_event.wait(timeout=0.3):
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    time.sleep(0.4)   # brief pause so the OS releases file locks
                    break
                if proc.poll() is not None:
                    # App closed normally (user shut the window)
                    print("  ■  Warden exited.")
                    return

    except KeyboardInterrupt:
        print("\n  ■  Stopping.")
        try:
            proc.terminate()
        except Exception:
            pass
    finally:
        stop_event.set()


if __name__ == "__main__":
    main()
