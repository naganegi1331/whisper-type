"""システムトレイ常駐（要件 4.1）。"""

from __future__ import annotations

from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .. import __app_name__
from ..state import AppState

_STATE_COLORS = {
    AppState.WAITING: QColor(46, 160, 67),      # 緑
    AppState.RECORDING: QColor(218, 54, 51),    # 赤
    AppState.RECOGNIZING: QColor(210, 153, 34), # 黄
    AppState.ERROR: QColor(110, 118, 129),      # 灰
}


def _make_icon(color: QColor) -> QIcon:
    """状態色の丸いマイク風アイコンを描画する（画像ファイル不要）。"""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(color)
    painter.setPen(QColor(0, 0, 0, 0))
    painter.drawEllipse(4, 4, 56, 56)
    painter.setBrush(QColor(255, 255, 255))
    painter.drawRoundedRect(26, 14, 12, 24, 6, 6)  # マイク本体
    painter.drawRect(30, 40, 4, 8)                 # スタンド
    painter.drawRect(22, 48, 20, 4)                # 台座
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """状態に応じて色が変わるトレイアイコンとメニュー。"""

    def __init__(self, window, on_toggle, on_quit, parent=None) -> None:
        super().__init__(parent)
        self._window = window
        self._icons = {state: _make_icon(color) for state, color in _STATE_COLORS.items()}
        self.setIcon(self._icons[AppState.WAITING])
        self.setToolTip(__app_name__)

        menu = QMenu()
        show_action = QAction("メイン画面を表示", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)
        hide_action = QAction("メイン画面を隠す", menu)
        hide_action.triggered.connect(window.hide)
        menu.addAction(hide_action)
        menu.addSeparator()
        toggle_action = QAction("音声入力 開始/停止", menu)
        toggle_action.triggered.connect(on_toggle)
        menu.addAction(toggle_action)
        menu.addSeparator()
        quit_action = QAction("終了", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(quit_action)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    def show_state(self, state: AppState) -> None:
        self.setIcon(self._icons[state])
        self.setToolTip(f"{__app_name__} - {state.label_ja}")

    def _show_window(self) -> None:
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # 左クリック
            self._show_window()
