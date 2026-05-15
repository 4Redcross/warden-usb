import os
import subprocess
import threading
import time
from typing import Callable, Optional

from core.models import DriveInfo, DriveType
from backends.base import DriveBackend

try:
    import pyudev
    _UDEV = True
except ImportError:
    _UDEV = False


class LinuxBackend(DriveBackend):
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
                    label=label or os.path.basename(part.mountpoint) or "USB Drive",
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
        dev_name = os.path.basename(device).rstrip("0123456789")
        try:
            with open(f"/sys/block/{dev_name}/removable") as f:
                return f.read().strip() == "1"
        except OSError:
            return False

    def _get_label(self, device: str) -> str:
        try:
            result = subprocess.run(
                ["lsblk", "-no", "LABEL", device],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------ #
    # Format
    # ------------------------------------------------------------------ #

    def format_drive(self, drive: DriveInfo, filesystem: str, label: str, quick: bool) -> None:
        device = drive.device_id
        if not device.startswith("/dev/"):
            raise ValueError(f"Invalid device path: {device}")

        safe_label = label[:11] if filesystem.lower() == "fat32" else label[:32]

        fs_cmds: dict[str, list[str]] = {
            "ntfs":  ["mkfs.ntfs", *([ "-f"] if quick else []), "-L", safe_label, device],
            "fat32": ["mkfs.fat", "-F", "32", "-n", safe_label, device],
            "exfat": ["mkfs.exfat", "-n", safe_label, device],
            "ext4":  ["mkfs.ext4", "-L", safe_label, device],
            "ext3":  ["mkfs.ext3", "-L", safe_label, device],
        }

        cmd = fs_cmds.get(filesystem.lower())
        if not cmd:
            raise ValueError(f"Unsupported filesystem: {filesystem}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"Format failed:\n{result.stderr}")

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
        if _UDEV:
            self._udev_monitor(on_connect, on_disconnect)
        else:
            self._polling_monitor(on_connect, on_disconnect)

    def _udev_monitor(self, on_connect: Callable, on_disconnect: Callable) -> None:
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="block", device_type="disk")
        monitor.start()
        known = {d.path: d for d in self.list_removable_drives()}
        while self._monitoring:
            device = monitor.poll(timeout=1)
            if device:
                time.sleep(1)  # brief wait for mount to settle
                current = {d.path: d for d in self.list_removable_drives()}
                for path, info in current.items():
                    if path not in known:
                        known[path] = info
                        on_connect(info)
                for path in list(known):
                    if path not in current:
                        del known[path]
                        on_disconnect(path)

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
