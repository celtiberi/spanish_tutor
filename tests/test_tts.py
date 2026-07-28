"""TTS helpers (no live API required for unit tests)."""

import unittest
import wave
import io

from tutor.tts import clean_for_speech, pcm_to_wav, _parse_pcm_rate


class TestTtsHelpers(unittest.TestCase):
    def test_clean_markdown(self):
        t = clean_for_speech("**Todo va bien** — *nice*")
        self.assertNotIn("**", t)
        self.assertIn("Todo va bien", t)

    def test_clean_tags(self):
        t = clean_for_speech("<recast>Hola</recast><continue>¿Y tú?</continue>")
        self.assertNotIn("<", t)
        self.assertIn("Hola", t)

    def test_pcm_to_wav(self):
        # 0.1s silence mono 16-bit 24kHz
        pcm = b"\x00\x00" * 2400
        wav = pcm_to_wav(pcm, rate=24000)
        self.assertTrue(wav[:4] == b"RIFF")
        with wave.open(io.BytesIO(wav), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getframerate(), 24000)

    def test_parse_rate(self):
        self.assertEqual(
            _parse_pcm_rate("audio/L16;codec=pcm;rate=24000"), 24000
        )


if __name__ == "__main__":
    unittest.main()


class TestTtsRatePolicy(unittest.TestCase):
    def test_slow_prefix_only_at_deliberately_slow_rates(self):
        # Prefix applies only in the deliberately-slow regime (<= 0.8).
        from tutor.tts import SLOW_STYLE_PREFIX, _tts_prompt_variants

        for rate in (0.7, 0.75, 0.8):
            for v in _tts_prompt_variants("Hola. ¿Cómo estás?", rate=rate):
                self.assertTrue(v.startswith(SLOW_STYLE_PREFIX), v[:60])

    def test_no_prefix_at_normal_rates(self):
        # 0.85–1.2: no style prefix — exact speed is client playbackRate only.
        # (Prefix at 0.9 stacked with 0.9x playback = double slowdown,
        # user complaint 2026-07-28.)
        from tutor.tts import SLOW_STYLE_PREFIX, _tts_prompt_variants

        for rate in (0.85, 0.9, 1.0, 1.2):
            for v in _tts_prompt_variants("Hola. ¿Cómo estás?", rate=rate):
                self.assertFalse(v.startswith(SLOW_STYLE_PREFIX), v[:60])

    def test_config_rate_default_and_clamped(self):
        import importlib
        import os

        from tutor import config as cfg

        old = os.environ.get("TTS_RATE")
        try:
            os.environ.pop("TTS_RATE", None)
            importlib.reload(cfg)
            self.assertEqual(cfg.TTS_RATE, 1.0)  # "Normal" = native speed
            os.environ["TTS_RATE"] = "2.5"
            importlib.reload(cfg)
            self.assertEqual(cfg.TTS_RATE, 1.2)
            os.environ["TTS_RATE"] = "0.1"
            importlib.reload(cfg)
            self.assertEqual(cfg.TTS_RATE, 0.7)
            os.environ["TTS_RATE"] = "not-a-number"
            importlib.reload(cfg)
            self.assertEqual(cfg.TTS_RATE, 1.0)
        finally:
            if old is None:
                os.environ.pop("TTS_RATE", None)
            else:
                os.environ["TTS_RATE"] = old
            importlib.reload(cfg)
