"""マイクからの音声取得（sounddevice）。

16kHz / モノラル / float32 のストリームを取得し、
コールバックで受け取ったチャンクをスレッドセーフに蓄積する。
"""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np
import sounddevice as sd


class AudioRecorder:
    """sounddevice の InputStream をラップした録音器。"""

    def __init__(self, sample_rate: int = 16000, device: str = "") -> None:
        self.sample_rate = sample_rate
        self.device = device or None
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._chunks: list[np.ndarray] = []

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        with self._lock:
            self._chunks.clear()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device,
            callback=self._on_audio,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        stream, self._stream = self._stream, None
        stream.stop()
        stream.close()

    def drain(self) -> np.ndarray:
        """前回の呼び出し以降に録音された音声を取り出す。"""
        with self._lock:
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            chunks, self._chunks = self._chunks, []
        return np.concatenate(chunks)

    def _on_audio(self, indata: np.ndarray, frames: int, time, status) -> None:
        # コールバックは PortAudio のスレッドから呼ばれる
        with self._lock:
            self._chunks.append(indata[:, 0].copy())
