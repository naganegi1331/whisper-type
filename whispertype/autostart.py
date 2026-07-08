"""Windows 起動時の自動常駐（レジストリ Run キー）。"""

from __future__ import annotations

import sys

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "WhisperType"


def _launch_command() -> str:
    """自動起動に登録するコマンドラインを返す。"""
    if getattr(sys, "frozen", False):  # PyInstaller 等でビルドされた場合
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m whispertype'


def is_supported() -> bool:
    return sys.platform == "win32"


def is_enabled() -> bool:
    if not is_supported():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, _VALUE_NAME)
        return True
    except OSError:
        return False


def set_enabled(enabled: bool) -> None:
    """自動常駐の ON/OFF を切り替える。Windows 以外では何もしない。"""
    if not is_supported():
        return
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(key, _VALUE_NAME)
            except FileNotFoundError:
                pass
