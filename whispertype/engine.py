"""音声認識エンジン（whisper.cpp）の抽象化。

実体は pywhispercpp（whisper.cpp の Python バインディング）を使う。
whisper.cpp は GPU 対応版バイナリ（CUDA / Vulkan ビルドの
pywhispercpp）を導入すれば、コード変更なしで GPU を活用できる。
テスト用に差し替えられるよう、エンジンはプロトコルとして定義する。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import numpy as np


class RecognitionEngine(Protocol):
    """音声波形（16kHz mono float32）をテキストへ変換するエンジン。"""

    def transcribe(self, audio: np.ndarray) -> str: ...


class WhisperCppEngine:
    """pywhispercpp 経由で whisper.cpp（large-v3-turbo）を実行する。"""

    def __init__(self, model_path: Path, language: str = "auto", n_threads: int = 0) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"Whisper モデルが見つかりません: {model_path}\n"
                "README の手順に従い ggml-large-v3-turbo モデルを配置してください。"
            )
        try:
            from pywhispercpp.model import Model
        except ImportError as exc:  # pragma: no cover - 実行環境依存
            raise RuntimeError(
                "pywhispercpp がインストールされていません。"
                "`pip install pywhispercpp` を実行してください。"
            ) from exc

        threads = n_threads if n_threads > 0 else max(1, (os.cpu_count() or 4) - 1)
        self._model = Model(
            str(model_path),
            n_threads=threads,
            print_realtime=False,
            print_progress=False,
        )
        self._language = language

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        kwargs = {}
        if self._language and self._language != "auto":
            kwargs["language"] = self._language
        segments = self._model.transcribe(audio, **kwargs)
        return "".join(seg.text for seg in segments).strip()
