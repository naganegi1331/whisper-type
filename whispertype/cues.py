"""操作開始を知らせる短いサウンドキュー。"""

from __future__ import annotations

import io
import logging
import math
import sys
import threading
import wave
from array import array
from functools import lru_cache

logger = logging.getLogger(__name__)


def play_start_chime() -> None:
    """音声入力開始を知らせる柔らかい2音チャイムを非同期再生する。"""
    if sys.platform != "win32":
        return
    threading.Thread(target=_play_windows, name="start-chime", daemon=True).start()


def _play_windows() -> None:
    try:
        import winsound

        # SND_MEMORY と SND_ASYNC は併用できないため、専用スレッド上で同期再生する。
        winsound.PlaySound(_chime_wav(), winsound.SND_MEMORY | winsound.SND_NODEFAULT)
    except Exception:
        # 通知音の失敗で音声入力自体を止めない。
        logger.warning("開始チャイムを再生できませんでした", exc_info=True)


@lru_cache(maxsize=1)
def _chime_wav() -> bytes:
    """短い上昇2音チャイムを WAV データとして生成する。"""
    sample_rate = 22050
    duration = 0.34
    tones = (
        (659.25, 0.00, 0.22),  # E5
        (783.99, 0.12, 0.22),  # G5
    )
    samples = array("h")
    for index in range(int(sample_rate * duration)):
        t = index / sample_rate
        value = 0.0
        for frequency, start, length in tones:
            local_t = t - start
            if not 0 <= local_t < length:
                continue
            attack = min(1.0, local_t / 0.018)
            release = min(1.0, (length - local_t) / 0.10)
            envelope = attack * release
            value += math.sin(2 * math.pi * frequency * local_t) * envelope
        samples.append(int(max(-1.0, min(1.0, value * 0.11)) * 32767))

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.tobytes())
    return output.getvalue()
