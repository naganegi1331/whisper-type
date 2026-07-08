"""アプリケーションの認識状態の定義（要件 4.6 認識状態表示）。"""

from __future__ import annotations

from enum import Enum


class AppState(Enum):
    """WhisperType の動作状態。"""

    WAITING = "waiting"        # 待機中
    RECORDING = "recording"    # 音声入力中
    RECOGNIZING = "recognizing"  # 認識中（停止後の確定処理など）
    ERROR = "error"            # エラー

    @property
    def label_ja(self) -> str:
        return _LABELS_JA[self]

    @property
    def icon(self) -> str:
        return _ICONS[self]


_LABELS_JA = {
    AppState.WAITING: "待機中",
    AppState.RECORDING: "音声入力中",
    AppState.RECOGNIZING: "認識中",
    AppState.ERROR: "エラー",
}

_ICONS = {
    AppState.WAITING: "🟢",
    AppState.RECORDING: "🔴",
    AppState.RECOGNIZING: "🟡",
    AppState.ERROR: "⚠️",
}
