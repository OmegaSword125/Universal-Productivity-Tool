"""Single-document state; unsuccessful operations never clear the edit buffer."""
from dataclasses import dataclass
from pathlib import Path

from .storage import Loaded, Revision, Workspace


@dataclass
class Document:
    text: str = ""
    saved_text: str = ""
    path: Path | None = None
    revision: Revision | None = None
    newline: str = "\n"
    bom: bool = False

    @property
    def dirty(self) -> bool:
        return self.text != self.saved_text

    @classmethod
    def from_loaded(cls, loaded: Loaded) -> "Document":
        return cls(loaded.text, loaded.text, loaded.path, loaded.revision,
                   loaded.newline, loaded.bom)

    def save(self, workspace: Workspace, target: Path | None = None) -> None:
        path = target or self.path
        if path is None:
            raise ValueError("Choose a filename before saving.")
        expected = self.revision if path == self.path else None
        loaded = workspace.write(path, self.text, expected, newline=self.newline, bom=self.bom)
        self.path, self.revision = loaded.path, loaded.revision
        self.saved_text = self.text
