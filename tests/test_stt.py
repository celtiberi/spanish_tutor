"""STT helpers (no live API required)."""

import io
import math
import struct
import unittest
import wave

from tutor.stt import (
    MIN_WAV_RMS,
    _clean_transcript,
    _normalize_mime,
    _parse_model_json,
    pcm_frame_stats,
    prepare_wav_for_stt,
    stt_enabled,
    stt_model,
    trim_pcm_silence,
    wav_from_pcm,
    wav_rms,
)


def _make_wav(seconds=0.5, amp=0.0, rate=16000):
    n = int(rate * seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            s = amp * math.sin(2 * math.pi * 440 * i / rate)
            frames += struct.pack("<h", int(max(-1, min(1, s)) * 32767))
        w.writeframes(bytes(frames))
    return buf.getvalue()


class TestSttHelpers(unittest.TestCase):
    def test_normalize_mime(self):
        self.assertEqual(_normalize_mime("audio/webm;codecs=opus"), "audio/webm")
        self.assertEqual(_normalize_mime("audio/x-wav"), "audio/wav")
        self.assertEqual(_normalize_mime(None), "audio/webm")

    def test_defaults(self):
        self.assertTrue(isinstance(stt_enabled(), bool))
        self.assertTrue(stt_model())

    def test_wav_rms_silence_below_gate(self):
        silent = _make_wav(amp=0.0)
        rms = wav_rms(silent)
        self.assertIsNotNone(rms)
        self.assertLess(rms, MIN_WAV_RMS)

    def test_wav_rms_loud_above_gate(self):
        loud = _make_wav(amp=0.2)
        rms = wav_rms(loud)
        self.assertIsNotNone(rms)
        self.assertGreater(rms, MIN_WAV_RMS)

    def test_clean_empty_tokens(self):
        self.assertEqual(_clean_transcript("EMPTY"), "")
        self.assertEqual(_clean_transcript("empty"), "")
        self.assertEqual(_clean_transcript("Who"), "")
        self.assertEqual(_clean_transcript("There are"), "")
        self.assertEqual(_clean_transcript("Estoy bien"), "Estoy bien")

    def test_parse_model_json(self):
        has, t = _parse_model_json('{"has_speech": false, "transcript": ""}')
        self.assertFalse(has)
        self.assertEqual(t, "")
        has, t = _parse_model_json(
            '{"has_speech": true, "transcript": "Estoy en el bote"}'
        )
        self.assertTrue(has)
        self.assertEqual(t, "Estoy en el bote")

    def test_prepare_silence_skipped(self):
        wav, stats = prepare_wav_for_stt(_make_wav(seconds=1.0, amp=0.0))
        self.assertIsNone(wav)
        self.assertEqual(stats.get("skipped"), "vad_gate")

    def test_prepare_loud_passes(self):
        wav, stats = prepare_wav_for_stt(_make_wav(seconds=1.0, amp=0.25))
        self.assertIsNotNone(wav)
        self.assertGreater(stats.get("speech_ratio", 0), 0.1)

    def test_trim_silence(self):
        # silence + tone + silence
        rate = 16000
        silent = b"\x00\x00" * rate  # 1s
        tone = bytearray()
        for i in range(rate):
            s = 0.3 * math.sin(2 * math.pi * 440 * i / rate)
            tone += struct.pack("<h", int(s * 32767))
        pcm = silent + bytes(tone) + silent
        trimmed = trim_pcm_silence(bytes(pcm))
        self.assertLess(len(trimmed), len(pcm))
        self.assertGreater(len(trimmed), rate)  # still has tone


if __name__ == "__main__":
    unittest.main()
