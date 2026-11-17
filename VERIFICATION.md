# Beta delivery verification

Verified on **November 16, 2026**. This report distinguishes automated tests, the visible desktop smoke test, and unverified environments.

## Environment

- Windows 11 x64, OS build 26200.
- CPython 3.12.14, 64-bit.
- PySide6 Essentials / shiboken6 / Qt 6.8.3.
- Python-Markdown 3.7; pytest 8.3.5.
- Packaging: setuptools 80.9.0, build 1.2.2.post1, pip 25.1.1.

The development host's normal `python` command was a nonfunctional Windows Store alias. A bundled CPython runtime was used to create an isolated virtual environment. Its `ensurepip` failed, so pip was bootstrapped into that environment using the host's working pip. Dependency downloads succeeded with network access. These are host setup limitations, not a requirement to use the Codex runtime on a normal installation.

The host's redirected default temporary folder denied some pytest/pip operations. Test data and build temporary files were redirected into the writable workspace; application safeguards were not disabled. Early runs exposed a Windows hard-link restriction and a notice layout problem; new-file commits now use no-overwrite Windows rename, and the compact-notice regression has a test.

## Automated result

Final source-tree run:

```text
python -m pytest -q --basetemp=.test-tmp-final --tb=short -ra
109 passed, 1 skipped in 1.87s
```

The delivered ZIP was then extracted into a separate folder and the suite rerun from that extracted source: **109 passed, 1 skipped in 1.88s**. The skip was the same Windows symlink privilege limitation. Both runs used the same verified dependency environment; this was not a clean-machine installation test.

The one skip is real directory-symlink creation: Windows returned **WinError 1314**, insufficient symlink privilege. A separate simulated symlink/junction boundary test passed. Actual Windows junction creation, and real symlink behavior on a permissive host, remain unverified.

Coverage includes:

- Nested folder and Markdown creation, read/write, rename, deletion, and tree filtering.
- Unicode, BOM/CRLF preservation, binary/invalid UTF-8/oversized/missing documents.
- Portable unsafe names, traversal, outside paths, protected workspace root, and link boundaries.
- Atomic create-only collision/race protection, save conflicts, second revision checks, deleted originals, and injected commit/permission failures.
- Dirty-buffer preservation, successful Save As recovery, and no clearing after failed saves.
- Atomic path-only settings, corrupt/oversized settings, unknown fields, and failed settings commits.
- Headings/lists/links/fences/tables, active HTML removal, unsafe links, and resource blocking.
- Real Qt editor keyboard events, undo/redo, live preview, menu Save shortcut, save/discard/cancel transitions, failed-open/failed-save protection, native-dialog outcome handling via controlled substitutes, reload decisions, and workspace switching.
- Nested tree loading/refresh, rename of dirty notes and parent folders, delete confirmations, restored selection, missing-session recovery, compact notices, focus-aware editing commands, find, and preview visibility.

Qt widget tests run on the **offscreen** platform with real widgets/event delivery. They are not a screen-reader or native OS-dialog certification. Offscreen raster output on this host lacks usable font glyphs, so the included visual preview was separately captured with the normal Windows Qt platform.

## Visible Windows desktop smoke test

The application was launched on the real Windows desktop and inspected through computer-use screenshots/accessibility output:

- Opened the example workspace and a Markdown note; inspected sidebar, split panes, menus, editor, and preview.
- Created an unsaved note with a heading, emphasis, list, table, and Python fenced block; observed the unsaved title and rendered content.
- Opened the native Windows Save dialog, named a disposable file using keyboard input, and saved successfully. Disk verification confirmed the 170-byte UTF-8 document.
- Closed normally, relaunched using the same session settings, and observed the same workspace and note restored with its content.
- Closed the resumed application and removed only the disposable smoke-test document. Sample notes and project reference material were preserved.

Bulk clipboard-based text entry into the native filename field did not work through the automation helper; direct keyboard entry did. The actual file-save path succeeded. The full native dialog matrix and clipboard interoperability with other apps remain items for manual acceptance testing.

`docs/upt-beta.png` shows the actual application rendered with its normal Windows Qt platform and the included Welcome note. It is not a mockup.

## Installation and packaging

- Editable installation succeeded from `pyproject.toml` with no dependency substitution.
- `python -m pip check` reported **No broken requirements found**.
- `python -m upt --help` succeeded.
- Standard Python source-distribution and wheel builds succeeded locally. They contain application source, not a frozen executable; nothing was uploaded.
- The final ZIP is assembled from an explicit source/documentation allowlist; virtual environments, test data, session settings, personal files, caches, and build products are excluded. Extraction and a test run from the extracted source are checked before delivery.

## Unverified and excluded

- Python 3.11/3.13, macOS, Linux, Windows ARM, a clean second machine, and frozen executables/installers.
- Full native dialog, clipboard, screen-reader, high-contrast, multi-monitor, keyboard-layout, and DPI matrices.
- Power failure/crash recovery, adversarial concurrent filesystem mutation, network/removable filesystems, special filesystem metadata preservation, and performance at the document limit.
- Exhaustive fuzzing/security audit. Preview uses an allowlist and a blocked resource loader; tests establish the specified cases, not a formal proof.

Use `MANUAL_TESTS.md` for acceptance. The documented 5 MiB limit, empty-folder-only deletion, create-only Save As, fixed dark theme, and lack of autosave are deliberate beta behavior. No repository, push, publication, or release was performed.
