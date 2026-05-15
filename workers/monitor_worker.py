import threading
from typing import Callable

from core.models import DriveInfo
from core.monitor import DriveMonitor


class MonitorWorker(threading.Thread):
    def __init__(
        self,
        monitor: DriveMonitor,
        on_connect: Callable[[DriveInfo], None],
        on_disconnect: Callable[[str], None],
    ):
        super().__init__(daemon=True)
        self._monitor = monitor
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect

    def run(self) -> None:
        self._monitor.start(
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )

    def stop(self) -> None:
        self._monitor.stop()
