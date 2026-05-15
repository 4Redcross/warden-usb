from typing import Callable, Optional

from core.models import DriveInfo
from backends.base import DriveBackend


class DriveMonitor:
    def __init__(self, backend: DriveBackend):
        self._backend = backend

    def start(
        self,
        on_connect: Callable[[DriveInfo], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        self._backend.start_monitoring(on_connect, on_disconnect)

    def stop(self) -> None:
        self._backend.stop_monitoring()
