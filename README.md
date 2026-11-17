# UPT 1.0 Beta

A local-first Python desktop Markdown editor. Open a folder, organize notes in a file tree, write in a comfortable editor, and read a live preview beside it. The subdued interface uses original styling and standard Qt icons; it has no Obsidian branding or assets.

This is a focused editor beta, not the full Universal Productivity Tool platform. Your notes are real UTF-8 `.md` files. No account, cloud service, telemetry, or document database is involved.

![UPT editor and live preview](docs/upt-beta.png)

## What is included

- Local workspace selection and session resumption.
- Nested folders and Markdown files, with lazy folder loading.
- New notes and folders, rename, confirmed file deletion, and empty-folder deletion.
- Plain text editing, undo/redo, cut/copy/paste, find with wraparound, and unsaved indicators.
- Save, create-only Save As, and save/discard/cancel prompts before leaving unsaved work.
- Conservative detection of missing, unreadable, replaced, or externally edited files.
- Atomic saves with error reporting and an intact edit buffer after failures.
- Live preview of headings, emphasis, lists, links, fenced code, and tables.
- Keyboard menus, labeled controls, resizable panes, focus shortcuts, and an editor-only view.
- Automated storage, session, rendering, and Qt widget tests; sample notes; contributor documentation.

## Supported environment

**Verified:** Windows 11 x64, Python 3.12.14, Qt/PySide6 Essentials 6.8.3, and Python-Markdown 3.7. See [the verification report](docs/VERIFICATION.md) for exact results and limits.

The package accepts Python **3.11–3.13**. Python 3.11 and 3.13 are compatibility targets, not tested versions in this delivery. Prefer Python 3.12 for this beta. Windows x64 is the verified platform; macOS and desktop Linux are expected to work through Qt but have not been tested. No standalone executable or installer is included. Windows ARM, Python 3.14+, mobile platforms, network drives, and packaged/frozen applications are not supported by this beta.

## Install and launch on Windows

