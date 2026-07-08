"""グローバルホットキー（keyboard ライブラリ）。

既定は Ctrl + Shift + Space。設定画面から変更できる。
1 回押すと音声入力開始、もう一度押すと停止（トグル動作）。
"""

from __future__ import annotations

import logging
from typing import Callable

import keyboard

logger = logging.getLogger(__name__)


class HotkeyManager:
    """グローバルホットキーの登録・変更を管理する。"""

    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self._callback = callback
        self._hotkey = ""
        self._handle = None
        self.rebind(hotkey)

    @property
    def hotkey(self) -> str:
        return self._hotkey

    def rebind(self, hotkey: str) -> None:
        """ホットキーを変更する。無効な指定の場合は例外を送出し、旧設定を維持する。"""
        handle = keyboard.add_hotkey(
            hotkey, self._callback, suppress=False, trigger_on_release=False
        )
        self.unbind()
        self._handle = handle
        self._hotkey = hotkey
        logger.info("ホットキーを登録しました: %s", hotkey)

    def unbind(self) -> None:
        if self._handle is not None:
            try:
                keyboard.remove_hotkey(self._handle)
            except (KeyError, ValueError):
                pass
            self._handle = None
