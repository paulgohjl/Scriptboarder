"""Drag-and-drop regression tests.

History of this bug:
  1. The app imported a nonexistent 'tkdnd' package, so an ImportError
     fallback silently disabled drag-and-drop.
  2. It then called tkinterdnd2.TkdndVersion(root), which does not exist
     (the version string lives at tkinterdnd2.TkinterDnD.TkdndVersion and is
     set by the library loader, not callable). The AttributeError escaped the
     `except tk.TclError` handler and crashed the app at startup.
  3. Python 3.14 refactored tkinter's class hierarchy: Tk's MRO is now
     Tk -> Misc -> Wm -> object, skipping BaseWidget. tkinterdnd2 installs
     drop_target_register/dnd_bind by patching tkinter.BaseWidget, so a plain
     tk.Tk / ttkbootstrap.Window root never gets those methods. Child widgets
     (Frame, Canvas) DO inherit them, so the drop target is registered on the
     DropZone canvas after TkinterDnD.require(root) loads the tkdnd library.

These tests deliberately avoid two traps:
  - Tk does not deliver `event generate -data` through the %D substitution
    (Tk docs: %D is an empty string for generated events), so a synthetic
    <<Drop>> cannot carry a payload. Drop parsing is tested directly instead.
  - `tkdnd::drop_target target <win>` is not a subcommand (tkdnd.tcl accepts
    only register/unregister). Registration is recorded in the
    <<DropTargetTypes>> binding, and on Windows DND_Files is stored in its
    platform-specific form (CF_HDROP), so tests assert non-empty, not a
    literal type name.

The main window is built once per process and never destroyed. ttkbootstrap
runs `ttk::ThemeChanged` -> `event generate $w <<ThemeChanged>>` from a
<Destroy> binding, which raises "can't invoke event command: application has
been destroyed" when a root is destroyed and another is then created in the
same process. That is a ttkbootstrap teardown race, unrelated to drag-and-drop
(reproduces with a plain ttkb.Window and no tkdnd at all), and it only bites
when a test suite churns several roots. The app itself builds one root, so it
is unaffected.
"""

import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_APP = None


def app_instance():
    """The main window, built once per process and left alive."""
    global _APP
    if _APP is None:
        from gui.app import MainWindow
        from utils import applog

        applog.setup_logging(Path(tempfile.mkdtemp()))
        _APP = MainWindow()
        _APP.root.withdraw()
        _APP.root.update()
    return _APP


class TestAppStarts(unittest.TestCase):
    """The startup crash is the reason drag-and-drop 'isn't working'."""

    def test_mainwindow_constructs_without_crashing(self):
        self.assertTrue(app_instance().root.winfo_exists())

    def test_gui_app_imports_tkinterdnd2_not_tkdnd(self):
        import gui.app as app

        self.assertFalse(
            hasattr(app, "tkdnd"),
            "gui.app must not import the nonexistent 'tkdnd' package",
        )
        self.assertIsNotNone(
            getattr(app, "tkinterdnd2", None),
            "gui.app must import tkinterdnd2 so drag-and-drop is enabled",
        )


class TestDropTargetRegistered(unittest.TestCase):
    def setUp(self):
        self.app = app_instance()

    def test_tkdnd_library_is_loaded_into_the_interpreter(self):
        from tkinterdnd2 import TkinterDnD

        self.assertTrue(
            TkinterDnD.TkdndVersion,
            "tkdnd Tcl library was not loaded; TkinterDnD.require() must run "
            "before any widget registers as a drop target",
        )

    def test_dropzone_is_registered_as_a_drop_target(self):
        zone = self.app.drop_zone
        types = zone.tk.splitlist(
            zone.tk.call("bind", zone._w, "<<DropTargetTypes>>")
        )
        self.assertTrue(
            types,
            "the DropZone must be registered as a drop target so files "
            "dropped on it reach the app",
        )

    def test_dropzone_is_bound_to_the_drop_event(self):
        binding = self.app.drop_zone.tk.call(
            "bind", self.app.drop_zone._w, "<<Drop>>"
        )
        self.assertTrue(
            binding,
            "the DropZone must bind <<Drop>> so dropped files are handled",
        )


class TestDropParsing(unittest.TestCase):
    """What the app does with the payload tkdnd hands it."""

    def setUp(self):
        self.app = app_instance()
        self.loaded = []
        self._real_load = self.app._load_video
        self.app._load_video = lambda path: self.loaded.append(path)

    def tearDown(self):
        self.app._load_video = self._real_load

    def drop(self, data):
        class Ev:
            pass

        Ev.data = data
        self.app._on_drop(Ev())

    def test_single_path_is_loaded(self):
        self.drop("C:/videos/clip.mp4")
        self.assertEqual(self.loaded, ["C:/videos/clip.mp4"])

    def test_path_with_spaces_is_loaded(self):
        self.drop("{C:/videos/my holiday clip.mp4}")
        self.assertEqual(self.loaded, ["C:/videos/my holiday clip.mp4"])

    def test_first_of_several_dropped_files_is_loaded(self):
        self.drop("C:/a.mp4 {C:/b b.mp4} C:/c.mp4")
        self.assertEqual(self.loaded, ["C:/a.mp4"])

    def test_empty_drop_does_not_load_anything(self):
        self.drop("")
        self.assertEqual(self.loaded, [])


if __name__ == "__main__":
    unittest.main()
