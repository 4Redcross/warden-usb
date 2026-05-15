from abc import ABC, abstractmethod
from typing import Callable

from core.models import DriveInfo


class DriveBackend(ABC):

    @abstractmethod
    def list_removable_drives(self) -> list[DriveInfo]:
        """Return all currently connected removable drives."""
        ...

    @abstractmethod
    def format_drive(self, drive: DriveInfo, filesystem: str, label: str, quick: bool) -> None:
        """Format the drive. Raises RuntimeError on failure."""
        ...

    @abstractmethod
    def start_monitoring(
        self,
        on_connect: Callable[[DriveInfo], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        """Start background monitoring for drive plug/unplug events."""
        ...

    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        ...

    @abstractmethod
    def get_drive_files(self, drive: DriveInfo) -> list[str]:
        """Return a flat list of all file paths on the drive."""
        ...
