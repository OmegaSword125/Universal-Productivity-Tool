# Architecture and contributor guide

UPT uses a single-process Qt Widgets application with one document buffer. There is no server, database, web engine, background network client, or platform framework.

## Source map

| File | Responsibility |
| --- | --- |
| `src/upt/app.py` | Window, actions, dialogs, lazy file tree, preview debounce, conflict polling, session restoration |
| `src/upt/storage.py` | Workspace boundary, path/name validation, revisions, reading, atomic saves, organization operations |
| `src/upt/document.py` | In-memory document, saved baseline, dirty comparison, save state transition |
| `src/upt/rendering.py` | Markdown conversion, constrained HTML, link policy, trusted preview styles |
| `src/upt/settings.py` | Atomic JSON session path persistence; no document content |
| `src/upt/theme.py` | Original Qt styling |
| `run_upt.py` | Source-tree launcher |
| `tests/` | Filesystem, rendering, session, and Qt widget regression tests |

Python 3.11–3.13 syntax is targeted. Python 3.12 on Windows x64 is the verified configuration. Runtime dependencies are pinned in both `pyproject.toml` and `requirements.txt`; update them together. `shiboken6` is an exact transitive dependency of PySide6 Essentials and is made explicit in requirements for clarity. Test-only dependencies are separate.

## State and transitions

`Document.text` is the current edit buffer. `saved_text` is the last successfully saved/opened version; comparing them implements dirty state, including undo back to the saved text. `path` and `revision` refer to the disk version from which the buffer originated. A revision includes a SHA-256 digest, byte size, nanosecond modification time, and inode/file identifier.

On editor changes, update the buffer, refresh unsaved indicators, and restart a 250 ms preview timer. Rendering is on the GUI thread. A two-second timer checks the current file for external changes. It never silently replaces editor text.

Before switching notes/workspaces or closing, `maybe_save()` requires Save, Discard, or Cancel when dirty. Save only permits the transition if the entire save succeeds. Discard permits the transition without first clearing the buffer. Failed target reads leave the old document intact. Reload has its own explicit discard confirmation.

Renaming an active file or parent folder updates the buffer's path without resetting the text or undo history. A direct file rename checks the observed revision; a parent-folder rename does not rewrite files. Deleting an active file clears the buffer only after a successful, confirmed deletion. Nonempty-folder deletion is refused by the operating system's `rmdir`, which includes hidden contents.

## Filesystem boundary

`Workspace` resolves the selected root once. Every operation validates its requested path against that root, applies portable name rules, and rejects symlink/junction components. Paths containing `..` are rejected rather than normalized into a permitted path. Tree entries are lazily loaded and include folders and `.md` files only. The UI must not bypass this boundary to write notes.

Reads accept regular UTF-8 files up to 5 MiB, reject null-containing data, and verify the file did not change during the read. Optional BOM and CRLF are recorded. Text is normalized to LF in memory.

Save protocol:

1. Validate the target. For existing documents, compare the current revision with the opened revision; reject a conflict, missing file, or unreadable original.
2. Encode text with the recorded line ending and BOM. Reject oversized content before modifying anything.
3. Create an exclusive same-directory temporary file, write all bytes, flush, and fsync it. Preserve ordinary permission bits for existing documents.
4. Revalidate the path and compare the existing revision again immediately before commit.
5. Existing files use `os.replace`; new files use Windows no-overwrite `os.rename`, or Unix `os.link`. A competing creation cannot be overwritten by Save As.
6. Read back the committed file. Only then update the document's revision and saved baseline. Attempt to clean up the temporary file in all cases.

A failed operation leaves the buffer intact. If a commit succeeded but readback failed, the UI conservatively reports a failure and retains the dirty buffer; the disk may already contain the new text. Reopen/reload only after preserving edits as needed.

The final revision check and OS commit are separate operations. This is not a cross-process transaction or defense against malicious filesystem races. Folder/file rename and deletion have the same portable concurrency limits. No background process should mutate the selected workspace at the same instant as an operation. The beta intentionally avoids claiming a stronger guarantee than the OS APIs provide.

## Preview boundary

Python-Markdown converts source with `fenced_code`, `tables`, and `sane_lists`. Its raw HTML support is **not** trusted. An `HTMLParser` pass emits an allowlist of rich-text tags and only validated link URLs/table alignment; active tags and their content are removed, and images become escaped placeholders. Note-provided attributes/styles are discarded.

`SafePreview` is a `QTextBrowser` with both automatic link options disabled and `loadResource()` overridden to return empty data. There is no JavaScript interpreter or web engine. Even a sanitizer mistake should not grant resource loading. External links require confirmation before `QDesktopServices` opens the default external app; internal `.md` links still go through `Workspace` and unsaved-work decisions.

Qt's rich text is a subset of HTML/CSS. Do not promise browser-level fidelity. Any future resource support needs its own workspace path checks, file-type/size restrictions, and tests; never enable the default loader as a shortcut.

## Settings and errors

Settings are two strings: workspace and saved document paths. JSON schema filtering ignores unknown/non-string fields; malformed, oversized, or unreadable files produce a startup notice. Saves use a flushed same-directory temporary file and replacement. Settings failures report a notice without undoing a successful document save.

Core errors use `WorkspaceError`; conflicts use its `ConflictError` subclass. UI operations show a warning dialog; non-blocking external-change/session notices stay above the main panes. Do not swallow write errors or clear dirty state in a `finally` block.

## Working on the source

Install the test dependencies and run the README's test command. Tests use temporary workspaces, controlled failure injection, actual Qt widgets, and Qt keyboard events. OS file dialogs and decisions are substituted in automated UI tests. The separate manual checklist covers the visible desktop and native-dialog experience. Add regression tests for meaningful new behavior, especially anything affecting the buffer, filesystem boundary, or preview resource policy.

Source releases can be built with standard Python packaging tools:

```powershell
.\.venv\Scripts\python.exe -m pip install build
.\.venv\Scripts\python.exe -m build
```

This creates a source distribution and wheel in `dist`; it does not publish them. A wheel is not a standalone Windows executable. Frozen-app packaging and installer licensing are outside this beta.

## Learning boundary after acceptance

The initial beta and acceptance fixes may be implemented with assistance. After acceptance, the user implements future features. Support should explain tradeoffs, help decompose work, and review user-written changes. Keep changes small and understandable; do not add speculative systems or take over feature implementation.
