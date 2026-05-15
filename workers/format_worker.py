import threading
from typing import Callable

from core.formatter import Formatter
from core.models import FormatJob


class FormatWorker(threading.Thread):
    def __init__(
        self,
        formatter: Formatter,
        job: FormatJob,
        on_status: Callable[[str], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None],
    ):
        super().__init__(daemon=True)
        self._formatter = formatter
        self._job = job
        self._on_status = on_status
        self._on_finished = on_finished
        self._on_error = on_error

    def run(self) -> None:
        try:
            self._on_status(f"Formatting {self._job.drive.display_name()} as {self._job.filesystem}…")
            self._formatter.format(self._job)
            self._on_finished()
        except Exception as e:
            self._on_error(str(e))
