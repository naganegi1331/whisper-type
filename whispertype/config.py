"""設定の読み込み・保存。

設定は JSON ファイルとして保存する。
Windows では %APPDATA%/WhisperType/config.json、
それ以外の環境（開発用）では ~/.config/WhisperType/config.json を使う。
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

DEFAULT_HOTKEY = "ctrl+shift+space"
DEFAULT_MODEL_NAME = "large-v3-turbo"
DEFAULT_MODEL_FILE = "ggml-large-v3-turbo.bin"


def config_dir() -> Path:
    """設定ファイルを置くディレクトリを返す。"""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home()))
        return Path(base) / "WhisperType"
    return Path.home() / ".config" / "WhisperType"


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class AppConfig:
    """WhisperType の全設定。"""

    # 4.2 グローバルホットキー（keyboard ライブラリの書式）
    hotkey: str = DEFAULT_HOTKEY

    # 4.3 音声認識
    model_name: str = DEFAULT_MODEL_NAME
    model_path: str = str(Path("models") / DEFAULT_MODEL_FILE)
    language: str = "auto"          # "auto" / "ja" / "en"
    n_threads: int = 0              # 0 = 自動（CPU コア数から決定）
    recognize_interval_ms: int = 1000  # 途中認識結果を更新する間隔

    # 4.4 / 4.5 自動入力
    auto_input: bool = True
    input_delay_ms: int = 0         # 自動入力開始までの待機時間
    typing_interval_ms: int = 0     # 1 文字あたりの入力間隔（入力速度）

    # 4.1 常駐
    autostart: bool = False         # Windows 起動時に自動常駐
    start_minimized: bool = True    # 起動時はトレイのみ（メイン画面非表示）

    # 音声取得
    sample_rate: int = 16000        # whisper.cpp の要求サンプルレート
    input_device: str = ""          # "" = 既定のマイク

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        """設定ファイルから読み込む。存在しない・壊れている場合は既定値。"""
        path = path or config_path()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        defaults = cls()
        kwargs = {}
        for item in fields(cls):
            if item.name not in raw:
                continue
            value = raw[item.name]
            if _is_valid_value(item.name, value):
                kwargs[item.name] = value
            else:
                kwargs[item.name] = getattr(defaults, item.name)
        return cls(**kwargs)

    def save(self, path: Path | None = None) -> None:
        """設定ファイルへ保存する。"""
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def resolved_model_path(self) -> Path:
        """モデルファイルの絶対パスを返す（相対パスはアプリ基準で解決）。"""
        p = Path(self.model_path)
        if p.is_absolute():
            return p
        return Path(__file__).resolve().parent.parent / p


def _is_valid_value(name: str, value: object) -> bool:
    """永続化された設定値の型と安全な範囲を検証する。"""
    if name in {"hotkey", "model_name", "model_path", "input_device"}:
        return isinstance(value, str) and (bool(value.strip()) or name == "input_device")
    if name == "language":
        return value in {"auto", "ja", "en"}
    if name in {"auto_input", "autostart", "start_minimized"}:
        return type(value) is bool
    if type(value) is not int:
        return False
    ranges = {
        "n_threads": (0, 1024),
        "recognize_interval_ms": (200, 60000),
        "input_delay_ms": (0, 10000),
        "typing_interval_ms": (0, 500),
        "sample_rate": (8000, 192000),
    }
    low, high = ranges[name]
    return low <= value <= high
