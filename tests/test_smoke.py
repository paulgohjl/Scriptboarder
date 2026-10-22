"""Smoke tests for Scriptboarder modules (stdlib unittest, no external deps)."""

import sys
import typing
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


class TestImports(unittest.TestCase):
    def test_all_modules_import(self):
        import audio.extractor  # noqa: F401
        import audio.transcriber  # noqa: F401
        import html_gen.html_generator  # noqa: F401
        import utils.deps  # noqa: F401
        import utils.platform_paths  # noqa: F401
        import video.metadata  # noqa: F401
        import video.scene_detector  # noqa: F401
        import video.screenshot  # noqa: F401
        import xlsx_gen.generator  # noqa: F401

    def test_extractor_annotations_evaluable(self):
        """Optional must be imported in extractor.py (fails on Py<=3.13 at import)."""
        import audio.extractor

        typing.get_type_hints(audio.extractor.extract_audio)

    def test_ffmpeg_finder_checks_meipass(self):
        """Packaged builds bundle ffmpeg at sys._MEIPASS; finders must check it.

        The bundle wins over the download cache, so a packaged app uses its
        pinned ffmpeg. Path.home() is pointed at an empty dir so a copy
        downloaded by an earlier source run cannot satisfy the lookup on
        either platform, and the binary name is taken from the platform layer
        because macOS has no .exe suffix.
        """
        import tempfile
        from unittest.mock import patch

        from utils.platform_paths import ffmpeg_binary_name

        binary = ffmpeg_binary_name()
        fake_meipass = Path(tempfile.gettempdir()) / "sb_test_meipass"
        fake_meipass.mkdir(exist_ok=True)
        (fake_meipass / binary).write_bytes(b"x")
        fake_home = Path(tempfile.gettempdir()) / "sb_test_home"
        fake_home.mkdir(exist_ok=True)

        import audio.extractor
        import utils.deps

        old = getattr(sys, "_MEIPASS", None)
        sys._MEIPASS = str(fake_meipass)
        try:
            with patch("pathlib.Path.home", return_value=fake_home):
                self.assertEqual(audio.extractor._find_ffmpeg(), str(fake_meipass / binary))
                self.assertEqual(utils.deps.ensure_ffmpeg_path(), str(fake_meipass / binary))
        finally:
            if old is None:
                del sys._MEIPASS
            else:
                sys._MEIPASS = old
            (fake_meipass / binary).unlink(missing_ok=True)
            fake_meipass.rmdir()
            import shutil

            shutil.rmtree(fake_home, ignore_errors=True)


class TestTranscriberFormatting(unittest.TestCase):
    def test_time_str(self):
        from audio.transcriber import TranscriptSegment

        seg = TranscriptSegment(start=3661.5, end=3663.25, text="hi")
        self.assertEqual(seg.time_str, "01:01:01.500")
        self.assertEqual(seg.end_str, "01:01:03.250")

    def test_device_detect_survives_old_torch(self):
        """_detect_device must not crash when torch lacks backends.mps."""
        import audio.transcriber as tr

        class FakeBackends:
            pass  # no mps attribute, like torch < 2.3

        class FakeTorch:
            backends = FakeBackends()

            @staticmethod
            def cuda_is_available():
                return False

        fake = FakeTorch()
        fake.cuda = type("C", (), {"is_available": staticmethod(lambda: False)})
        tr._detect_device.__globals__["__builtins__"]  # touch to ensure module state
        # Simulate torch present without mps by injecting into import machinery
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "torch":
                return fake
            return real_import(name, *args, **kwargs)

        builtins.__import__ = fake_import
        try:
            device, compute = tr._detect_device()
            self.assertEqual(device, "cpu")
        finally:
            builtins.__import__ = real_import


class TestSceneDetector(unittest.TestCase):
    def test_merge_nearby(self):
        from video.scene_detector import SceneChange, _merge_nearby

        scenes = [
            SceneChange(1.0, 30, 50.0),
            SceneChange(1.2, 36, 60.0),  # closer, higher score -> replaces
            SceneChange(3.0, 90, 40.0),
        ]
        merged = _merge_nearby(scenes, 0.5)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].timestamp, 1.2)
        self.assertEqual(merged[1].timestamp, 3.0)


class TestMetadata(unittest.TestCase):
    def test_format_duration(self):
        from video.metadata import _format_duration

        self.assertEqual(_format_duration(65), "1:05")
        self.assertEqual(_format_duration(3661), "1:01:01")
        self.assertEqual(_format_duration(0), "0:00")


class TestGenerators(unittest.TestCase):
    def _fake_data(self):
        from audio.transcriber import TranscriptSegment
        from video.scene_detector import SceneChange

        segments = [
            TranscriptSegment(0.0, 2.0, "Hello <b>world</b>"),
            TranscriptSegment(2.5, 4.0, "Second line"),
            TranscriptSegment(10.0, 12.0, "Third line"),
        ]
        scenes = [SceneChange(2.4, 72, 55.0), SceneChange(9.9, 297, 40.0)]
        return segments, scenes

    def test_generate_html(self):
        import tempfile

        from html_gen.html_generator import generate_html

        segments, scenes = self._fake_data()
        out = Path(tempfile.mkdtemp()) / "out.html"
        generate_html("test", str(out), segments, scenes, {})
        content = out.read_text(encoding="utf-8")
        self.assertIn("Hello &lt;b&gt;world&lt;/b&gt;", content)
        self.assertIn("</html>", content)

    def test_generate_xlsx(self):
        import tempfile

        from xlsx_gen.generator import generate_xlsx

        segments, scenes = self._fake_data()
        out = Path(tempfile.mkdtemp()) / "out.xlsx"
        generate_xlsx("test", str(out), segments, scenes, {})
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
