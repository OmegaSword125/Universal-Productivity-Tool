import os
from pathlib import Path
import stat

import pytest

from upt.document import Document
from upt.storage import ConflictError, MAX_BYTES, Workspace, WorkspaceError, validate_name


@pytest.mark.parametrize("name", ["", ".", "..", "../escape", "a/b", "a\\b", "C:note", "a?b",
                                   "a*b", "a|b", 'a"b', "a<b", "a>b", " tail", "tail ",
                                   "tail.", "CON", "nul.md", "LPT9.txt", "COM1.md", "a\x00b",
                                   "a\nb", "a\x7fb", "n" * 201])
def test_unsafe_names(name):
    with pytest.raises(WorkspaceError):
        validate_name(name)


@pytest.mark.parametrize("name", ["Résumé.md", "my note.md", "2026-11-16", "COM10.md", ".hidden.md"])
def test_portable_names(name):
    assert validate_name(name) == name


def test_nested_create_read_rename_delete(workspace):
    folder = workspace.create_folder(workspace.root, "Projects")
    nested = workspace.create_folder(folder, "Notes")
    loaded = workspace.write(nested / "hello.md", "# Héllo 🌿\n")
    assert workspace.read(loaded.path).text == "# Héllo 🌿\n"
    renamed = workspace.rename(loaded.path, "hello again.md")
    assert not loaded.path.exists()
    workspace.delete(renamed, workspace.read(renamed).revision)
    workspace.delete(nested)
    workspace.delete(folder)
    assert workspace.children() == []


def test_tree_folders_first_markdown_only(workspace):
    workspace.write("z.MD", "")
    (workspace.root / "ignore.txt").write_text("hidden")
    workspace.create_folder(workspace.root, "Alpha")
    assert [p.name for p in workspace.children()] == ["Alpha", "z.MD"]


@pytest.mark.parametrize("relative", ["../escape.md", "nested/../../escape.md", "a:bad.md"])
def test_path_traversal(workspace, relative):
    with pytest.raises(WorkspaceError):
        workspace.write(relative, "do not write")


def test_outside_and_root_protected(workspace, tmp_path):
    for operation in [lambda: workspace.path(tmp_path / "outside.md"),
                      lambda: workspace.delete(workspace.root),
                      lambda: workspace.rename(workspace.root, "new")]:
        with pytest.raises(WorkspaceError):
            operation()


