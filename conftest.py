import os

# Uses real Qt widgets and event delivery without needing an interactive desktop.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    yield app


@pytest.fixture
def workspace(tmp_path):
    from upt.storage import Workspace
    root = tmp_path / "workspace"
    root.mkdir()
    return Workspace(root)
