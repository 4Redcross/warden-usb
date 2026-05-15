import io
import os
import zipfile
from pathlib import Path
from typing import Callable, Optional

import requests

_RULES_ZIP = "https://github.com/Neo23x0/signature-base/archive/refs/heads/master.zip"

try:
    import yara
    _YARA = True
except ImportError:
    _YARA = False


class YaraEngine:
    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir
        self._compiled: Optional[object] = None

    def is_available(self) -> bool:
        return _YARA

    def has_rules(self) -> bool:
        if not self.rules_dir.exists():
            return False
        return any(self.rules_dir.rglob("*.yar")) or any(self.rules_dir.rglob("*.yara"))

    def load_rules(self) -> bool:
        if not _YARA or not self.has_rules():
            return False

        filepaths: dict[str, str] = {}
        for i, p in enumerate(self.rules_dir.rglob("*.yar")):
            filepaths[f"r{i}"] = str(p)
        for i, p in enumerate(self.rules_dir.rglob("*.yara")):
            filepaths[f"ra{i}"] = str(p)

        if not filepaths:
            return False

        try:
            self._compiled = yara.compile(filepaths=filepaths)
            return True
        except yara.SyntaxError:
            # Load one-by-one, skip broken files
            valid: dict[str, str] = {}
            for ns, path in filepaths.items():
                try:
                    yara.compile(filepath=path)
                    valid[ns] = path
                except yara.SyntaxError:
                    pass
            if valid:
                self._compiled = yara.compile(filepaths=valid)
                return True
            return False

    def scan_file(self, file_path: Path) -> list[str]:
        if not _YARA or self._compiled is None:
            return []
        try:
            matches = self._compiled.match(str(file_path), timeout=30)
            return [m.rule for m in matches]
        except Exception:
            return []

    def download_rules(self, progress_cb: Optional[Callable[[int], None]] = None) -> bool:
        """Download Neo23x0/signature-base YARA rules. Returns True on success."""
        try:
            resp = requests.get(_RULES_ZIP, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            buf = io.BytesIO()
            for chunk in resp.iter_content(chunk_size=8192):
                buf.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total:
                    progress_cb(int(downloaded / total * 100))

            buf.seek(0)
            self.rules_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(buf) as zf:
                for name in zf.namelist():
                    if name.endswith((".yar", ".yara")) and "/yara/" in name:
                        fname = os.path.basename(name)
                        if fname:
                            dest = self.rules_dir / fname
                            with zf.open(name) as src, open(dest, "wb") as dst:
                                dst.write(src.read())

            return self.has_rules()
        except Exception:
            return False
