"""ストリーミング認識ループのテスト（録音・エンジンはフェイク）。"""

import time

import numpy as np

from whispertype.recognizer import StreamingRecognizer


class FakeRecorder:
    """AudioRecorder と同じインターフェースのフェイク。"""

    sample_rate = 16000

    def __init__(self):
        self._pending: list[np.ndarray] = []
        self.recording = False

    def feed_seconds(self, seconds: float):
        self._pending.append(
            np.zeros(int(self.sample_rate * seconds), dtype=np.float32)
        )

    def start(self):
        self.recording = True

    def stop(self):
        self.recording = False

    def drain(self) -> np.ndarray:
        if not self._pending:
            return np.zeros(0, dtype=np.float32)
        chunks, self._pending = self._pending, []
        return np.concatenate(chunks)


class FakeEngine:
    """音声長（秒数）に応じたダミーテキストを返すエンジン。"""

    def __init__(self):
        self.calls = 0

    def transcribe(self, audio: np.ndarray) -> str:
        self.calls += 1
        seconds = audio.size / 16000
        return f"認識結果({seconds:.0f}秒)"


def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_partial_results_and_final_commit():
    recorder = FakeRecorder()
    engine = FakeEngine()
    partials: list[str] = []
    commits: list[str] = []

    recognizer = StreamingRecognizer(
        recorder=recorder,
        engine=engine,
        on_partial=partials.append,
        on_commit=commits.append,
        interval_ms=200,
    )
    recorder.feed_seconds(2.0)
    recognizer.start()
    assert recorder.recording

    assert wait_until(lambda: len(partials) >= 1)
    recorder.feed_seconds(1.0)
    assert wait_until(lambda: len(partials) >= 2)

    recognizer.stop()
    assert not recorder.recording
    assert not recognizer.is_running
    # 停止時に最終結果が確定される
    assert commits == [partials[-1]]
    assert commits[0] == "認識結果(3秒)"


def test_too_short_audio_is_not_recognized():
    recorder = FakeRecorder()
    engine = FakeEngine()
    partials: list[str] = []
    commits: list[str] = []

    recognizer = StreamingRecognizer(
        recorder=recorder,
        engine=engine,
        on_partial=partials.append,
        on_commit=commits.append,
        interval_ms=200,
    )
    recorder.feed_seconds(0.1)  # 0.5 秒未満はノイズとして無視
    recognizer.start()
    time.sleep(0.5)
    recognizer.stop()

    assert engine.calls == 0
    assert partials == []
    assert commits == []


def test_long_audio_commits_segment_and_resets():
    recorder = FakeRecorder()
    engine = FakeEngine()
    commits: list[str] = []

    recognizer = StreamingRecognizer(
        recorder=recorder,
        engine=engine,
        on_partial=lambda t: None,
        on_commit=commits.append,
        interval_ms=200,
    )
    recorder.feed_seconds(26.0)  # 上限 25 秒を超える → 区間確定
    recognizer.start()
    assert wait_until(lambda: len(commits) >= 1)
    recognizer.stop()
    assert commits[0] == "認識結果(26秒)"


def test_engine_error_reported():
    recorder = FakeRecorder()
    errors: list[Exception] = []

    class BrokenEngine:
        def transcribe(self, audio):
            raise RuntimeError("モデルが壊れています")

    recognizer = StreamingRecognizer(
        recorder=recorder,
        engine=BrokenEngine(),
        on_partial=lambda t: None,
        on_commit=lambda t: None,
        on_error=errors.append,
        interval_ms=200,
    )
    recorder.feed_seconds(2.0)
    recognizer.start()
    assert wait_until(lambda: len(errors) >= 1)
    recognizer.stop()
    assert "モデルが壊れています" in str(errors[0])
    assert not recorder.recording


def test_stop_timeout_keeps_worker_reference():
    recorder = FakeRecorder()
    entered = False
    release = False

    class SlowEngine:
        def transcribe(self, audio):
            nonlocal entered
            entered = True
            while not release:
                time.sleep(0.01)
            return "完了"

    recognizer = StreamingRecognizer(
        recorder=recorder,
        engine=SlowEngine(),
        on_partial=lambda t: None,
        on_commit=lambda t: None,
        interval_ms=200,
    )
    recorder.feed_seconds(2.0)
    recognizer.start()
    assert wait_until(lambda: entered)
    assert recognizer.stop(timeout=0.01) is False
    assert recognizer.is_running
    release = True
    assert recognizer.stop(timeout=1.0) is True
    assert not recognizer.is_running