Install standard 64-bit Python 3.12 from [python.org](https://www.python.org/downloads/windows/) with its Python launcher. Extract the source archive into a normal writable folder. Open PowerShell in the extracted `upt-beta` folder and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_upt.py
```

No PowerShell activation script or execution-policy change is required. If your installation provides `python` instead of `py`, replace `py -3.12` with `python` in the first command. Confirm that it reports Python 3.12 with `python --version`.

You can then double-click **Launch-UPT.cmd**, which uses this folder's `.venv` without opening a console. Setup requires an internet connection to download dependencies; normal editor use works offline.

To explore the included workspace:

```powershell
.\.venv\Scripts\python.exe run_upt.py --workspace examples\starter
```

Choose `Welcome.md` in the file tree. These are editable sample files; copy the starter folder first if you want to preserve it.

### PyCharm

Open the extracted `upt-beta` folder as a project. Select its `.venv\Scripts\python.exe` as the existing interpreter after following setup above. Run `run_upt.py`, using the project folder as the working directory. No source changes are needed. For a test configuration select pytest and the `tests` folder.

### Optional installed command

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\upt.exe
```

The installed package also supports `python -m upt`. The source launcher works without installing the UPT package itself.

### macOS / Linux (not verified)

Use a Python 3.12 installation and a Qt-compatible graphical desktop:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_upt.py
```

Linux may require your distribution's Qt/XCB/Wayland system libraries. Qt 6.8's wheels need a compatible OS and architecture; consult [Qt for Python installation](https://doc.qt.io/qtforpython-6.8/gettingstarted/installation.html). macOS uses the displayed **Ctrl** shortcuts in this beta rather than native Command conventions. These platforms need acceptance testing before a support claim is made.

## Everyday use

1. Choose **Open workspace** and select a local folder. UPT does not create a workspace database.
2. Click a `.md` file to open it. Expand folders with their arrow or keyboard controls.
3. Use **New note**, write, and **Save** to choose a filename. New notes start as in-memory buffers; no file exists until the first successful save.
4. Select a folder before **New folder** to create a child folder. Select a file to create a sibling folder. New note Save As starts in the selected folder, or in the open note's folder when applicable.
5. Use the **Workspace** menu or a file-tree context menu to rename or delete selected items. Renaming an open note or its parent preserves its unsaved buffer.
6. Drag the pane dividers or use **View → Show preview** to concentrate on writing. Preview updates after a 250 ms pause; **Refresh preview** is also available.
7. UPT remembers the workspace and saved note path after successful actions and on a normal exit. It reopens them on the next launch when available.

File-tree changes made outside UPT appear after **F5**. Open-document conflicts are checked every two seconds and again when saving. The title and editor header show **Unsaved** when text differs from the saved version. Undoing back to that version clears the indicator.

### When a file changes elsewhere

UPT preserves the editor text and shows a notice. **Save** refuses to overwrite the changed or missing original. Choose:

- **Save As**, with an unused name, to keep your text as a separate file; or
- **Reload from disk**, to read the current disk version. Unsaved editor text requires a discard confirmation.

Save As always creates a new file. Even if the operating system's file dialog offers to replace an existing file, UPT refuses the overwrite. Use Save for your current unchanged-on-disk document. If a save fails, the buffer remains open and leaving it still requires a save/discard/cancel decision. A canceled Save As also cancels the attempted switch or exit.

If an attempted open fails, the current editor buffer remains intact. If the last workspace or document is missing at startup, UPT explains the problem and lets you choose a new folder or note. A corrupt settings file does not prevent startup.

### Deletion

File deletion is **permanent**, after a confirmation, and is not sent to the system Recycle Bin. Folders can only be deleted when completely empty, including hidden and non-Markdown files. Delete their contents intentionally using your file manager if you need to remove a nonempty folder. UPT never recursively deletes a folder.

## Shortcuts

| Shortcut | Action |
| --- | --- |
| Ctrl+Shift+O | Open workspace |
| Ctrl+N | New note |
| Ctrl+Shift+N | New folder |
| Ctrl+O | Open note inside workspace |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As (new file) |
| Ctrl+Shift+R | Reload from disk |
| Ctrl+W / Ctrl+Q | Close note / exit |
| Ctrl+Z / Ctrl+Shift+Z | Undo / redo |
| Ctrl+X / Ctrl+C / Ctrl+V / Ctrl+A | Cut / copy / paste / select all |
| Ctrl+F / F3 | Find / next match, wrapping |
| F2 | Rename selected tree item |
| F5 | Refresh files |
| Ctrl+E / Ctrl+R | Toggle preview / refresh preview |
| Ctrl+1 / Ctrl+2 / Ctrl+3 | Focus editor / files / preview |
| F1 | Shortcut reference |

Tab and Shift+Tab navigate controls. Within the editor, Tab inserts indentation. Menu access uses Alt plus the underlined menu letter. Deletion deliberately has no global key binding.

## Preview and privacy

Rendering uses Python-Markdown's `fenced_code`, `tables`, and `sane_lists` extensions, followed by an HTML allowlist. The preview is a Qt text document, not a web browser. Note scripts, event handlers, styles, embedded frames, and resource URLs cannot execute or load automatically. All images, including local images, appear as text placeholders. The resource loader blocks all schemes as an additional boundary.

Web and email links require a confirmation before being passed to the system browser/mail app. That external application can use the network. Relative `.md` links can open notes within the workspace; traversal (`..`), absolute paths, symbolic links, and junctions are rejected. UPT itself does not make network requests during normal use, check for updates, or send telemetry. Dependency installation contacts the Python package index.

Session settings store **only two paths**, never note content:

- Windows: `%APPDATA%\UPT\session.json`
- macOS: `~/Library/Application Support/UPT/session.json`
- Linux: `$XDG_CONFIG_HOME/UPT/session.json`, otherwise `~/.config/UPT/session.json`

Use `--settings path/to/session.json` for a separate local session. Remove that settings file while UPT is closed to forget the last session. Paths can reveal folder/note names; keep the settings file private. Notes inherit the security of their local folder; this beta does not encrypt them.

## Deliberate beta limits

- One workspace and one open note at a time; no tabs, plugins, synchronization, wikilinks, graph, attachments, or full-platform features.
- Maximum document size: **5 MiB of encoded UTF-8**. Very large Markdown can pause rendering; ordinary notes are the intended workload.
- UTF-8 only (with optional BOM). UTF-8 BOM and CRLF are preserved for opened documents. Mixed line endings and lone CR lines normalize on save; new notes use LF. Binary/null-containing files are rejected.
- Newline normalization aside, the source text is saved as entered; preview does not rewrite documents.
- Filenames use conservative portable rules: 1–200 characters, no control characters, unsafe Windows punctuation, reserved device names, leading/trailing whitespace, or trailing dots. Only `.md` documents are editable; `.MD` is accepted. Unsupported existing names and symlinks/junctions are omitted from the tree.
- Workspace root cannot be renamed/deleted. All document operations stay inside it. Case-only renames may be refused on case-insensitive filesystems; use an intermediate name.
- Preview follows Python-Markdown syntax, not full GitHub Markdown. Fences inside nested lists, task checkboxes, math, Mermaid, syntax coloring, arbitrary HTML/CSS, images, and heading-anchor navigation are not supported. Editor and preview scroll independently.
- No autosave, crash recovery, backup history, or recovery after a forced termination/power loss. Save regularly and keep independent backups. Normal close/switch actions protect unsaved work.
- Conflict checking compares SHA-256, size, modification time, and file identity. It protects against observed external changes, including same-size changes. Portable filesystem operations cannot provide compare-and-swap against another program writing in the tiny interval between the last check and replacement/deletion/rename. Do not simultaneously edit a file from multiple apps or UPT instances. This is a local editor, not a security boundary against a hostile process mutating the workspace.
- Existing-file saves use same-directory temporary files, flush+fsync, and atomic replacement. New files use no-overwrite rename on Windows or hard-link commit on Unix. Unix filesystems without hard-link support fail visibly. Directory metadata is not fsynced; power-loss durability is not guaranteed. Replacement preserves ordinary permission bits, not every extended attribute, ACL, alternate stream, hard link, or owner metadata. Use ordinary local files, not special metadata-dependent documents.
- The dark palette is fixed. Controls have accessible names and keyboard paths, but screen-reader, high-contrast, localization, touch, and exhaustive DPI testing remain unverified.

## Tests

From the source folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp
```

On macOS/Linux, use `.venv/bin/python` in those commands. `.test-tmp` is reserved disposable test data and pytest recreates it. Do not store notes there. The suite creates temporary workspaces; it never targets your real notes. Qt widget tests use the offscreen platform by default, real widgets, and Qt keyboard events. Prompts/file-dialog results are controlled in tests so all decision paths are repeatable. Real symlink creation is skipped when the OS denies it; a separate boundary test still runs.

See [manual acceptance checks](docs/MANUAL_TESTS.md), [architecture and contributing](docs/ARCHITECTURE.md), and [verification results](docs/VERIFICATION.md).

## Troubleshooting

- **Python not found:** install standard Python 3.12 x64. Windows Store command aliases alone are not a working Python installation.
- **No module named PySide6/markdown:** run the install command using the same `.venv` interpreter used to launch UPT.
- **GUI does not start:** launch `run_upt.py` with `.venv\Scripts\python.exe` from PowerShell to see diagnostics. Use a local graphical desktop. An offscreen test session does not display a window; remove a manually set `QT_QPA_PLATFORM=offscreen` before normal use.
- **Permission denied/read-only:** use a writable workspace and check file/folder permissions, disk space, antivirus locks, or another application's lock. Save As to a new writable path within the workspace. UPT does not bypass OS restrictions.
- **File changed notice:** use Save As or Reload as described above. Changes in timestamps/file identity can trigger a conservative conflict even when text looks unchanged.
- **Missing file in tree:** only Markdown and folders with supported names appear. Press F5. Symlinks/junctions are intentionally excluded.
- **Cannot delete folder:** it contains something, possibly a hidden or non-Markdown file. Inspect it in your file manager.
- **Could not remember session:** notes are still saved; verify permissions on the settings folder or use `--settings` with a writable path.
- **Long path errors on Windows:** extract to a shorter path and avoid deeply nested workspace folders.
- **Leftover `.upt-*.upt-tmp`:** a crash or permission failure may leave a temporary file. Inspect it before removing it while UPT is closed; never confuse it with the actual `.md` file.

## License, publication, and learning

Application code and original documentation use the full [MIT license](LICENSE). Replace **[YEAR]** and **[COPYRIGHT HOLDER]** before publication. Dependencies retain separate licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The source archive excludes dependencies and virtual environments.

Nothing has been pushed, published, or released. Use [the GitHub publication checklist](docs/PUBLICATION_CHECKLIST.md) when you are ready.

After this beta and its acceptance fixes, future feature implementation belongs to you. Assistance should focus on explaining concepts, planning small learning steps, and reviewing your implementation rather than implementing future features for you.
