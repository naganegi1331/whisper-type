"""設定ダイアログ（要件 4.1 / 4.2 / 4.3 / 4.5）。"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .. import autostart
from ..config import AppConfig

_LANGUAGES = [("自動判定", "auto"), ("日本語", "ja"), ("英語", "en")]


class SettingsDialog(QDialog):
    """設定変更ダイアログ。OK 時に AppConfig へ書き戻す。"""

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self.hotkey_changed = False
        self.model_settings_changed = False

        self.setWindowTitle("設定 - WhisperType")
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        cfg = self._config
        root = QVBoxLayout(self)
        form = QFormLayout()

        # ホットキー
        self._hotkey_edit = QLineEdit(cfg.hotkey)
        self._hotkey_edit.setPlaceholderText("例: ctrl+shift+space")
        form.addRow("ホットキー", self._hotkey_edit)

        # 自動入力
        self._auto_input_check = QCheckBox("認識結果をカーソル位置へ自動入力する")
        self._auto_input_check.setChecked(cfg.auto_input)
        form.addRow("自動入力", self._auto_input_check)

        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(0, 10000)
        self._delay_spin.setSingleStep(100)
        self._delay_spin.setSuffix(" ms")
        self._delay_spin.setValue(cfg.input_delay_ms)
        form.addRow("自動入力開始までの待機時間", self._delay_spin)

        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(0, 500)
        self._interval_spin.setSingleStep(5)
        self._interval_spin.setSuffix(" ms/文字")
        self._interval_spin.setToolTip("0 = 最速（一括入力）")
        self._interval_spin.setValue(cfg.typing_interval_ms)
        form.addRow("入力速度", self._interval_spin)

        # 音声認識
        self._language_combo = QComboBox()
        for label, code in _LANGUAGES:
            self._language_combo.addItem(label, code)
        index = self._language_combo.findData(cfg.language)
        self._language_combo.setCurrentIndex(max(0, index))
        form.addRow("認識言語", self._language_combo)

        model_row = QHBoxLayout()
        self._model_path_edit = QLineEdit(cfg.model_path)
        model_row.addWidget(self._model_path_edit)
        browse = QPushButton("参照...")
        browse.clicked.connect(self._browse_model)
        model_row.addWidget(browse)
        form.addRow("モデルファイル", model_row)

        # 常駐
        self._autostart_check = QCheckBox("Windows 起動時に自動的に常駐する")
        self._autostart_check.setChecked(cfg.autostart)
        self._autostart_check.setEnabled(autostart.is_supported())
        form.addRow("自動起動", self._autostart_check)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Whisper モデルファイルを選択",
            self._model_path_edit.text(),
            "Whisper モデル (*.bin *.gguf);;すべてのファイル (*)",
        )
        if path:
            self._model_path_edit.setText(path)

    def accept(self) -> None:
        cfg = self._config
        hotkey = self._hotkey_edit.text().strip().lower()
        if not hotkey:
            QMessageBox.warning(self, "WhisperType", "ホットキーを入力してください。")
            return

        self.hotkey_changed = hotkey != cfg.hotkey
        self.model_settings_changed = (
            self._model_path_edit.text() != cfg.model_path
            or self._language_combo.currentData() != cfg.language
        )

        cfg.hotkey = hotkey
        cfg.auto_input = self._auto_input_check.isChecked()
        cfg.input_delay_ms = self._delay_spin.value()
        cfg.typing_interval_ms = self._interval_spin.value()
        cfg.language = self._language_combo.currentData()
        cfg.model_path = self._model_path_edit.text()

        if autostart.is_supported() and (
            self._autostart_check.isChecked() != cfg.autostart
        ):
            try:
                autostart.set_enabled(self._autostart_check.isChecked())
            except OSError as exc:
                QMessageBox.warning(
                    self, "WhisperType", f"自動起動の設定に失敗しました: {exc}"
                )
        cfg.autostart = self._autostart_check.isChecked()

        super().accept()
