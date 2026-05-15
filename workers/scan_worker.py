import threading
from typing import Callable

from core.models import DriveInfo, ScanResult
from core.scanner import Scanner


class ScanWorker(threading.Thread):
    def __init__(
        self,
        scanner: Scanner,
        drive: DriveInfo,
        on_progress: Callable[[int, str], None],
        on_result: Callable[[ScanResult], None],
        on_error: Callable[[str], None],
    ):
        super().__init__(daemon=True)
        self._scanner = scanner
        self._drive = drive
        self._on_progress = on_progress
        self._on_result = on_result
        self._on_error = on_error
        self._cancelled = False

    def run(self) -> None:
        try:
            result = self._scanner.scan_drive(
                self._drive,
                progress_callback=self._on_progress,
                cancel_check=lambda: self._cancelled,
            )
            self._on_result(result)
        except Exception as e:
            self._on_error(str(e))

    def cancel(self) -> None:
        self._cancelled = True
