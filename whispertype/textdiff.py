"""途中認識結果の差分計算。

リアルタイム認識では、同じ発話区間のテキストが認識の進行に伴って
更新される（後半が伸びるだけでなく、前半が訂正されることもある）。
既に入力済みのテキストと新しい認識結果を比較し、
「何文字削除して、何を追加入力すべきか」を計算する。
"""

from __future__ import annotations

from typing import NamedTuple


class TypingOps(NamedTuple):
    """自動入力が実行すべき操作。"""

    backspaces: int  # 送信する Backspace の回数
    text: str        # その後に入力する文字列


def compute_ops(typed: str, new: str) -> TypingOps:
    """入力済み文字列 ``typed`` を ``new`` に一致させる操作を返す。

    共通接頭辞を保持し、残りを Backspace で削除してから差分を入力する。
    """
    prefix = _common_prefix_len(typed, new)
    return TypingOps(backspaces=len(typed) - prefix, text=new[prefix:])


def _common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i
