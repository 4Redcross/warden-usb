from core.audit import AuditLog
from core.models import DriveInfo, FormatJob
from backends.base import DriveBackend

FILESYSTEMS_WINDOWS = ["NTFS", "FAT32", "exFAT"]
FILESYSTEMS_LINUX = ["ext4", "NTFS", "FAT32", "exFAT"]


class Formatter:
    def __init__(self, backend: DriveBackend, audit: AuditLog):
        self._backend = backend
        self._audit = audit

    def format(self, job: FormatJob) -> None:
        if not job.confirmed:
            raise RuntimeError("Format job must be explicitly confirmed before execution.")
        self._backend.format_drive(job.drive, job.filesystem, job.label, job.quick_format)
        self._audit.log_format(job.drive.path, job.filesystem, job.label)

    def get_file_preview(self, drive: DriveInfo) -> list[str]:
        return self._backend.get_drive_files(drive)
