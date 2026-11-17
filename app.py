"""Qt desktop UI. Filesystem work stays in storage.py; no browser engine is used."""
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

from PySide6.QtCore import QByteArray, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QFont, QKeySequence, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
    QSizePolicy, QStyle, QTextBrowser, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .document import Document
from .rendering import render_markdown, safe_link
from .settings import Settings
from .storage import Workspace, WorkspaceError
from .theme import STYLE


class SafePreview(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.setOpenExternalLinks(False)
        self.setOpenLinks(False)
        self.setAccessibleName("Markdown preview")
        self.setMinimumWidth(180)

    def loadResource(self, resource_type, name):  # noqa: N802 (Qt virtual)
        # No automatic local, network, data, qrc, or other resource access.
        return QByteArray()


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None, *, restore: bool = True):
        super().__init__()
        self.settings = settings or Settings()
        self.workspace: Workspace | None = None
        self.document = Document()
        self.disk_changed = False
        self.loading = False
        self.tree_loading = False
        self.setMinimumSize(820, 540)
        self.resize(1280, 820)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._build_actions()
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(250)
        self.preview_timer.timeout.connect(self.update_preview)
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(2000)
        self.poll_timer.timeout.connect(self.check_external)
        self.poll_timer.start()
        self.editor.textChanged.connect(self.text_changed)
        self.editor.cursorPositionChanged.connect(self.update_status)
        self.tree.itemClicked.connect(self.tree_clicked)
        self.tree.itemActivated.connect(self.tree_clicked)
        self.tree.itemExpanded.connect(self.expand_folder)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.context_menu)
        self.preview.anchorClicked.connect(self.follow_link)
        self._set_document(Document())
        self.update_workspace_ui()
        if restore:
            QTimer.singleShot(0, self.restore_session)

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.notice = QLabel()
        self.notice.setTextFormat(Qt.TextFormat.PlainText)
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        self.notice.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.notice.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.notice.hide()
        layout.addWidget(self.notice)
        self.outer = QSplitter(Qt.Orientation.Horizontal)
        sidebar = QWidget()
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        self.workspace_title = QLabel("WORKSPACE")
        self.workspace_title.setTextFormat(Qt.TextFormat.PlainText)
        self.workspace_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.workspace_title.setObjectName("workspaceTitle")
        side_layout.addWidget(self.workspace_title)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName("Workspace folders and Markdown files")
        self.tree.setMinimumWidth(170)
        side_layout.addWidget(self.tree)
        self.empty_sidebar = QLabel("Open a folder to organize your Markdown files.")
        self.empty_sidebar.setWordWrap(True)
        self.empty_sidebar.setMargin(16)
        side_layout.addWidget(self.empty_sidebar)
        self.open_button = QPushButton("Open workspace…")
        self.open_button.clicked.connect(lambda: self.choose_workspace())
        side_layout.addWidget(self.open_button)
        self.outer.addWidget(sidebar)
        self.panes = QSplitter(Qt.Orientation.Horizontal)
        editor_pane = QWidget()
        edit_layout = QVBoxLayout(editor_pane)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(0)
        self.editor_title = QLabel("EDITOR")
        self.editor_title.setTextFormat(Qt.TextFormat.PlainText)
        self.editor_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.editor_title.setObjectName("paneTitle")
        edit_layout.addWidget(self.editor_title)
        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName("Markdown editor")
        self.editor.setPlaceholderText("A quiet place for your notes.\n\nOpen a workspace, then create a note with Ctrl+N.")
        font = QFont("Cascadia Mono", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(font)
        self.editor.setTabStopDistance(self.editor.fontMetrics().horizontalAdvance(" ") * 4)
        edit_layout.addWidget(self.editor)
        preview_pane = QWidget()
        preview_layout = QVBoxLayout(preview_pane)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)
        self.preview_title = QLabel("PREVIEW  ·  Live")
        self.preview_title.setObjectName("paneTitle")
        preview_layout.addWidget(self.preview_title)
        self.preview = SafePreview()
        preview_layout.addWidget(self.preview)
        self.panes.addWidget(editor_pane)
        self.panes.addWidget(preview_pane)
        self.panes.setSizes([530, 480])
        self.outer.addWidget(self.panes)
        self.outer.setSizes([250, 1030])
        self.outer.setStretchFactor(1, 1)
        layout.addWidget(self.outer, 1)
        self.setCentralWidget(central)
        self.statusBar().setSizeGripEnabled(True)
        self.position_label = QLabel()
        self.statusBar().addPermanentWidget(self.position_label)
        self.find_bar = QWidget()
        self.find_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        find_layout = QHBoxLayout(self.find_bar)
        find_layout.setContentsMargins(10, 6, 10, 6)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find in this document…")
        self.find_input.setAccessibleName("Find text")
        self.find_input.returnPressed.connect(self.find_next)
        next_button = QPushButton("Next")
        next_button.clicked.connect(self.find_next)
        done_button = QPushButton("Close find")
        done_button.clicked.connect(self.hide_find)
        find_layout.addWidget(self.find_input)
        find_layout.addWidget(next_button)
        find_layout.addWidget(done_button)
        layout.addWidget(self.find_bar)
        self.find_bar.hide()

    def action(self, menu, text, shortcut, callback):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(lambda checked=False: callback())
        menu.addAction(action)
        return action

    def _build_actions(self):
        file_menu = self.menuBar().addMenu("&File")
        self.open_workspace_action = self.action(file_menu, "Open &workspace…", "Ctrl+Shift+O", self.choose_workspace)
        self.new_action = self.action(file_menu, "&New note", "Ctrl+N", self.new_note)
        self.folder_action = self.action(file_menu, "New &folder…", "Ctrl+Shift+N", self.new_folder)
        self.open_action = self.action(file_menu, "&Open note…", "Ctrl+O", self.choose_note)
        file_menu.addSeparator()
        self.save_action = self.action(file_menu, "&Save", "Ctrl+S", self.save)
        self.save_as_action = self.action(file_menu, "Save &as…", "Ctrl+Shift+S", self.save_as)
        self.reload_action = self.action(file_menu, "&Reload from disk…", "Ctrl+Shift+R", self.reload_document)
        self.action(file_menu, "&Close note", "Ctrl+W", self.close_document)
        file_menu.addSeparator()
        self.action(file_menu, "E&xit", "Ctrl+Q", self.close)
        edit_menu = self.menuBar().addMenu("&Edit")
        for text, shortcut, method in [("&Undo", "Ctrl+Z", "undo"),
                                       ("&Redo", "Ctrl+Shift+Z", "redo"),
                                       ("Cu&t", "Ctrl+X", "cut"),
                                       ("&Copy", "Ctrl+C", "copy"),
                                       ("&Paste", "Ctrl+V", "paste"),
                                       ("Select &all", "Ctrl+A", "selectAll")]:
            self.action(edit_menu, text, shortcut, lambda m=method: self.edit_command(m))
        edit_menu.addSeparator()
        self.action(edit_menu, "&Find…", "Ctrl+F", self.show_find)
        self.action(edit_menu, "Find &next", "F3", self.find_next)
        workspace_menu = self.menuBar().addMenu("&Workspace")
        self.rename_action = self.action(workspace_menu, "&Rename selected…", "F2", self.rename_selected)
        self.delete_action = self.action(workspace_menu, "&Delete selected…", "", self.delete_selected)
        self.action(workspace_menu, "Re&fresh files", "F5", self.refresh_tree)
        view_menu = self.menuBar().addMenu("&View")
        self.preview_action = self.action(view_menu, "Show &preview", "Ctrl+E", self.toggle_preview)
        self.preview_action.setCheckable(True)
        self.preview_action.setChecked(True)
        self.action(view_menu, "Refresh preview", "Ctrl+R", self.update_preview)
        self.action(view_menu, "Focus editor", "Ctrl+1", self.editor.setFocus)
        self.action(view_menu, "Focus files", "Ctrl+2", self.tree.setFocus)
        self.action(view_menu, "Focus preview", "Ctrl+3", self.preview.setFocus)
        help_menu = self.menuBar().addMenu("&Help")
        self.action(help_menu, "&Keyboard shortcuts", "F1", self.show_shortcuts)
        self.action(help_menu, "&About UPT", "", self.show_about)
        toolbar = QToolBar("Main actions")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.addToolBar(toolbar)
        for action in (self.open_workspace_action, self.new_action, self.save_action,
                       self.save_as_action, self.reload_action):
            toolbar.addAction(action)
        toolbar.addSeparator()
        toolbar.addAction(self.preview_action)

    def inform(self, text):
        self.notice.setText(text)
        self.notice.setVisible(bool(text))

    def error(self, exc):
        QMessageBox.warning(self, "UPT — action could not be completed",
                            "<p>" + escape(str(exc)).replace("\n", "<br>") + "</p>")

    def edit_command(self, method):
        focused = QApplication.focusWidget()
        target = focused if isinstance(focused, (QPlainTextEdit, QTextBrowser, QLineEdit)) else self.editor
        callback = getattr(target, method, None)
        if callback:
            callback()

    def persist(self):
        try:
            self.settings.save(self.workspace.root if self.workspace else None, self.document.path)
        except OSError as exc:
            self.inform(f"Your document is safe, but UPT could not remember this session: {exc}")

    def restore_session(self):
        try:
            data = self.settings.load()
        except ValueError as exc:
            self.inform(str(exc) + ". Open a workspace to continue.")
            return
        if not data.get("workspace"):
            return
        try:
            workspace = Workspace(data["workspace"])
        except WorkspaceError as exc:
            self.inform(f"Previous workspace unavailable. Open a folder to continue. {exc}")
            return
        self.workspace = workspace
        self.update_workspace_ui()
        self.refresh_tree()
        if data.get("document"):
            try:
                self._set_document(Document.from_loaded(workspace.read(data["document"])))
                self.refresh_tree()
                self.select_current_document()
            except WorkspaceError as exc:
                self.inform(f"Workspace restored; the previous note could not be opened. {exc}")

    def update_workspace_ui(self):
        available = self.workspace is not None
        self.workspace_title.setText(self.workspace.root.name if available else "WORKSPACE")
        self.workspace_title.setToolTip(str(self.workspace.root) if available else "No workspace open")
        self.update_tree_empty()
        self.editor.setEnabled(available)
        for action in (self.new_action, self.folder_action, self.open_action,
                       self.save_action, self.save_as_action, self.rename_action, self.delete_action):
            action.setEnabled(available)
        self.reload_action.setEnabled(available and self.document.path is not None)
        self.update_status()

    def update_tree_empty(self):
        self.empty_sidebar.setText("No Markdown notes to show. Press Ctrl+N to create your first note."
                                   if self.workspace else "Open a folder to organize your Markdown files.")
        self.empty_sidebar.setVisible(self.workspace is None or self.tree.topLevelItemCount() == 0)

    def choose_workspace(self):
        value = QFileDialog.getExistingDirectory(self, "Choose a local workspace",
                                                str(self.workspace.root) if self.workspace else "")
        if value:
            self.switch_workspace(Path(value))

    def switch_workspace(self, root: Path) -> bool:
        try:
            workspace = Workspace(root)
            workspace.children()
        except WorkspaceError as exc:
            self.error(exc)
            return False
        if not self.maybe_save():
            return False
        self.workspace = workspace
        self._set_document(Document())
        self.inform("")
        self.refresh_tree()
        self.update_workspace_ui()
        self.persist()
        return True

    def selected_path(self) -> Path | None:
        item = self.tree.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else None

    def selected_folder(self) -> Path:
        path = self.selected_path()
        return path if path and path.is_dir() else path.parent if path else self.workspace.root

    def _add_children(self, parent, folder):
        for path in self.workspace.children(folder):
            item = QTreeWidgetItem([path.name])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setToolTip(0, str(path.relative_to(self.workspace.root)))
            is_folder = path.is_dir()
            icon = QStyle.StandardPixmap.SP_DirIcon if is_folder else QStyle.StandardPixmap.SP_FileIcon
            item.setIcon(0, self.style().standardIcon(icon))
            parent.addChild(item)
            if is_folder:
                item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

    def refresh_tree(self):
        if not self.workspace:
            return
        expanded = set()
        selected = self.selected_path()

        def collect(parent):
            for i in range(parent.childCount()):
                item = parent.child(i)
                if item.isExpanded():
                    expanded.add(item.data(0, Qt.ItemDataRole.UserRole))
                    collect(item)

        collect(self.tree.invisibleRootItem())
        if self.document.path:
            expanded.update(self.document.path.parents)
        self.tree_loading = True
        self.tree.clear()
        errors = []
        try:
            self._add_children(self.tree.invisibleRootItem(), self.workspace.root)

            def restore(parent):
                for i in range(parent.childCount()):
                    item = parent.child(i)
                    path = item.data(0, Qt.ItemDataRole.UserRole)
                    if path in expanded and path.is_dir():
                        try:
                            self._add_children(item, path)
                            item.setData(0, Qt.ItemDataRole.UserRole + 1, True)
                            item.setExpanded(True)
                            restore(item)
                        except WorkspaceError as exc:
                            errors.append(str(exc))
                    if path == (selected or self.document.path):
                        self.tree.setCurrentItem(item)

            restore(self.tree.invisibleRootItem())
        except WorkspaceError as exc:
            errors.append(str(exc))
        finally:
            self.tree_loading = False
        self.update_tree_empty()
        if errors:
            self.inform("Some folders could not be read: " + "; ".join(errors))
        elif self.tree.topLevelItemCount() == 0:
            self.statusBar().showMessage("This folder has no Markdown notes yet. Press Ctrl+N to create one.")

    def expand_folder(self, item):
        if self.tree_loading or item.data(0, Qt.ItemDataRole.UserRole + 1):
            return
        try:
            self._add_children(item, item.data(0, Qt.ItemDataRole.UserRole))
            item.setData(0, Qt.ItemDataRole.UserRole + 1, True)
        except WorkspaceError as exc:
            self.error(exc)

    def tree_clicked(self, item, column=0):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and not path.is_dir() and path != self.document.path:
            if not self.open_document(path):
                self.select_current_document()

    def select_current_document(self):
        self.tree.clearSelection()

        def select(parent):
            for i in range(parent.childCount()):
                item = parent.child(i)
                if item.data(0, Qt.ItemDataRole.UserRole) == self.document.path:
                    self.tree.setCurrentItem(item)
                    return True
                if select(item):
                    return True
            return False

        if not select(self.tree.invisibleRootItem()):
            self.tree.setCurrentItem(None)

    def context_menu(self, position):
        item = self.tree.itemAt(position)
        if item:
            self.tree.setCurrentItem(item)
        menu = QMenu(self)
        for action in (self.new_action, self.folder_action):
            menu.addAction(action)
        if item:
            menu.addSeparator()
            menu.addAction(self.rename_action)
            menu.addAction(self.delete_action)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _set_document(self, document):
        self.document = document
        self.disk_changed = False
        self.loading = True
        self.editor.setPlainText(document.text)
        self.editor.document().setModified(False)
        self.loading = False
        self.update_preview()
        self.update_status()
        self.reload_action.setEnabled(document.path is not None)

    def open_document(self, path: Path) -> bool:
        if not self.workspace:
            return False
        # Read first so a failed open cannot discard the current buffer.
        try:
            loaded = self.workspace.read(path)
        except WorkspaceError as exc:
            self.error(exc)
            return False
        if not self.maybe_save():
            return False
        self._set_document(Document.from_loaded(loaded))
        self.inform("")
        self.refresh_tree()
        self.select_current_document()
        self.persist()
        self.editor.setFocus()
        return True

    def choose_note(self):
        if not self.workspace:
            return
        name, _ = QFileDialog.getOpenFileName(self, "Open Markdown note inside workspace",
                                            str(self.workspace.root), "Markdown (*.md *.MD)")
        if name:
            self.open_document(Path(name))

    def new_note(self):
        if not self.workspace or not self.maybe_save():
            return
        self._set_document(Document())
        self.inform("New unsaved note. Save to choose a .md filename inside your workspace.")
        self.persist()
        self.editor.setFocus()

    def new_folder(self):
        if not self.workspace:
            return
        name, ok = QInputDialog.getText(self, "New folder", "Folder name (inside selected folder):")
        if ok:
            try:
                self.workspace.create_folder(self.selected_folder(), name)
                self.refresh_tree()
            except WorkspaceError as exc:
                self.error(exc)

    def text_changed(self):
        if self.loading:
            return
        self.document.text = self.editor.toPlainText()
        self.preview_timer.start()
        self.update_status()

    def update_preview(self):
        position = self.preview.verticalScrollBar().value()
        text = self.editor.toPlainText()
        if not text:
            text = "# Your words, your workspace\n\nWrite Markdown on the left. Your preview appears here.\n\n" \
                   "Try a heading, a list, or a fenced code block. Everything stays on your computer."
        try:
            self.preview.setHtml(render_markdown(text))
            self.preview.verticalScrollBar().setValue(position)
        except Exception as exc:
            self.preview.setPlainText("Preview could not be rendered. Your text is still safe in the editor.")
            self.inform(f"Preview error: {exc}")

    def update_status(self):
        name = self.document.path.name if self.document.path else "Untitled"
        marker = " • Unsaved" if self.document.dirty else ""
        self.setWindowTitle(f"{name}{marker} — UPT 1.0 Beta")
        self.editor_title.setText(f"{name}{marker}")
        self.editor_title.setToolTip(str(self.document.path) if self.document.path else "Unsaved note")
        cursor = self.editor.textCursor()
        self.position_label.setText(f"Ln {cursor.blockNumber() + 1}, Col {cursor.positionInBlock() + 1}  |  UTF-8")
        if self.document.path and self.workspace:
            self.statusBar().showMessage(str(self.document.path.relative_to(self.workspace.root)))
        else:
            self.statusBar().showMessage("Local only · No account · No telemetry")

    def save(self) -> bool:
        if not self.workspace:
            return False
        if self.document.path is None:
            return self.save_as()
        try:
            self.document.save(self.workspace)
        except WorkspaceError as exc:
            self.error(exc)
            return False
        self.editor.document().setModified(False)
        self.disk_changed = False
        self.inform("")
        self.update_status()
        self.persist()
        self.refresh_tree()
        return True

    def save_as(self) -> bool:
        if not self.workspace:
            return False
        folder = self.document.path.parent if self.document.path else self.selected_folder()
        name, _ = QFileDialog.getSaveFileName(self, "Save a new Markdown copy (existing files are protected)",
                                            str(folder / "Untitled.md"), "Markdown (*.md)")
        if not name:
            return False
        target = Path(name)
        if not target.suffix:
            target = target.with_suffix(".md")
        try:
            target = self.workspace.markdown_path(target)
            if target.exists():
                raise WorkspaceError("Save As creates a new file. Choose an unused name; use Save for the current document.")
            self.document.save(self.workspace, target)
        except WorkspaceError as exc:
            self.error(exc)
            return False
        self.editor.document().setModified(False)
        self.disk_changed = False
        self.inform("")
        self.update_status()
        self.reload_action.setEnabled(True)
        self.persist()
        self.refresh_tree()
        return True

    def maybe_save(self) -> bool:
        if not self.document.dirty:
            return True
        choice = QMessageBox.question(self, "Save your changes?",
                                      "This note has unsaved changes. Save before continuing?",
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                      QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Save:
            return self.save()
        return choice == QMessageBox.StandardButton.Discard

    def close_document(self):
        if self.maybe_save():
            self._set_document(Document())
            self.inform("")
            self.persist()

    def reload_document(self):
        if not self.workspace or not self.document.path:
            return
        if self.document.dirty:
            choice = QMessageBox.question(self, "Reload from disk?",
                                          "Reloading replaces your unsaved editor text with the disk version. "
                                          "Use Save As first if you want to keep both versions. Discard your edits?",
                                          QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                                          QMessageBox.StandardButton.Cancel)
            if choice != QMessageBox.StandardButton.Discard:
                return
        try:
            loaded = self.workspace.read(self.document.path)
        except WorkspaceError as exc:
            self.error(exc)
            return
        self._set_document(Document.from_loaded(loaded))
        self.inform("")

    def check_external(self):
        if not self.workspace or not self.document.path or self.disk_changed:
            return
        try:
            self.workspace.check_revision(self.document.path, self.document.revision)
        except WorkspaceError:
            self.disk_changed = True
            self.inform("The disk version changed, moved, or became unreadable. Your editor text is preserved. "
                        "Use Reload from disk to review the current file, or Save As to keep your text separately.")

    def rename_selected(self):
        path = self.selected_path()
        if not self.workspace or not path:
            return
        try:
            expected = (self.document.revision if path == self.document.path else
                        self.workspace.read(path).revision if not path.is_dir() else None)
            name, ok = QInputDialog.getText(self, "Rename selected item", "New name:", text=path.name)
            if not ok:
                return
            if expected:
                self.workspace.check_revision(path, expected)
            target = self.workspace.rename(path, name)
            if self.document.path and self.document.path.is_relative_to(path):
                self.document.path = target / self.document.path.relative_to(path)
                self.update_status()
                self.persist()
            self.refresh_tree()
        except WorkspaceError as exc:
            self.error(exc)

    def delete_selected(self):
        path = self.selected_path()
        if not self.workspace or not path:
            return
        active = path == self.document.path
        if active and not self.maybe_save():
            return
        try:
            revision = (self.document.revision if active else
                        self.workspace.read(path).revision if not path.is_dir() else None)
            choice = QMessageBox.question(self, "Permanently delete?",
                                          f'Permanently delete "{path.name}"? This cannot be undone. '
                                          "Folders must be completely empty (including hidden files).",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                          QMessageBox.StandardButton.Cancel)
            if choice != QMessageBox.StandardButton.Yes:
                return
            self.workspace.delete(path, revision)
            if active:
                self._set_document(Document())
                self.persist()
            self.refresh_tree()
        except WorkspaceError as exc:
            self.error(exc)

    def follow_link(self, url: QUrl):
        value = url.toString()
        if not safe_link(value):
            self.inform("This link is blocked. Only web, email, and workspace Markdown links are supported.")
            return
        parts = urlsplit(value)
        if parts.scheme:
            choice = QMessageBox.question(self, "Open outside UPT?",
                                          "<p>Open this link in your default browser or mail app?</p><p>"
                                          + escape(value) + "</p><p>That application may contact an external service.</p>",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                          QMessageBox.StandardButton.Cancel)
            if choice == QMessageBox.StandardButton.Yes and not QDesktopServices.openUrl(url):
                self.error("The system could not open this link.")
        elif not parts.path:
            self.preview.scrollToAnchor(parts.fragment)
        elif self.workspace:
            base = self.document.path.parent if self.document.path else self.workspace.root
            target = base / unquote(parts.path)
            # The workspace boundary rejects traversal before any read takes place.
            self.open_document(target)

    def toggle_preview(self):
        self.panes.widget(1).setVisible(self.preview_action.isChecked())

    def show_find(self):
        self.find_bar.show()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def hide_find(self):
        self.find_bar.hide()
        self.editor.setFocus()

    def find_next(self):
        text = self.find_input.text()
        if not text:
            self.show_find()
            return
        if not self.editor.find(text):
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            if not self.editor.find(text):
                self.statusBar().showMessage("No matches in this document.", 4000)

    def show_shortcuts(self):
        QMessageBox.information(self, "Keyboard shortcuts",
                                "Ctrl+Shift+O  Open workspace\nCtrl+N  New note\nCtrl+Shift+N  New folder\n"
                                "Ctrl+O  Open note\nCtrl+S  Save\nCtrl+Shift+S  Save As\n"
                                "Ctrl+Shift+R  Reload from disk\nCtrl+W  Close note\nCtrl+Q  Exit\n"
                                "Ctrl+Z / Ctrl+Shift+Z  Undo / Redo\nCtrl+F / F3  Find / Next\n"
                                "F2  Rename selected item\nF5  Refresh files\nCtrl+E  Toggle preview\n"
                                "Ctrl+R  Refresh preview\nCtrl+1 / 2 / 3  Focus editor / files / preview")

    def show_about(self):
        QMessageBox.about(self, "About UPT", "<h2>UPT 1.0 Beta</h2><p>A local-first Markdown workspace.</p>"
                          "<p>Python · Qt for Python · Python-Markdown</p>"
                          "<p>No accounts, telemetry, or automatic network requests.</p>"
                          "<p>Application source: MIT. Qt/PySide and other dependencies retain their own licenses.</p>")

    def closeEvent(self, event):  # noqa: N802 (Qt virtual)
        if self.maybe_save():
            self.persist()
            event.accept()
        else:
            event.ignore()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="UPT 1.0 Beta — local Markdown editor")
    parser.add_argument("--workspace", type=Path, help="Open this local folder")
    parser.add_argument("--settings", type=Path, help="Use an alternative session settings file")
    args = parser.parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("UPT")
    app.setApplicationVersion("1.0.0b1")
    app.setStyle("Fusion")
    window = MainWindow(Settings(args.settings), restore=not bool(args.workspace))
    if args.workspace:
        window.switch_workspace(args.workspace)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