def test_symlink_escape_rejected(workspace, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = workspace.root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink creation unavailable: {exc}")
    with pytest.raises(WorkspaceError):
        workspace.write(link / "escape.md", "unsafe")
    assert link not in workspace.children()
    assert not (outside / "escape.md").exists()


def test_junction_or_symlink_guard_without_privileges(workspace, monkeypatch):
    import upt.storage as storage
    fake = workspace.root / "linked"
    monkeypatch.setattr(storage, "is_link", lambda p: p == fake)
    with pytest.raises(WorkspaceError, match="Symbolic"):
        workspace.path(fake / "escape.md")


def test_create_never_overwrites(workspace):
    workspace.write("note.md", "original")
    with pytest.raises(WorkspaceError):
        workspace.write("note.md", "replacement")
    assert workspace.read("note.md").text == "original"


def test_atomic_create_race_does_not_overwrite(workspace, monkeypatch):
    import upt.storage as storage
    original_commit = storage.commit_new

    def competing_create(source, target):
        Path(target).write_text("other writer", encoding="utf-8")
        original_commit(source, target)

    monkeypatch.setattr(storage, "commit_new", competing_create)
    with pytest.raises(WorkspaceError):
        workspace.write("note.md", "mine")
    assert workspace.read("note.md").text == "other writer"
    assert not list(workspace.root.glob("*.upt-tmp"))


def test_external_edits_preserve_dirty_buffer(workspace):
    doc = Document.from_loaded(workspace.write("note.md", "original"))
    doc.text = "my changes"
    doc.path.write_text("external changes", encoding="utf-8")
    with pytest.raises(ConflictError):
        doc.save(workspace)
    assert doc.dirty and doc.text == "my changes"
    assert doc.path.read_text(encoding="utf-8") == "external changes"
    doc.save(workspace, workspace.root / "my-copy.md")
    assert not doc.dirty and doc.path.name == "my-copy.md"


def test_deleted_original_not_silently_recreated(workspace):
    doc = Document.from_loaded(workspace.write("note.md", "original"))
    doc.text = "keep me"
    doc.path.unlink()
    with pytest.raises(ConflictError):
        doc.save(workspace)
    assert doc.dirty and not doc.path.exists()


def test_check_immediately_before_replace(workspace, monkeypatch):
    doc = Document.from_loaded(workspace.write("note.md", "original"))
    doc.text = "mine"
    original = workspace.check_revision
    calls = 0

    def change_on_second_check(path, expected):
        nonlocal calls
        calls += 1
        if calls == 2:
            path.write_text("external", encoding="utf-8")
        original(path, expected)

    monkeypatch.setattr(workspace, "check_revision", change_on_second_check)
    with pytest.raises(ConflictError):
        doc.save(workspace)
    assert doc.path.read_text() == "external" and doc.dirty


def test_replace_failure_keeps_original_and_buffer(workspace, monkeypatch):
    doc = Document.from_loaded(workspace.write("note.md", "original"))
    doc.text = "unsaved"

    def denied(*args):
        raise PermissionError("injected permission denial")

    monkeypatch.setattr(os, "replace", denied)
    with pytest.raises(WorkspaceError, match="permission denial"):
        doc.save(workspace)
    assert workspace.read("note.md").text == "original"
    assert doc.dirty and doc.text == "unsaved"
    assert not list(workspace.root.glob("*.upt-tmp"))


def test_read_only_save_is_visible(workspace):
    doc = Document.from_loaded(workspace.write("readonly.md", "original"))
    original_mode = doc.path.stat().st_mode
    doc.path.chmod(stat.S_IREAD)
    try:
        doc.text = "unsaved"
        with pytest.raises(WorkspaceError, match="read-only"):
            doc.save(workspace)
        assert doc.dirty and workspace.read(doc.path).text == "original"
    finally:
        doc.path.chmod(original_mode)


def test_preserve_crlf_and_utf8_bom(workspace):
    path = workspace.root / "windows.md"
    path.write_bytes(b"\xef\xbb\xbf# Note\r\nBody\r\n")
    doc = Document.from_loaded(workspace.read(path))
    assert doc.text == "# Note\nBody\n"
    doc.text += "Added\n"
    doc.save(workspace)
    assert path.read_bytes() == b"\xef\xbb\xbf# Note\r\nBody\r\nAdded\r\n"


def test_rename_collision_and_extension(workspace):
    a = workspace.write("a.md", "A")
    workspace.write("b.md", "B")
    for name in ("b.md", "a.txt", "../bad.md"):
        with pytest.raises(WorkspaceError):
            workspace.rename(a.path, name)
    assert workspace.read("a.md").text == "A" and workspace.read("b.md").text == "B"


def test_delete_checks_external_changes(workspace):
    loaded = workspace.write("note.md", "A")
    loaded.path.write_text("B", encoding="utf-8")
    with pytest.raises(ConflictError):
        workspace.delete(loaded.path, loaded.revision)
    assert loaded.path.exists()
    with pytest.raises(WorkspaceError):
        workspace.delete(loaded.path)


def test_nonempty_folder_delete_never_removes_hidden_data(workspace):
    folder = workspace.create_folder(workspace.root, "folder")
    (folder / ".important.txt").write_text("valuable", encoding="utf-8")
    with pytest.raises(WorkspaceError):
        workspace.delete(folder)
    assert (folder / ".important.txt").read_text() == "valuable"


def test_invalid_missing_and_large_files(workspace):
    for data in (b"\xff\xfe", b"text\x00binary", b"a" * (MAX_BYTES + 1)):
        path = workspace.root / "bad.md"
        path.write_bytes(data)
        with pytest.raises(WorkspaceError):
            workspace.read(path)
    with pytest.raises(WorkspaceError):
        workspace.read("missing.md")
    with pytest.raises(WorkspaceError):
        workspace.write("large.md", "x" * (MAX_BYTES + 1))
    with pytest.raises(WorkspaceError):
        workspace.write("not-markdown.txt", "text")


def test_missing_workspace_and_parent_errors(workspace, tmp_path):
    with pytest.raises(WorkspaceError):
        Workspace(tmp_path / "missing")
    with pytest.raises(WorkspaceError):
        workspace.write("missing/note.md", "text")
    workspace.root.rmdir()
    with pytest.raises(WorkspaceError):
        workspace.write("note.md", "text")


def test_dirty_returns_to_clean_after_undo_value(workspace):
    doc = Document.from_loaded(workspace.write("note.md", "saved"))
    doc.text = "edited"
    assert doc.dirty
    doc.text = "saved"
    assert not doc.dirty


@pytest.mark.parametrize("operation,method", [("list", "iterdir"), ("read", "open"),
                                             ("mkdir", "mkdir"), ("rename", "rename"),
                                             ("delete", "unlink")])
def test_permission_errors_visible_for_filesystem_operations(workspace, monkeypatch, operation, method):
    loaded = workspace.write("note.md", "keep this")

    def denied(*args, **kwargs):
        raise PermissionError("permission denied for test")

    monkeypatch.setattr(Path, method, denied)
    operations = {"list": lambda: workspace.children(), "read": lambda: workspace.read(loaded.path),
                  "mkdir": lambda: workspace.create_folder(workspace.root, "new"),
                  "rename": lambda: workspace.rename(loaded.path, "renamed.md"),
                  "delete": lambda: workspace.delete(loaded.path, loaded.revision)}
    with pytest.raises(WorkspaceError, match="permission denied"):
        operations[operation]()


def test_permission_failure_at_boundary_is_user_readable(workspace, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("folder inaccessible")

    monkeypatch.setattr(Path, "is_dir", denied)
    with pytest.raises(WorkspaceError, match="folder inaccessible"):
        workspace.path("note.md")
