"""Workspace confinement and conservative, atomic UTF-8 document storage.

No Qt dependency: the UI must go through this boundary for every document action.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile

MAX_BYTES = 5 * 1024 * 1024
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.I)


class WorkspaceError(Exception):
    """A user-readable filesystem or validation failure."""


class ConflictError(WorkspaceError):
    """The disk no longer matches the version opened by the editor."""


def validate_name(name: str) -> str:
    if (not name or len(name) > 200 or name in {".", ".."}
            or name != name.strip() or name.endswith(".")
            or any(ord(c) < 32 or ord(c) == 127 or c in '<>:"/\\|?*' for c in name)
            or RESERVED.fullmatch(name)):
        raise WorkspaceError("Use a name of 1–200 characters without path separators, "
                             "reserved device names, trailing dots, or special characters.")
    return name


def is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def commit_new(temporary: Path, target: Path) -> None:
    """Commit without replacing a competing writer's file on either OS family."""
    if os.name == "nt":
        # Windows rename fails when the destination exists; POSIX rename does not.
        os.rename(temporary, target)
    else:
        os.link(temporary, target)


@dataclass(frozen=True)
class Revision:
    digest: str
    size: int
    mtime_ns: int
    inode: int


@dataclass(frozen=True)
class Loaded:
    path: Path
    text: str
    revision: Revision
    newline: str = "\n"
    bom: bool = False


