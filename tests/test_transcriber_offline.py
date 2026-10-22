"""Transcription must not require network access when the model is cached.

Regression test: WhisperModel's default load path contacts huggingface.co
for a revision check; on machines with TLS interception (proxy/AV) that
check fails with SSLError and kills the transcription phase. The model is
pre-cached with the app, so loading must use local_files_only=True.
"""

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


class TestOfflineModelLoad(unittest.TestCase):
    def test_transcribe_audio_loads_model_offline(self):
        import audio.transcriber as tr

        captured = {}

        class FakeSegment:
            start = 0.5
            end = 1.5
            text = " hello "

        class FakeModel:
            def transcribe(self, audio_path, **kwargs):
                return [FakeSegment()], type("Info", (), {"language": "en"})

        def fake_whisper_model(*args, **kwargs):
            captured.update(kwargs)
            return FakeModel()

        original = tr.WhisperModel
        tr.WhisperModel = fake_whisper_model
        try:
            segments = tr.transcribe_audio("dummy.wav", device="cpu", compute_type="int8")
        finally:
            tr.WhisperModel = original

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].text, "hello")
        self.assertTrue(
            captured.get("local_files_only") is True,
            "WhisperModel must be constructed with local_files_only=True "
            f"(got kwargs: {captured})",
        )


class TestBundledModelResolution(unittest.TestCase):
    """Frozen builds ship the model inside the bundle (whisper_models/<size>/);
    transcribe must load from there, not from the user's HF cache."""

    def test_bundled_dir_used_when_frozen(self):
        import tempfile

        import audio.transcriber as tr

        with tempfile.TemporaryDirectory() as td:
            model_dir = Path(td) / "whisper_models" / "medium"
            model_dir.mkdir(parents=True)
            sys._MEIPASS = td
            try:
                self.assertEqual(tr._resolve_model_arg("medium"), str(model_dir))
            finally:
                del sys._MEIPASS

    def test_falls_back_to_cache_name_when_not_frozen(self):
        import audio.transcriber as tr

        self.assertFalse(hasattr(sys, "_MEIPASS"))
        self.assertEqual(tr._resolve_model_arg("medium"), "medium")

    def test_falls_back_when_bundle_missing(self):
        import tempfile

        import audio.transcriber as tr

        with tempfile.TemporaryDirectory() as td:
            sys._MEIPASS = td  # no whisper_models/ inside
            try:
                self.assertEqual(tr._resolve_model_arg("medium"), "medium")
            finally:
                del sys._MEIPASS


if __name__ == "__main__":
    unittest.main()
