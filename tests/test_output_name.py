"""Document name handling and progress panel reuse across runs.

Regression tests:
  - The Document name field is free text. A typed path ('sub/clip') pointed the
    writer at a directory the pipeline never creates, so the run died with
    FileNotFoundError after minutes of transcription. Characters Windows
    rejects, a typed extension, and reserved device names all reached the
    writer unfiltered.
  - ProgressPanel had no reset, so a second run opened on the first run's
    bars and log.
"""

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


class TestSafeOutputName(unittest.TestCase):
    def _name(self, raw, ext="xlsx"):
        from gui.app import safe_output_name

        return safe_output_name(raw, ext)

    def test_plain_name_gets_the_extension(self):
        self.assertEqual(self._name("clip_annotated"), "clip_annotated.xlsx")
        self.assertEqual(self._name("clip_annotated", "html"), "clip_annotated.html")

    def test_typed_extension_is_not_doubled(self):
        self.assertEqual(self._name("clip_annotated.xlsx"), "clip_annotated.xlsx")
        self.assertEqual(self._name("clip.XLSX"), "clip.xlsx")
        self.assertEqual(self._name("clip.html", "html"), "clip.html")

    def test_path_separators_cannot_escape_the_output_folder(self):
        # A separator must not survive: os.makedirs only creates the chosen
        # output folder, so a nested name is an unwritable path.
        for raw in ("sub/clip", "..\\evil", "C:/Users/x/clip", "a\\b\\c"):
            name = self._name(raw)
            self.assertNotIn("/", name)
            self.assertNotIn("\\", name)
            self.assertNotIn("..", name)

    def test_windows_invalid_characters_are_replaced(self):
        for ch in '<>:"|?*':
            self.assertNotIn(ch, self._name(f"clip{ch}name"))

    def test_reserved_device_names_are_neutralised(self):
        for reserved in ("CON", "NUL", "COM1", "LPT9", "con"):
            name = self._name(reserved)
            self.assertNotEqual(Path(name).stem.upper(), reserved.upper())

    def test_trailing_dot_and_space_are_stripped(self):
        # Windows strips these silently, which desyncs the name from the file.
        self.assertEqual(Path(self._name("clip.")).stem, "clip")
        self.assertEqual(Path(self._name("clip  ")).stem, "clip")

    def test_empty_name_still_produces_a_writable_file(self):
        for raw in ("", "   ", "???"):
            name = self._name(raw)
            self.assertTrue(name.endswith(".xlsx"))
            self.assertGreater(len(Path(name).stem), 0)

    def test_result_is_a_single_file_name(self):
        name = self._name("clip_annotated")
        self.assertEqual(Path(name).parent.name, "")


class TestSafeOutputNameWrites(unittest.TestCase):
    def test_name_from_the_field_is_writable_in_the_output_dir(self):
        """The whole point: the pipeline's final write must not explode."""
        import tempfile

        from gui.app import safe_output_name
        from xlsx_gen.generator import generate_xlsx

        out_dir = Path(tempfile.mkdtemp())
        for raw in ("clip", "sub/clip", 'a:b', "CON", "clip.xlsx", "  "):
            full = out_dir / safe_output_name(raw, "xlsx")
            generate_xlsx("v", str(full), [], [], {})
            self.assertTrue(full.exists(), f"not written for {raw!r}")


_PANEL = None


def progress_panel():
    """A ProgressPanel on the process's live Tk root, built once and never destroyed.

    ttkbootstrap allows a single root per process (Style is bound to it), and
    tests/test_dnd.py already builds the app's window in the same discovery
    run — creating a second ttkb.Window raises. So reuse tkinter's live root
    when there is one, and only stand up a root when this suite runs alone.
    ttkbootstrap's <Destroy> binding also fires ThemeChanged on a dead app
    when a suite churns roots; see the note in tests/test_dnd.py.
    """
    global _PANEL
    if _PANEL is None:
        import tkinter as tk

        from gui.progress_panel import ProgressPanel

        root = tk._default_root
        try:
            if root is None:
                import ttkbootstrap as ttkb

                root = ttkb.Window(themename="darkly")
                root.withdraw()
            _PANEL = ProgressPanel(root)
            root.update()
        except tk.TclError as exc:
            raise unittest.SkipTest(f"no display available for Tk: {exc}")
    return _PANEL


class TestProgressPanelReset(unittest.TestCase):
    def setUp(self):
        self.panel = progress_panel()

    def test_reset_clears_bars_and_log(self):
        self.panel.set_phase_status(0, 100, "42 scenes found")
        self.panel.set_phase_status(3, 100, "Done")
        self.panel.log_message("Transcribing audio...")

        self.panel.reset()

        for _lbl, pbar, lbl_status in self.panel.phases:
            self.assertEqual(pbar["value"], 0)
            self.assertEqual(lbl_status["text"], "Ready")
        self.assertEqual(self.panel.log.get("1.0", "end").strip(), "")

    def test_panel_is_disabled_after_reset(self):
        self.panel.reset()
        self.assertEqual(self.panel.log["state"], "disabled")

    def test_log_message_works_again_after_reset(self):
        self.panel.reset()
        self.panel.log_message("second run")
        self.assertIn("second run", self.panel.log.get("1.0", "end"))


if __name__ == "__main__":
    unittest.main()
