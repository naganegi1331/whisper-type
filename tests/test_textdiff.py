"""textdiff（途中認識結果の差分計算）のテスト。"""

from whispertype.textdiff import compute_ops


def test_append_only():
    ops = compute_ops("今日は", "今日は晴れ")
    assert ops.backspaces == 0
    assert ops.text == "晴れ"

def test_initial_typing():
    ops = compute_ops("", "こんにちは")
    assert ops.backspaces == 0
    assert ops.text == "こんにちは"


def test_correction_in_middle():
    # 前半が訂正された場合は、共通接頭辞以降を打ち直す
    ops = compute_ops("今日は貼れです", "今日は晴れです")
    assert ops.backspaces == 4  # 「貼れです」を削除
    assert ops.text == "晴れです"


def test_no_change():
    ops = compute_ops("同じテキスト", "同じテキスト")
    assert ops.backspaces == 0
    assert ops.text == ""


def test_shrink():
    ops = compute_ops("長いテキスト", "長い")
    assert ops.backspaces == 4
    assert ops.text == ""


def test_completely_different():
    ops = compute_ops("abc", "xyz")
    assert ops.backspaces == 3
    assert ops.text == "xyz"


def test_english():
    ops = compute_ops("Hello wor", "Hello world!")
    assert ops.backspaces == 0
    assert ops.text == "ld!"
