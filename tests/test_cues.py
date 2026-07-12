"""操作通知音のテスト。"""

import io
import wave

from whispertype.cues import _chime_wav


def test_start_chime_is_short_valid_wav():
    with wave.open(io.BytesIO(_chime_wav()), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 22050
        assert 0.3 <= wav.getnframes() / wav.getframerate() <= 0.4
