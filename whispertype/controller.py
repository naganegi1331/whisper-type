"""アプリケーションコントローラ。

録音・認識・自動入力・ホットキーを束ね、GUI 非依存の
コールバックで状態と認識結果を通知する（処理フロー：要件 8 章）。
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from .audio import AudioRecorder
from .config import AppConfig
from .cues import play_start_chime
from .engine import RecognitionEngine, WhisperCppEngine
from .recognizer import StreamingRecognizer
from .state import AppState
from .typist import AutoTypist

logger = logging.getLogger(__name__)


class AppController:
    """WhisperType の中核。GUI からもホットキーからも同じ API を使う。

    コールバック（ワーカースレッドから呼ばれることがある）:
      on_state(state):        状態変化（待機中／音声入力中／認識中／エラー）
      on_text(text):          認識結果表示エリア向けの累積テキスト
      on_error(message):      エラーメッセージ
    """

    def __init__(
        self,
        config: AppConfig,
        on_state: Callable[[AppState], None] = lambda s: None,
        on_text: Callable[[str], None] = lambda t: None,
        on_error: Callable[[str], None] = lambda m: None,
        engine: RecognitionEngine | None = None,
    ) -> None:
        self.config = config
        self._on_state = on_state
        self._on_text = on_text
        self._on_error = on_error
        self._engine = engine
        self._lock = threading.Lock()
        self._state = AppState.WAITING
        self._committed_text = ""  # 確定済み区間の累積（表示用）
        self._recognizer: StreamingRecognizer | None = None
        self._engine_loading = False
        self._pending_engine_reload = False
        self._shutting_down = False

        self.typist = AutoTypist(
            enabled=config.auto_input,
            input_delay_ms=config.input_delay_ms,
            typing_interval_ms=config.typing_interval_ms,
        )

    # ------------------------------------------------------------------ 状態

    def set_callbacks(
        self,
        on_state: Callable[[AppState], None] | None = None,
        on_text: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """通知先を差し替える（GUI 構築後にシグナルへ接続するため）。"""
        if on_state is not None:
            self._on_state = on_state
        if on_text is not None:
            self._on_text = on_text
        if on_error is not None:
            self._on_error = on_error

    @property
    def state(self) -> AppState:
        return self._state

    def _set_state(self, state: AppState) -> None:
        self._state = state
        self._on_state(state)

    # ------------------------------------------------------------ エンジン

    def _ensure_engine(self) -> RecognitionEngine:
        """モデルの初回ロードは重いため、最初の使用時まで遅延させる。"""
        if self._engine is None:
            self._set_state(AppState.RECOGNIZING)
            self._engine = WhisperCppEngine(
                model_path=self.config.resolved_model_path(),
                language=self.config.language,
                n_threads=self.config.n_threads,
            )
        return self._engine

    # -------------------------------------------------------------- 開始/停止

    def toggle(self) -> None:
        """ホットキー用：録音中なら停止、それ以外なら開始。"""
        if self._state == AppState.RECORDING:
            self.stop_dictation()
        else:
            self.start_dictation()

    def start_dictation(self) -> None:
        """音声入力を開始する。"""
        with self._lock:
            if self._shutting_down or self._engine_loading or (
                self._recognizer is not None and self._recognizer.is_running
            ):
                return
            if self._engine is None:
                self._engine_loading = True
                self._set_state(AppState.RECOGNIZING)
                threading.Thread(
                    target=self._load_engine_and_start,
                    name="engine-loader",
                    daemon=True,
                ).start()
                return
            self._start_with_engine(self._engine)

    def _load_engine_and_start(self) -> None:
        """重いモデルロードを GUI スレッドの外で行う。"""
        try:
            engine = WhisperCppEngine(
                model_path=self.config.resolved_model_path(),
                language=self.config.language,
                n_threads=self.config.n_threads,
            )
        except Exception as exc:
            logger.exception("音声認識エンジンをロードできませんでした")
            with self._lock:
                self._engine_loading = False
                if not self._shutting_down:
                    self._set_state(AppState.ERROR)
                    self._on_error(str(exc))
            return

        with self._lock:
            self._engine_loading = False
            if self._shutting_down:
                return
            self._engine = engine
            self._start_with_engine(engine)

    def _start_with_engine(self, engine: RecognitionEngine) -> None:
        """ロック保持中に録音・認識ワーカーを開始する。"""
        try:
            recorder = AudioRecorder(
                sample_rate=self.config.sample_rate,
                device=self.config.input_device,
            )
            self._recognizer = StreamingRecognizer(
                recorder=recorder,
                engine=engine,
                on_partial=self._handle_partial,
                on_commit=self._handle_commit,
                on_error=self._handle_error,
                interval_ms=self.config.recognize_interval_ms,
            )
            self.typist.begin_session()
            self._recognizer.start()
        except Exception as exc:
            logger.exception("音声入力を開始できませんでした")
            self._set_state(AppState.ERROR)
            self._on_error(str(exc))
            self._recognizer = None
            return
        self._set_state(AppState.RECORDING)
        if self.config.start_chime:
            play_start_chime()

    def stop_dictation(self) -> None:
        """音声入力を停止する。最終認識の完了までは「認識中」を表示する。"""
        with self._lock:
            recognizer = self._recognizer
            if recognizer is None or not recognizer.is_running:
                return
            self._set_state(AppState.RECOGNIZING)
            # stop() は最終認識を待つため、GUI を固めないよう別スレッドで行う
            threading.Thread(
                target=self._finish, args=(recognizer,), name="finisher", daemon=True
            ).start()

    def _finish(self, recognizer: StreamingRecognizer) -> None:
        if not recognizer.stop():
            self._handle_error(TimeoutError("音声認識の停止がタイムアウトしました"))
            return
        with self._lock:
            # 最終認識の完了を待つ間に新しい録音が始まっていたら何もしない
            if self._recognizer is not recognizer:
                return
            self._recognizer = None
            if self._pending_engine_reload:
                self._engine = None
                self._pending_engine_reload = False
            if self._state == AppState.RECOGNIZING:
                self._set_state(AppState.WAITING)

    def shutdown(self) -> None:
        """アプリ終了時の後片付け。"""
        with self._lock:
            self._shutting_down = True
            recognizer = self._recognizer
        if recognizer is not None:
            if not recognizer.stop(timeout=5.0):
                logger.warning("音声認識ワーカーは停止タイムアウト後も動作中です")
            else:
                self._recognizer = None

    # ---------------------------------------------------------- コールバック

    def _handle_partial(self, text: str) -> None:
        self._on_text(self._committed_text + text)
        self.typist.update(text)

    def _handle_commit(self, text: str) -> None:
        self._committed_text += text
        self.typist.commit_segment()

    def _handle_error(self, exc: Exception) -> None:
        self._set_state(AppState.ERROR)
        self._on_error(str(exc))

    # ------------------------------------------------------------ 設定反映

    def apply_config(self, reload_engine: bool = False) -> None:
        """設定変更を実行中のコンポーネントへ反映する。

        モデル・言語・スレッド数を変更した場合は ``reload_engine=True`` で
        呼び出す。録音中でなければエンジンを破棄し、次回開始時に再ロードする。
        """
        self.typist.enabled = self.config.auto_input
        self.typist.input_delay_ms = self.config.input_delay_ms
        self.typist.typing_interval_ms = self.config.typing_interval_ms
        if reload_engine:
            if self._recognizer is not None and self._recognizer.is_running:
                self._pending_engine_reload = True
            else:
                self._engine = None
                self._pending_engine_reload = False
