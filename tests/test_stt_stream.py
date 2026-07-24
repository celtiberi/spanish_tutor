"""Streaming STT helpers (no live network)."""

import struct
import unittest

from tutor import stt_stream


class TestSttStreamHelpers(unittest.TestCase):
    def test_pcm_rms_silence(self):
        silence = b"\x00\x00" * 1600
        self.assertLess(stt_stream.pcm_rms(silence), stt_stream.MIN_PEAK_RMS)

    def test_pcm_rms_loud(self):
        # full-scale alternating samples
        samples = b"".join(struct.pack("<h", 20000 if i % 2 else -20000) for i in range(1600))
        self.assertGreater(stt_stream.pcm_rms(samples), stt_stream.MIN_PEAK_RMS)

    def test_pcm_to_wav_header(self):
        pcm = b"\x00\x00" * 100
        wav = stt_stream.pcm_to_wav(pcm, 16000)
        self.assertTrue(wav.startswith(b"RIFF"))
        self.assertIn(b"WAVE", wav[:16])

    def test_backend_env(self):
        self.assertIn(stt_stream.stream_backend(), ("gemini", "chirp"))

    def test_clean_via_stream(self):
        self.assertEqual(stt_stream.clean_stream_text("EMPTY"), "")
        self.assertEqual(stt_stream.clean_stream_text("Estoy bien"), "Estoy bien")


if __name__ == "__main__":
    unittest.main()
