from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QCloseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from upt.app import MainWindow
from upt.document import Document
from upt.settings import Settings


@pytest.fixture
def window(qapp, tmp_path, monkeypatch):
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: messages.append(str(text)))
    widget = MainWindow(Settings(tmp_path / "session.json"), restore=False)
    widget.messages = messages
    widget.show()
    qapp.processEvents()
    yield widget
    widget._set_document(Document())
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def open_note(window, workspace, text="original"):
    loaded = workspace.write("note.md", text)
    assert window.switch_workspace(workspace.root)
    assert window.open_document(loaded.path)
    return loaded.path


def answer(monkeypatch, choice):
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: choice)


def test_real_editor_keys_preview_undo_redo_and_save(window, workspace, qapp):
    path = open_note(window, workspace, "")
    window.editor.setFocus()
    QTest.keyClicks(window.editor, "# Hello")
    QTest.qWait(300)
    assert window.document.dirty and "Unsaved" in window.windowTitle()
    assert "Hello" in window.preview.toPlainText()
    window.editor.undo()
    assert window.editor.toPlainText() == "" and not window.document.dirty
    window.editor.redo()
    assert window.document.text == "# Hello"
    # QAction shortcut travels through Qt's event system.
    QTest.keyClick(window.editor, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    qapp.processEvents()
    assert path.read_text(encoding="utf-8") == "# Hello"
    assert not window.document.dirty and not window.messages


@pytest.mark.parametrize("choice,switched", [(QMessageBox.StandardButton.Cancel, False),
                                            (QMessageBox.StandardButton.Discard, True),
                                            (QMessageBox.StandardButton.Save, True)])
def test_switch_prompt_choices(window, workspace, monkeypatch, choice, switched):
    path = open_note(window, workspace)
    other = workspace.write("other.md", "other").path
    window.editor.setPlainText("my edits")
    answer(monkeypatch, choice)
    assert window.open_document(other) is switched
    assert window.document.path == (other if switched else path)
    assert path.read_text() == ("my edits" if choice == QMessageBox.StandardButton.Save else "original")
    if not switched:
        assert window.document.text == "my edits"


def test_failed_save_prevents_switch_and_close(window, workspace, monkeypatch):
    path = open_note(window, workspace)
    other = workspace.write("other.md", "other").path
    window.editor.setPlainText("my edits")
    path.write_text("external", encoding="utf-8")
    answer(monkeypatch, QMessageBox.StandardButton.Save)
    assert not window.open_document(other)
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()
    assert window.document.text == "my edits" and path.read_text() == "external"
    assert window.messages


def test_failed_open_does_not_discard_editor(window, workspace):
    open_note(window, workspace)
    window.editor.setPlainText("my edits")
    assert not window.open_document(workspace.root / "missing.md")
    assert window.document.text == "my edits" and window.document.dirty
    assert window.messages


def test_save_as_cancel_and_existing_targets(window, workspace, monkeypatch):
    path = open_note(window, workspace)
    window.editor.setPlainText("my edits")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    assert not window.save_as() and window.document.dirty
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(path), ""))
    assert not window.save_as() and path.read_text() == "original"
    target = workspace.root / "copy.md"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), ""))
    assert window.save_as()
    assert target.read_text() == "my edits" and not window.document.dirty


def test_save_as_outside_workspace_rejected(window, workspace, tmp_path, monkeypatch):
    open_note(window, workspace)
    window.editor.setPlainText("my edits")
    target = tmp_path / "outside.md"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(target), ""))
    assert not window.save_as()
    assert not target.exists() and window.document.dirty


def test_external_notice_reload_cancel_and_reload(window, workspace, monkeypatch):
    path = open_note(window, workspace)
    window.editor.setPlainText("my edits")
    path.write_text("external", encoding="utf-8")
    window.check_external()
    assert window.disk_changed and "disk version changed" in window.notice.text()
    answer(monkeypatch, QMessageBox.StandardButton.Cancel)
    window.reload_document()
    assert window.document.text == "my edits"
    answer(monkeypatch, QMessageBox.StandardButton.Discard)
    window.reload_document()
    assert window.document.text == "external" and not window.document.dirty


def test_reload_missing_preserves_buffer(window, workspace):
    path = open_note(window, workspace)
    path.unlink()
    window.reload_document()
    assert window.document.text == "original" and window.messages


def test_restore_existing_and_missing_document(window, workspace):
    path = workspace.write("last.md", "last note").path
    window.settings.save(workspace.root, path)
    window.restore_session()
    assert window.document.path == path and window.document.text == "last note"
    window._set_document(Document())
    path.unlink()
    window.restore_session()
    assert window.workspace.root == workspace.root and window.document.path is None
    assert "could not be opened" in window.notice.text()


def test_restore_missing_workspace_and_corrupt_settings(window, tmp_path):
    window.settings.save(tmp_path / "gone", None)
    window.restore_session()
    assert window.workspace is None and "unavailable" in window.notice.text()
    window.settings.path.write_text("{invalid")
    window.restore_session()
    assert "restore" in window.notice.text()


def test_nested_tree_refresh_and_file_actions(window, workspace, monkeypatch):
    folder = workspace.create_folder(workspace.root, "folder")
    workspace.write(folder / "nested.md", "nested")
    window.switch_workspace(workspace.root)
    item = window.tree.topLevelItem(0)
    item.setExpanded(True)
    assert item.child(0).text(0) == "nested.md"
    window.tree.setCurrentItem(item)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("new folder", True))
    window.new_folder()
    assert (folder / "new folder").is_dir()
    # Refresh retains expansion and exposes the new item.
    item = window.tree.topLevelItem(0)
    assert item.childCount() == 2


