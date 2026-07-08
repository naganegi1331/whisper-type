"""自動入力（AutoTypist）のテスト。pynput はスタブ化されている。"""

from whispertype.typist import AutoTypist


class RecordingKeyboard:
    def __init__(self):
        self.output = ""

    def press(self, key):
        if key == "<backspace>" or getattr(key, "name", "") == "backspace":
            self.output = self.output[:-1]

    def release(self, key):
        pass

    def type(self, text):
        self.output += text


def make_typist(**kwargs) -> tuple[AutoTypist, RecordingKeyboard]:
    typist = AutoTypist(**kwargs)
    keyboard = RecordingKeyboard()
    typist._keyboard = keyboard
    return typist, keyboard


def test_progressive_updates():
    typist, kb = make_typist()
    typist.begin_session()
    typist.update("今日は")
    typist.update("今日は晴れ")
    typist.update("今日は晴れです")
    assert kb.output == "今日は晴れです"


def test_correction_uses_backspace():
    typist, kb = make_typist()
    typist.begin_session()
    typist.update("今日は貼れ")
    typist.update("今日は晴れです")
    assert kb.output == "今日は晴れです"


def test_disabled_types_nothing():
    typist, kb = make_typist(enabled=False)
    typist.begin_session()
    typist.update("こんにちは")
    assert kb.output == ""


def test_commit_segment_starts_fresh():
    typist, kb = make_typist()
    typist.begin_session()
    typist.update("最初の区間。")
    typist.commit_segment()
    typist.update("次の区間。")
    # 確定後の更新は追記になる（確定済みテキストは削除されない）
    assert kb.output == "最初の区間。次の区間。"


def test_new_session_resets_typed_memory():
    typist, kb = make_typist()
    typist.begin_session()
    typist.update("一回目")
    typist.begin_session()
    typist.update("二回目")
    assert kb.output == "一回目二回目"
