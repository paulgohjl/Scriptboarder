"""Row heights in the XLSX output must scale to the transcript text."""

import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


class TestWrappedLineCount(unittest.TestCase):
    def test_short_text_one_line(self):
        from xlsx_gen.generator import _wrapped_line_count

        self.assertEqual(_wrapped_line_count("hello world", 58), 1)
        self.assertEqual(_wrapped_line_count("", 58), 1)

    def test_wraps_at_width(self):
        from xlsx_gen.generator import _wrapped_line_count

        # 3 words of 20 chars: only 2 fit per line at width 58 (20+1+20=41, +21>58)
        text = " ".join(["a" * 20] * 3)
        self.assertEqual(_wrapped_line_count(text, 58), 2)

    def test_long_paragraph(self):
        from xlsx_gen.generator import _wrapped_line_count

        text = " ".join(["word"] * 120)  # 120 words x 5 chars = 599 chars
        self.assertGreater(_wrapped_line_count(text, 58), 10)


class TestRowHeights(unittest.TestCase):
    def _generate(self, segments, scenes, cache):
        from xlsx_gen.generator import generate_xlsx

        out = Path(tempfile.mkdtemp()) / "out.xlsx"
        generate_xlsx("test", str(out), segments, scenes, cache)

        from openpyxl import load_workbook

        return load_workbook(out)["Transcript"]

    def test_heights_scale_with_text(self):
        from audio.transcriber import TranscriptSegment
        from video.scene_detector import SceneChange

        short = TranscriptSegment(0.0, 1.0, "Short line.")
        long = TranscriptSegment(1.0, 5.0, " ".join(["word"] * 120))
        ws = self._generate([short, long], [], {})

        h_short = ws.row_dimensions[3].height
        h_long = ws.row_dimensions[4].height
        self.assertEqual(h_short, 15)
        self.assertGreater(h_long, 60)
        self.assertGreater(h_long, h_short)

    def test_screenshot_row_fits_image(self):
        from PIL import Image as PILImage

        from audio.transcriber import TranscriptSegment
        from video.scene_detector import SceneChange

        tmp = Path(tempfile.mkdtemp())
        shot = tmp / "shot.png"
        PILImage.new("RGB", (640, 360)).save(shot)

        seg = TranscriptSegment(2.0, 3.0, "A caption")
        scene = SceneChange(2.0, 50, 30.0)
        ws = self._generate([seg], [scene], {2.0: str(shot)})

        self.assertGreaterEqual(ws.row_dimensions[3].height, 70)

    def test_screenshot_row_grows_for_long_text(self):
        from PIL import Image as PILImage

        from audio.transcriber import TranscriptSegment
        from video.scene_detector import SceneChange

        tmp = Path(tempfile.mkdtemp())
        shot = tmp / "shot.png"
        PILImage.new("RGB", (640, 360)).save(shot)

        seg = TranscriptSegment(2.0, 3.0, " ".join(["word"] * 120))
        scene = SceneChange(2.0, 50, 30.0)
        ws = self._generate([seg], [scene], {2.0: str(shot)})

        self.assertGreater(ws.row_dimensions[3].height, 70)


if __name__ == "__main__":
    unittest.main()
