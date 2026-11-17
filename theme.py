STYLE = """
QMainWindow, QWidget { background: #21232b; color: #e0e3ed; font-family: 'Segoe UI'; font-size: 10pt; }
QMenuBar, QMenu, QToolBar { background: #191b22; border: none; }
QMenuBar::item, QMenu::item { padding: 7px 14px; }
QMenuBar::item:selected, QMenu::item:selected { background: #38334e; }
QToolBar { spacing: 6px; padding: 8px; border-bottom: 1px solid #343744; }
QToolButton { padding: 7px 12px; border: 1px solid transparent; border-radius: 5px; }
QToolButton:hover { background: #343344; border-color: #655b82; }
QToolButton:disabled { color: #777d8e; }
QTreeWidget { background: #191b22; border: none; padding: 8px; outline: none; }
QTreeWidget::item { padding: 6px 3px; border-radius: 4px; }
QTreeWidget::item:selected { background: #39334f; color: #f4efff; }
QTreeWidget::item:hover { background: #2c2e3a; }
QPlainTextEdit, QTextBrowser { border: none; padding: 20px; selection-background-color: #51496d; }
QPlainTextEdit { background: #23252e; font-family: Consolas, monospace; font-size: 12pt; }
QTextBrowser { background: #21232b; }
QSplitter::handle { background: #343744; width: 2px; }
QLabel#paneTitle { background: #1e2028; color: #aeb6c9; padding: 10px 16px; font-size: 9pt; }
QLabel#workspaceTitle { color: #b9a8ff; font-size: 11pt; font-weight: 600; padding: 15px 14px; }
QLabel#notice { background: #3a3349; color: #f0e5ff; padding: 10px; }
QStatusBar { background: #191b22; color: #bbc2d3; border-top: 1px solid #343744; }
QPushButton { background: #393449; border: 1px solid #6a6082; border-radius: 5px; padding: 8px 15px; }
QPushButton:hover { background: #4b425f; }
QPushButton:default { background: #665287; }
QPushButton:disabled { color: #828697; border-color: #424652; }
QLineEdit { background: #191b22; border: 1px solid #6d637f; border-radius: 4px; padding: 8px; }
QWidget:focus { outline: none; }
QTreeWidget:focus, QPlainTextEdit:focus, QTextBrowser:focus { border: 1px solid #8f7eb4; }
QScrollBar:vertical { background: #20222a; width: 12px; }
QScrollBar::handle:vertical { background: #4a4e5e; min-height: 28px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #393449; color: #fff; border: 1px solid #7f719b; }
"""
