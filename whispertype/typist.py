"""自動入力（pynput によるキーボードエミュレーション）。

認識結果を、現在フォーカスされているアプリケーションのカーソル位置へ
入力する。途中認識結果の訂正には Backspace を用いる。
"""

from __future__ import annotations

import threading
import time

from pynput.keyboard import Controller, Key

from .textdiff import compute_ops


class AutoTypist:
    """途中認識結果の更新を追従入力するタイピスト。

    1 回の音声入力セッション中に入力したテキストを記憶し、
    認識結果が更新されるたびに差分（Backspace + 追記）だけを送信する。
    """

    def __init__(
        self,
        enabled: bool = True,
        input_delay_ms: int = 0,
        typing_interval_ms: int = 0,
    ) -> None:
        self.enabled = enabled
        self.input_delay_ms = input_delay_ms
        self.typing_interval_ms = typing_interval_ms
        self._keyboard = Controller()
        self._lock = threading.Lock()
        self._typed = ""           # 現在の発話区間で入力済みのテキスト
        self._session_started_at = 0.0

    def begin_session(self) -> None:
        """音声入力の開始。入力済みテキストの記憶をリセットする。"""
        with self._lock:
            self._typed = ""
            self._session_started_at = time.monotonic()

    def commit_segment(self) -> None:
        """現在の発話区間を確定する。以降の更新は新しい区間として扱う。"""
        with self._lock:
            self._typed = ""

    def update(self, new_text: str) -> None:
        """途中認識結果 ``new_text`` に合わせて差分を入力する。"""
        if not self.enabled:
            return
        with self._lock:
            # 自動入力開始までの待機時間（要件 4.5）
            wait = self.input_delay_ms / 1000.0 - (
                time.monotonic() - self._session_started_at
            )
            if wait > 0:
                time.sleep(wait)
            ops = compute_ops(self._typed, new_text)
            if ops.backspaces == 0 and not ops.text:
                return
            self._send_backspaces(ops.backspaces)
            self._type_text(ops.text)
            self._typed = new_text

    def _send_backspaces(self, count: int) -> None:
        interval = self.typing_interval_ms / 1000.0
        for _ in range(count):
            self._keyboard.press(Key.backspace)
            self._keyboard.release(Key.backspace)
            if interval > 0:
                time.sleep(interval)

    def _type_text(self, text: str) -> None:
        interval = self.typing_interval_ms / 1000.0
        if interval <= 0:
            self._keyboard.type(text)
            return
        for ch in text:
            self._keyboard.type(ch)
            time.sleep(interval)
