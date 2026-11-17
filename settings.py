"""Only workspace and document paths are persisted. No document content or telemetry."""
import json
import os
from pathlib import Path
import tempfile


def default_settings_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif __import__("sys").platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "UPT" / "session.json"


class Settings:
    def __init__(self, path: Path | None = None):
        self.path = path or default_settings_path()

    def load(self) -> dict[str, str]:
        try:
            if not self.path.exists():
                return {}
            if self.path.stat().st_size > 16384:
                raise ValueError("settings are too large")
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("settings must be an object")
            return {key: value for key, value in data.items()
                    if key in {"workspace", "document"} and isinstance(value, str)}
        except (OSError, ValueError) as exc:
            raise ValueError(f"Cannot restore the previous session: {exc}") from exc

    def save(self, workspace: Path | None, document: Path | None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix="session-", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump({"workspace": str(workspace) if workspace else "",
                           "document": str(document) if document else ""}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
