"""テスト用の共通設定。

Windows 専用・ハードウェア依存のライブラリ（sounddevice / pynput /
keyboard）が無い環境でもコアロジックをテストできるよう、
未インストールの場合はスタブモジュールを注入する。
"""

from __future__ import annotations

import sys
import types


def _ensure_stub(name: str, module: types.ModuleType) -> None:
    try:
        __import__(name)
    except Exception:
        sys.modules[name] = module


# --- sounddevice スタブ -------------------------------------------------
_sd = types.ModuleType("sounddevice")


class _FakeInputStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass


_sd.InputStream = _FakeInputStream
_ensure_stub("sounddevice", _sd)

# --- pynput スタブ ------------------------------------------------------
_pynput = types.ModuleType("pynput")
_pynput_kb = types.ModuleType("pynput.keyboard")


class _FakeKey:
    backspace = "<backspace>"


class _FakeController:
    def __init__(self):
        self.events: list[tuple[str, str]] = []

    def press(self, key):
        self.events.append(("press", key))

    def release(self, key):
        self.events.append(("release", key))

    def type(self, text):
        self.events.append(("type", text))


_pynput_kb.Key = _FakeKey
_pynput_kb.Controller = _FakeController
_pynput.keyboard = _pynput_kb
_ensure_stub("pynput", _pynput)
_ensure_stub("pynput.keyboard", _pynput_kb)

# --- keyboard スタブ ----------------------------------------------------
_kb = types.ModuleType("keyboard")
_kb._hotkeys = {}


def _add_hotkey(hotkey, callback, **kwargs):
    if not hotkey:
        raise ValueError("invalid hotkey")
    handle = object()
    _kb._hotkeys[handle] = (hotkey, callback)
    return handle


def _remove_hotkey(handle):
    del _kb._hotkeys[handle]


_kb.add_hotkey = _add_hotkey
_kb.remove_hotkey = _remove_hotkey
_ensure_stub("keyboard", _kb)
