import os
import re
import subprocess
import threading
import time
from typing import Callable, Optional

from core.models import DriveInfo, DriveType
from backends.base import DriveBackend

try:
    import win32api
    import win32file
    _WIN32 = True
except ImportError:
    _WIN32 = False

try:
    import wmi as _wmi_mod
    _WMI = True
except ImportError:
    _WMI = False


class WindowsBackend(DriveBackend):
    def __init__(self):
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ #
    # Drive listing
    # ------------------------------------------------------------------ #

    def list_removable_drives(self) -> list[DriveInfo]:
        import psutil
        drives = []
        for part in psutil.disk_partitions(all=False):
            try:
                if not self._is_removable(part.device):
                    continue
                usage = psutil.disk_usage(part.mountpoint)
                label = self._get_label(part.device)
                drives.append(DriveInfo(
                    path=part.mountpoint,
                    label=label or "USB Drive",
                    filesystem=part.fstype or "Unknown",
                    total_bytes=usage.total,
                    free_bytes=usage.free,
                    drive_type=DriveType.USB,
                    device_id=part.device,
                ))
            except Exception:
                continue
        return drives

    def _is_removable(self, device: str) -> bool:
        if _WIN32:
            try:
                # DRIVE_REMOVABLE = 2
                return win32file.GetDriveType(device) == 2
            except Exception:
                pass
        # Fallback: skip C:\ and anything that looks like an internal drive
        letter = device.upper().rstrip("\\")
        return letter not in ("C:", "D:") and len(letter) == 2

    def _get_label(self, device: str) -> str:
        if _WIN32:
            try:
                info = win32api.GetVolumeInformation(device)
                return info[0]
            except Exception:
                pass
        try:
            result = subprocess.run(
                ["vol", device.rstrip("\\")],
                capture_output=True, text=True, shell=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "Volume in drive" in line and "is" in line:
                    return line.split("is")[-1].strip()
        except Exception:
            pass
        return ""

    # ------------------------------------------------------------------ #
    # Format
    # ------------------------------------------------------------------ #

    def format_drive(self, drive: DriveInfo, filesystem: str, label: str, quick: bool) -> None:
        letter = drive.path.rstrip("\\/")
        if not re.match(r"^[A-Za-z]:$", letter):
            raise ValueError(f"Invalid drive letter: {letter}")

        safe_label = re.sub(r'[^A-Za-z0-9 _\-]', '', label)[:32]
        quick_flag = "quick" if quick else ""

        script = "\n".join([
            f"select volume {letter[0]}",
            f'format fs={filesystem.lower()} label="{safe_label}" {quick_flag}'.strip(),
            "exit",
        ])

        result = subprocess.run(
            ["diskpart"],
            input=script,
            capture_output=True,
            text=True,
            timeout=300,
        )
        # Diskpart returns 0 even on failure — check stdout for success marker
        if result.returncode != 0 or "successfully formatted" not in result.stdout.lower():
            raise RuntimeError(
                f"Diskpart failed:\n{result.stdout}\n{result.stderr}".strip()
            )

    # ------------------------------------------------------------------ #
    # Hot-plug monitoring
    # ------------------------------------------------------------------ #

    def start_monitoring(
        self,
        on_connect: Callable[[DriveInfo], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(on_connect, on_disconnect),
            daemon=True,
        )
        self._monitor_thread.start()

    def _monitor_loop(self, on_connect: Callable, on_disconnect: Callable) -> None:
        if _WMI:
            self._wmi_monitor(on_connect, on_disconnect)
        else:
            self._polling_monitor(on_connect, on_disconnect)

    def _wmi_monitor(self, on_connect: Callable, on_disconnect: Callable) -> None:
        try:
            c = _wmi_mod.WMI()
            watcher = c.Win32_VolumeChangeEvent.watch_for()
            known = {d.path: d for d in self.list_removable_drives()}
            while self._monitoring:
                try:
                    watcher(timeout_ms=1000)
                    current = {d.path: d for d in self.list_removable_drives()}
                    for path, info in current.items():
                        if path not in known:
                            known[path] = info
                            on_connect(info)
                    for path in list(known):
                        if path not in current:
                            del known[path]
                            on_disconnect(path)
                except Exception:
                    pass
        except Exception:
            self._polling_monitor(on_connect, on_disconnect)

    def _polling_monitor(self, on_connect: Callable, on_disconnect: Callable) -> None:
        known = {d.path: d for d in self.list_removable_drives()}
        while self._monitoring:
            time.sleep(2)
            try:
                current = {d.path: d for d in self.list_removable_drives()}
                for path, info in current.items():
                    if path not in known:
                        on_connect(info)
                for path in list(known):
                    if path not in current:
                        on_disconnect(path)
                known = current
            except Exception:
                pass

    def stop_monitoring(self) -> None:
        self._monitoring = False

    # ------------------------------------------------------------------ #
    # File listing
    # ------------------------------------------------------------------ #

    def get_drive_files(self, drive: DriveInfo) -> list[str]:
        files = []
        for root, _, filenames in os.walk(drive.path):
            for fname in filenames:
                files.append(os.path.join(root, fname))
        return files