class Workspace:
    def __init__(self, root: str | Path):
        try:
            self.root = Path(root).expanduser().resolve(strict=True)
            if not self.root.is_dir():
                raise WorkspaceError("The workspace must be a folder.")
        except (OSError, RuntimeError, ValueError) as exc:
            raise WorkspaceError(f"Cannot open workspace: {exc}") from exc

    def path(self, value: str | Path, *, allow_root: bool = False) -> Path:
        """Reject traversal, portable unsafe names, and every symlink/junction component."""
        try:
            return self._path(value, allow_root=allow_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise WorkspaceError(f"Cannot access the workspace path: {exc}") from exc

    def _path(self, value: str | Path, *, allow_root: bool = False) -> Path:
        if is_link(self.root) or not self.root.is_dir() or self.root.resolve() != self.root:
            raise WorkspaceError("The workspace folder is missing or was replaced. Choose it again.")
        value = Path(value)
        candidate = value if value.is_absolute() else self.root / value
        try:
            relative = candidate.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError("Choose a path inside the current workspace.") from exc
        if not relative.parts and not allow_root:
            raise WorkspaceError("The workspace root cannot be renamed or deleted.")
        cursor = self.root
        for part in relative.parts:
            validate_name(part)
            cursor = cursor / part
            if is_link(cursor):
                raise WorkspaceError("Symbolic links and junctions are not supported in a workspace.")
        try:
            candidate.resolve().relative_to(self.root)
        except (ValueError, OSError, RuntimeError) as exc:
            raise WorkspaceError("The path is outside the workspace or cannot be resolved.") from exc
        return candidate

    def markdown_path(self, value: str | Path) -> Path:
        path = self.path(value)
        if path.suffix.lower() != ".md":
            raise WorkspaceError("Markdown documents must end in .md.")
        return path

    def children(self, folder: str | Path | None = None) -> list[Path]:
        path = self.path(folder or self.root, allow_root=True)
        try:
            items = []
            for child in path.iterdir():
                if is_link(child):
                    continue
                # Do not offer names the application cannot safely operate on.
                try:
                    validate_name(child.name)
                except WorkspaceError:
                    continue
                if child.is_dir() or (child.is_file() and child.suffix.lower() == ".md"):
                    items.append(child)
            return sorted(items, key=lambda p: (not p.is_dir(), p.name.casefold()))
        except OSError as exc:
            raise WorkspaceError(f"Cannot list {path.name}: {exc}") from exc

    def read(self, value: str | Path) -> Loaded:
        path = self.markdown_path(value)
        try:
            if not path.is_file():
                raise WorkspaceError(f"Cannot read {path.name}: the regular file is missing or unavailable.")
            with path.open("rb") as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise WorkspaceError("Only regular Markdown files can be opened.")
                data = stream.read(MAX_BYTES + 1)
                after = os.fstat(stream.fileno())
            if len(data) > MAX_BYTES:
                raise WorkspaceError("This beta supports documents up to 5 MiB.")
            if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                raise ConflictError("The file changed while it was being read. Try opening it again.")
            self.path(path)
            text = data.decode("utf-8-sig")
            if "\x00" in text:
                raise WorkspaceError("The file contains binary data, not Markdown text.")
            newline = "\r\n" if b"\r\n" in data else "\n"
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            revision = Revision(hashlib.sha256(data).hexdigest(), len(data),
                                after.st_mtime_ns, after.st_ino)
            return Loaded(path, text, revision, newline, data.startswith(b"\xef\xbb\xbf"))
        except (OSError, UnicodeError) as exc:
            raise WorkspaceError(f"Cannot read {path.name}: {exc}") from exc

    def check_revision(self, path: Path, expected: Revision) -> None:
        try:
            actual = self.read(path).revision
        except WorkspaceError as exc:
            raise ConflictError("The original file is missing or unreadable. Your text is still "
                                "in the editor; use Save As to preserve it.") from exc
        if actual != expected:
            raise ConflictError("The file changed outside UPT. Reload it, or use Save As "
                                "with a new name to keep your edits. UPT did not overwrite it.")

    def write(self, value: str | Path, text: str, expected: Revision | None = None,
              *, newline: str = "\n", bom: bool = False) -> Loaded:
        """None means create-only; an existing target is never silently replaced."""
        path = self.markdown_path(value)
        if "\x00" in text:
            raise WorkspaceError("Documents cannot contain null characters.")
        data = (("\ufeff" if bom else "") + text.replace("\r\n", "\n").replace("\r", "\n")
                .replace("\n", newline)).encode("utf-8")
        if len(data) > MAX_BYTES:
            raise WorkspaceError("This beta supports documents up to 5 MiB. Your edits remain open.")
        temporary = None
        try:
            if expected is not None:
                self.check_revision(path, expected)
                mode = path.stat().st_mode
                if not mode & 0o222:
                    raise PermissionError("The document is read-only.")
            else:
                mode = None
                if path.exists():
                    raise WorkspaceError("A file or folder already has that name. Choose a new name.")
            with tempfile.NamedTemporaryFile(prefix=".upt-", suffix=".upt-tmp",
                                             dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if mode is not None:
                os.chmod(temporary, stat.S_IMODE(mode))
            self.markdown_path(path)
            if expected is not None:
                self.check_revision(path, expected)
                os.replace(temporary, path)
            else:
                commit_new(temporary, path)
            return self.read(path)
        except OSError as exc:
            raise WorkspaceError(f"Cannot save {path.name}: {exc}. Your edits remain open.") from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass  # A leftover temp file is safer than deleting a document.

    def create_folder(self, parent: str | Path, name: str) -> Path:
        path = self.path(self.path(parent, allow_root=True) / validate_name(name))
        try:
            path.mkdir()
            return path
        except OSError as exc:
            raise WorkspaceError(f"Cannot create folder: {exc}") from exc

    def rename(self, value: str | Path, name: str) -> Path:
        source = self.path(value)
        target = self.path(source.parent / validate_name(name))
        try:
            if source.is_file() and target.suffix.lower() != ".md":
                raise WorkspaceError("Keep the .md extension when renaming a document.")
            if source == target and source.exists():
                return source
            if target.exists():
                raise WorkspaceError("A file or folder already has that name.")
            # Refuse risky non-regular filesystem entries.
            if not source.is_dir() and not source.is_file():
                raise WorkspaceError("The selected item is no longer available.")
            source.rename(target)
            return target
        except OSError as exc:
            raise WorkspaceError(f"Cannot rename {source.name}: {exc}") from exc

    def delete(self, value: str | Path, expected: Revision | None = None) -> None:
        """Folders must be empty, including hidden and non-Markdown files."""
        path = self.path(value)
        try:
            if path.is_dir():
                path.rmdir()
            else:
                if expected is None:
                    raise WorkspaceError("Read the document before deleting it.")
                self.check_revision(path, expected)
                path.unlink()
        except OSError as exc:
            raise WorkspaceError(f"Cannot delete {path.name}: {exc}. Folders must be completely empty.") from exc
