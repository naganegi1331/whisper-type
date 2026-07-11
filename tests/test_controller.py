"""AppController の状態遷移テスト（エンジンはフェイク、音声は無音）。"""

import time

from whispertype.config import AppConfig
from whispertype.controller import AppController
from whispertype.state import AppState


class SilentEngine:
    def transcribe(self, audio):
        return ""


def wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def make_controller():
    states: list[AppState] = []
    errors: list[str] = []
    controller = AppController(
        config=AppConfig(recognize_interval_ms=200),
        on_state=states.append,
        on_error=errors.append,
        engine=SilentEngine(),
    )
    return controller, states, errors


def test_start_stop_state_flow():
    controller, states, errors = make_controller()
    assert controller.state == AppState.WAITING

    controller.start_dictation()
    assert controller.state == AppState.RECORDING

    controller.stop_dictation()
    assert wait_until(lambda: controller.state == AppState.WAITING)
    assert errors == []
    assert AppState.RECOGNIZING in states  # 停止直後は「認識中」を経由する


def test_toggle():
    controller, states, errors = make_controller()
    controller.toggle()
    assert controller.state == AppState.RECORDING
    controller.toggle()
    assert wait_until(lambda: controller.state == AppState.WAITING)


def test_double_start_is_noop():
    controller, states, errors = make_controller()
    controller.start_dictation()
    controller.start_dictation()
    assert states.count(AppState.RECORDING) == 1
    controller.stop_dictation()
    assert wait_until(lambda: controller.state == AppState.WAITING)


def test_missing_model_reports_error():
    errors: list[str] = []
    config = AppConfig(model_path="/存在しない/model.bin")
    controller = AppController(config=config, on_error=errors.append)

    controller.start_dictation()
    assert wait_until(lambda: controller.state == AppState.ERROR)
    assert len(errors) == 1
    assert "model.bin" in errors[0]


def test_shutdown_while_recording():
    controller, states, errors = make_controller()
    controller.start_dictation()
    controller.shutdown()
    assert errors == []


def test_engine_reload_is_deferred_until_recording_finishes():
    controller, states, errors = make_controller()
    controller.start_dictation()
    controller.apply_config(reload_engine=True)
    assert controller._engine is not None
    controller.stop_dictation()
    assert wait_until(lambda: controller.state == AppState.WAITING)
    assert controller._engine is None
