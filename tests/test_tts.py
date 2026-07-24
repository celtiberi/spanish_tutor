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
