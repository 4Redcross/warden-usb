from core.models import DriveInfo
from backends.base import DriveBackend


class DriveManager:
    def __init__(self, backend: DriveBackend):
        self._backend = backend

    def list_drives(self) -> list[DriveInfo]:
        return self._backend.list_removable_drives()

    def get_files(self, drive: DriveInfo) -> list[str]:
        return self._backend.get_drive_files(drive)
