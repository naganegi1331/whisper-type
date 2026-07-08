"""ストリーミング音声認識。

録音中、一定間隔で「発話開始からの音声バッファ全体」を whisper.cpp に
かけ直し、途中認識結果としてコールバックへ通知する。
バッファが上限（既定 25 秒）を超えたら、その時点のテキストを確定して
コールバックへ通知し、バッファを新しい発話区間として仕切り直す。
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

import numpy as np

from .audio import AudioRecorder
from .engine import RecognitionEngine

logger = logging.getLogger(__name__)

# 1 区間としてエンジンに渡す音声の上限（whisper のウィンドウは 30 秒）
MAX_SEGMENT_SECONDS = 25.0
# これ未満の音声は認識にかけない（ノイズによる誤認識防止）
MIN_AUDIO_SECONDS = 0.5


class StreamingRecognizer:
    """録音とリアルタイム認識を行うワーカー。

    コールバック（別スレッドから呼ばれる）:
      on_partial(text): 現在の発話区間の途中認識結果（全文で通知）
      on_commit(text):  区間が確定したテキスト
      on_error(exc):    認識スレッド内で発生した例外
    """

    def __init__(
        self,
        recorder: AudioRecorder,
        engine: RecognitionEngine,
        on_partial: Callable[[str], None],
        on_commit: Callable[[str], None],
        on_error: Callable[[Exception], None] | None = None,
        interval_ms: int = 1000,
    ) -> None:
        self._recorder = recorder
        self._engine = engine
        self._on_partial = on_partial
        self._on_commit = on_commit
        self._on_error = on_error
        self._interval = max(0.2, interval_ms / 1000.0)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._recorder.start()
        self._thread = threading.Thread(target=self._run, name="recognizer", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        """録音を止め、最終認識が完了するまで待つ。"""
        if not self.is_running:
            return
        self._stop_event.set()
        assert self._thread is not None
        self._thread.join(timeout=timeout)
        self._thread = None

    def _run(self) -> None:
        sr = self._recorder.sample_rate
        buffer = np.zeros(0, dtype=np.float32)
        partial = ""
        try:
            while not self._stop_event.wait(self._interval):
                buffer = np.concatenate([buffer, self._recorder.drain()])
                if buffer.size < sr * MIN_AUDIO_SECONDS:
                    continue
                partial = self._engine.transcribe(buffer)
                self._on_partial(partial)
                if buffer.size >= sr * MAX_SEGMENT_SECONDS:
                    # 区間を確定して仕切り直す
                    self._on_commit(partial)
                    buffer = np.zeros(0, dtype=np.float32)
                    partial = ""
            # 停止指示後：残りの音声を含めて最終認識
            self._recorder.stop()
            buffer = np.concatenate([buffer, self._recorder.drain()])
            if buffer.size >= sr * MIN_AUDIO_SECONDS:
                partial = self._engine.transcribe(buffer)
                self._on_partial(partial)
            if partial:
                self._on_commit(partial)
        except Exception as exc:
            logger.exception("認識スレッドでエラーが発生しました")
            self._recorder.stop()
            if self._on_error is not None:
                self._on_error(exc)
