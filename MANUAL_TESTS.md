# Manual acceptance checklist

Use a disposable copy of `examples/starter`, not valuable notes. Automated coverage and the delivery smoke test are listed in `VERIFICATION.md`; this checklist is for your own acceptance testing.

1. Launch UPT. Open the copied workspace, expand Projects, and open both sample notes. Resize the window and pane dividers. Confirm the editor and preview stay usable.
2. Create a note, type Unicode, headings, lists, fenced code, and a table. Check the unsaved indicator, live preview, undo/redo, find, and preview toggle. Save it, close UPT, and reopen. Confirm workspace/document resumption and actual UTF-8 file contents in another viewer.
3. Make unsaved edits and switch notes: test Cancel, Discard, and Save. Repeat with closing the window and switching workspaces. Cancel the first-save dialog and confirm the original transition is canceled too.
4. Create a nested folder and a note inside it. Rename the note while dirty; save. Rename its parent; confirm the open note still saves to the right location. Change files with your file manager and press F5.
5. Try names such as `../escape.md`, `CON.md`, trailing spaces/dots, or filenames without `.md`. Try saving outside the workspace. Confirm rejection and preserved editor text. In a disposable folder, test symlinks/junctions if your OS permits them.
6. Edit an open note in another editor and save it there. Wait at least two seconds. Confirm UPT reports a conflict and refuses Save. Save As to a new name, then verify both files. Repeat with a moved/deleted original and with an external same-length change.
7. Try a read-only file and an unwritable folder. Confirm a visible error and intact unsaved text. Restore permissions after testing. Check the same behavior with a full disk only in a dedicated test environment.
8. Paste `<script>alert(1)</script>`, an `<iframe>`, a raw image pointing at a local file, and a Markdown remote image. Confirm no scripts or resources run/load. Click a web link and cancel the external-app confirmation; test a workspace Markdown link.
9. Cancel file deletion, then confirm it for a disposable saved note. Confirm nonempty folder deletion fails without removing anything, including a hidden `.txt` file. Delete a truly empty folder.
10. Close UPT and move the last document; reopen and verify recovery messaging. Repeat with a moved workspace and a malformed copy of the session JSON (use `--settings` to avoid touching your main session).
11. Navigate using Tab, Shift+Tab, menus, F2/F5, and Ctrl+1/2/3. Check at your usual display scale. If you use a screen reader/high-contrast mode, record any issues; these modes are not verified in this delivery.

Report a bug with OS/Python version, reproduction steps, expected/actual behavior, and whether the issue affects disk content or only display. Use non-sensitive sample notes.