def test_rename_active_note_keeps_unsaved_buffer(window, workspace, monkeypatch):
    path = open_note(window, workspace)
    window.refresh_tree()
    window.tree.setCurrentItem(window.tree.topLevelItem(0))
    window.editor.setPlainText("unsaved")
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("renamed.md", True))
    window.rename_selected()
    assert window.document.path.name == "renamed.md" and not path.exists()
    assert window.document.dirty and window.document.text == "unsaved"
    assert window.save() and workspace.read("renamed.md").text == "unsaved"


def test_delete_confirmation_cancel_and_confirm(window, workspace, monkeypatch):
    path = open_note(window, workspace)
    window.refresh_tree()
    window.tree.setCurrentItem(window.tree.topLevelItem(0))
    answer(monkeypatch, QMessageBox.StandardButton.Cancel)
    window.delete_selected()
    assert path.exists()
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    window.delete_selected()
    assert not path.exists() and window.document.path is None


def test_unsaved_workspace_change_cancel(window, workspace, tmp_path, monkeypatch):
    open_note(window, workspace)
    window.editor.setPlainText("keep me")
    other = tmp_path / "other"
    other.mkdir()
    answer(monkeypatch, QMessageBox.StandardButton.Cancel)
    assert not window.switch_workspace(other)
    assert window.workspace.root == workspace.root and window.document.text == "keep me"


def test_resource_loader_blocks_every_scheme(window):
    for value in ("https://example.com/image.png", "file:///secret", "data:image/png,AAAA", "qrc:/x"):
        assert window.preview.loadResource(2, QUrl(value)).isEmpty()
    assert not window.preview.openExternalLinks() and not window.preview.openLinks()


def test_links_require_confirmation_and_stay_in_workspace(window, workspace, monkeypatch):
    from upt.app import QDesktopServices
    path = open_note(window, workspace)
    calls = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: calls.append(url) or True)
    answer(monkeypatch, QMessageBox.StandardButton.Cancel)
    window.follow_link(QUrl("https://example.com"))
    assert not calls
    answer(monkeypatch, QMessageBox.StandardButton.Yes)
    window.follow_link(QUrl("https://example.com"))
    assert len(calls) == 1
    window.follow_link(QUrl("javascript:alert(1)"))
    window.follow_link(QUrl("../outside.md"))
    assert window.document.path == path and len(calls) == 1 and window.messages


def test_find_wrap_and_preview_toggle(window, workspace):
    open_note(window, workspace, "hello\nworld\nhello")
    window.show_find()
    window.find_input.setText("world")
    window.find_next()
    assert window.editor.textCursor().selectedText() == "world"
    window.find_next()
    assert window.editor.textCursor().selectedText() == "world"
    window.preview_action.setChecked(False)
    window.toggle_preview()
    assert window.panes.widget(1).isHidden()


def test_notice_stays_compact_and_find_edits_use_focus(window, workspace, qapp):
    open_note(window, workspace)
    window.new_note()
    qapp.processEvents()
    assert 20 < window.notice.height() < 100
    assert window.editor.height() > window.height() // 2
    window.show_find()
    window.find_input.setText("search term")
    window.edit_command("selectAll")
    assert window.find_input.selectedText() == "search term"


def test_cancel_tree_switch_keeps_active_selection(window, workspace, monkeypatch):
    path = open_note(window, workspace)
    workspace.write("other.md", "other")
    window.refresh_tree()
    window.editor.setPlainText("unsaved")
    answer(monkeypatch, QMessageBox.StandardButton.Cancel)
    other = window.tree.topLevelItem(1)
    window.tree.setCurrentItem(other)
    window.tree_clicked(other)
    assert window.document.path == path
    assert window.selected_path() == path


def test_empty_workspace_has_useful_visible_state(window, workspace):
    window.switch_workspace(workspace.root)
    assert window.empty_sidebar.isVisible()
    assert "Ctrl+N" in window.empty_sidebar.text()
    workspace.write("first.md", "first")
    window.refresh_tree()
    assert not window.empty_sidebar.isVisible()


def test_parent_folder_rename_preserves_open_dirty_note(window, workspace, monkeypatch):
    folder = workspace.create_folder(workspace.root, "Projects")
    path = workspace.write(folder / "note.md", "original").path
    window.switch_workspace(workspace.root)
    window.open_document(path)
    window.editor.setPlainText("unsaved work")
    window.tree.setCurrentItem(window.tree.topLevelItem(0))
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("Renamed", True))
    window.rename_selected()
    assert window.document.path == workspace.root / "Renamed" / "note.md"
    assert window.document.dirty and not path.exists()
    assert window.save()
    assert workspace.read("Renamed/note.md").text == "unsaved work"


def test_restore_selects_nested_document_and_rejects_outside_path(window, workspace, tmp_path):
    folder = workspace.create_folder(workspace.root, "Projects")
    path = workspace.write(folder / "note.md", "note").path
    window.settings.save(workspace.root, path)
    window.restore_session()
    assert window.tree.topLevelItem(0).isExpanded()
    assert window.selected_path() == path
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    window._set_document(Document())
    window.settings.save(workspace.root, outside)
    window.restore_session()
    assert window.document.path is None
    assert "could not be opened" in window.notice.text()
