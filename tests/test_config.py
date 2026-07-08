"""設定の読み込み・保存のテスト。"""

import json

from whispertype.config import DEFAULT_HOTKEY, AppConfig


def test_defaults():
    cfg = AppConfig()
    assert cfg.hotkey == DEFAULT_HOTKEY == "ctrl+shift+space"
    assert cfg.model_name == "large-v3-turbo"
    assert cfg.auto_input is True
    assert cfg.language == "auto"
    assert cfg.sample_rate == 16000


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    cfg = AppConfig(hotkey="ctrl+alt+v", auto_input=False, input_delay_ms=500)
    cfg.save(path)

    loaded = AppConfig.load(path)
    assert loaded == cfg


def test_load_missing_file_returns_defaults(tmp_path):
    loaded = AppConfig.load(tmp_path / "nothing.json")
    assert loaded == AppConfig()


def test_load_broken_json_returns_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{broken", encoding="utf-8")
    assert AppConfig.load(path) == AppConfig()


def test_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"hotkey": "f9", "future_option": 123}), encoding="utf-8"
    )
    loaded = AppConfig.load(path)
    assert loaded.hotkey == "f9"
    assert loaded.auto_input is True


def test_saved_file_is_utf8_json(tmp_path):
    path = tmp_path / "config.json"
    AppConfig().save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["model_name"] == "large-v3-turbo"


def test_resolved_model_path_absolute(tmp_path):
    cfg = AppConfig(model_path=str(tmp_path / "model.bin"))
    assert cfg.resolved_model_path() == tmp_path / "model.bin"


def test_resolved_model_path_relative():
    cfg = AppConfig()
    resolved = cfg.resolved_model_path()
    assert resolved.is_absolute()
    assert resolved.name == "ggml-large-v3-turbo.bin"
