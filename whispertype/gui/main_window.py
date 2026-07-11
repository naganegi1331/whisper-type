"""メインウィンドウ（要件 5 章・6 章の GUI イメージに準拠）。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__
from ..config import AppConfig
from ..controller import AppController
from ..state import AppState


class MainWindow(QMainWindow):
    """WhisperType のメイン画面。

    ワーカースレッドからの通知は Qt シグナル経由で GUI スレッドへ
    ブリッジする（state_changed / text_changed / error_occurred）。
    """

    state_changed = Signal(object)   # AppState
    text_changed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, controller: AppController, config: AppConfig) -> None:
        super().__init__()
        self._controller = controller
        self._config = config
        self._allow_close = False  # 閉じるボタンはトレイへの最小化にする
        # 設定でホットキーが変わったときに app 側が差し替えるコールバック
        self.on_hotkey_changed = lambda hotkey: True

        self.setWindowTitle(__app_name__)
        self.setMinimumSize(420, 480)
        self._build_ui()

        self.state_changed.connect(self._show_state, Qt.QueuedConnection)
        self.text_changed.connect(self._show_text, Qt.QueuedConnection)
        self.error_occurred.connect(self._show_error, Qt.QueuedConnection)
        self._show_state(controller.state)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        title = QLabel(__app_name__)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        root.addWidget(title)

        info = QGroupBox()
        form = QFormLayout(info)
        self._status_label = QLabel()
        form.addRow("Status", self._status_label)
        self._model_label = QLabel(self._config.model_name)
        form.addRow("Model", self._model_label)
        self._hotkey_label = QLabel(self._format_hotkey(self._config.hotkey))
        form.addRow("Hotkey", self._hotkey_label)
        self._auto_input_check = QCheckBox("Auto Input")
        self._auto_input_check.setChecked(self._config.auto_input)
        self._auto_input_check.toggled.connect(self._on_auto_input_toggled)
        form.addRow("", self._auto_input_check)
        root.addWidget(info)

        root.addWidget(QLabel("Recognized Text"))
        self._text_area = QPlainTextEdit()
        self._text_area.setReadOnly(True)
        self._text_area.setPlaceholderText("認識結果がここに表示されます")
        root.addWidget(self._text_area, stretch=1)

        buttons = QHBoxLayout()
        self._start_button = QPushButton("Start")
        self._start_button.clicked.connect(self._controller.start_dictation)
        buttons.addWidget(self._start_button)
        self._stop_button = QPushButton("Stop")
        self._stop_button.clicked.connect(self._controller.stop_dictation)
        buttons.addWidget(self._stop_button)
        self._settings_button = QPushButton("Settings")
        self._settings_button.clicked.connect(self._open_settings)
        buttons.addWidget(self._settings_button)
        root.addLayout(buttons)

        self.setCentralWidget(central)

    @staticmethod
    def _format_hotkey(hotkey: str) -> str:
        return " + ".join(part.strip().capitalize() for part in hotkey.split("+"))

    # ------------------------------------------------------------ スロット

    def _show_state(self, state: AppState) -> None:
        self._status_label.setText(f"{state.icon} {state.label_ja}")
        recording = state == AppState.RECORDING
        self._start_button.setEnabled(not recording and state != AppState.RECOGNIZING)
        self._stop_button.setEnabled(recording)

    def _show_text(self, text: str) -> None:
        self._text_area.setPlainText(text)
        scrollbar = self._text_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _show_error(self, message: str) -> None:
        self._text_area.appendPlainText(f"\n[エラー] {message}")

    def _on_auto_input_toggled(self, checked: bool) -> None:
        self._config.auto_input = checked
        self._config.save()
        self._controller.apply_config()

    def _open_settings(self) -> None:
        from .settings_dialog import SettingsDialog

        dialog = SettingsDialog(self._config, parent=self)
        previous_hotkey = self._config.hotkey
        if dialog.exec():
            if dialog.hotkey_changed and not self.on_hotkey_changed(
                self._config.hotkey
            ):
                self._config.hotkey = previous_hotkey
            self._config.save()
            self._controller.apply_config(reload_engine=dialog.model_settings_changed)
            self._hotkey_label.setText(self._format_hotkey(self._config.hotkey))
            self._model_label.setText(self._config.model_name)
            self._auto_input_check.setChecked(self._config.auto_input)

    # -------------------------------------------------------------- 閉じる

    def force_close(self) -> None:
        self._allow_close = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._allow_close:
            event.accept()
            return
        # 閉じる＝非表示（トレイ常駐を続ける）
        event.ignore()
        self.hide()
