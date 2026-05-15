import threading
from pathlib import Path
from typing import Callable

from core.audit import AuditLog
from core.fileserver import FileServer


class ServerWorker(threading.Thread):
    def __init__(
        self,
        server: FileServer,
        audit: AuditLog,
        root_path: Path,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool,
        on_started: Callable[[str], None],
        on_error: Callable[[str], None],
    ):
        super().__init__(daemon=True)
        self._server = server
        self._audit = audit
        self._root_path = root_path
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_ssl = use_ssl
        self._on_started = on_started
        self._on_error = on_error
        self._stop_event = threading.Event()

    def run(self) -> None:
        try:
            url = self._server.start(
                self._root_path,
                self._host,
                self._port,
                self._username,
                self._password,
                self._use_ssl,
            )
            self._audit.log_server("start", str(self._root_path), self._port)
            self._on_started(url)
            self._stop_event.wait()
        except Exception as e:
            self._on_error(str(e))

    def stop_server(self) -> None:
        self._server.stop()
        self._audit.log_server("stop", str(self._root_path), self._port)
        self._stop_event.set()
