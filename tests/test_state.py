"""状態表示（要件 4.6）のテスト。"""

from whispertype.state import AppState


def test_all_states_have_labels_and_icons():
    for state in AppState:
        assert state.label_ja
        assert state.icon


def test_japanese_labels():
    assert AppState.WAITING.label_ja == "待機中"
    assert AppState.RECORDING.label_ja == "音声入力中"
    assert AppState.RECOGNIZING.label_ja == "認識中"
    assert AppState.ERROR.label_ja == "エラー"
