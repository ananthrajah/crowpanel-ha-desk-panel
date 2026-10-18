"""Dialog helpers that always open IN FRONT of the panel.

The panel is a frameless always-on-top tool window. On Windows a normal dialog
opened from it can end up behind it (v0.1.0 bug), so every dialog goes through
here: it is made always-on-top + application-modal, centred on the panel/screen,
raised and focused once shown.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QInputDialog, QLineEdit, QMessageBox, QWidget


def run(dlg: QDialog, anchor: QWidget | None = None) -> int:
    dlg.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.adjustSize()
    ref = anchor if (anchor is not None and anchor.isVisible()) else None
    area = ref.frameGeometry() if ref else QGuiApplication.primaryScreen().availableGeometry()
    g = dlg.frameGeometry()
    g.moveCenter(area.center())
    scr = QGuiApplication.primaryScreen().availableGeometry()
    g.moveLeft(max(scr.left(), min(g.left(), scr.right() - g.width())))
    g.moveTop(max(scr.top(), min(g.top(), scr.bottom() - g.height())))
    dlg.move(g.topLeft())

    def _front():
        dlg.raise_()
        dlg.activateWindow()
    QTimer.singleShot(0, _front)
    QTimer.singleShot(150, _front)  # Windows sometimes ignores the first request
    return dlg.exec()


def ask_text(parent, title: str, label: str, text: str = "") -> tuple[str, bool]:
    d = QInputDialog(parent)
    d.setWindowTitle(title)
    d.setLabelText(label)
    d.setTextValue(text)
    d.setTextEchoMode(QLineEdit.Normal)
    ok = run(d, parent) == QDialog.Accepted
    return d.textValue(), ok


def confirm(parent, title: str, text: str) -> bool:
    m = QMessageBox(QMessageBox.Question, title, text, QMessageBox.Yes | QMessageBox.No, parent)
    return run(m, parent) == QMessageBox.Yes


def info(parent, title: str, text: str) -> None:
    m = QMessageBox(QMessageBox.Information, title, text, QMessageBox.Ok, parent)
    run(m, parent)
