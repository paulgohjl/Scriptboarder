"""Tests for utils.applog: file logging of progress + errors."""

import logging
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


def _reset_logger():
    logger = logging.getLogger("scriptboarder")
    for h in list(logger.handlers):
        h.close()
        logger.removeHandler(h)


class TestAppLog(unittest.TestCase):
    def setUp(self):
        _reset_logger()

    def tearDown(self):
        _reset_logger()

    def test_default_log_dir_is_project_root(self):
        from utils.applog import default_log_dir

        # From a source checkout the log lives in the program's main folder
        self.assertEqual(default_log_dir(), SRC.parent)

    def test_setup_logging_writes_to_given_dir(self):
        from utils import applog

        tmp = Path(tempfile.mkdtemp()) / "logs"
        path = applog.setup_logging(tmp)
        self.assertIsNotNone(path)
        self.assertEqual(path.name, "scriptboarder.log")

        applog.log_progress("Transcribing audio...")
        applog.shutdown()

        content = path.read_text(encoding="utf-8")
        self.assertIn("Transcribing audio...", content)

    def test_log_error_includes_traceback(self):
        from utils import applog

        tmp = Path(tempfile.mkdtemp())
        path = applog.setup_logging(tmp)
        try:
            raise ValueError("boom")
        except ValueError as e:
            applog.log_error("Processing failed", e)
        applog.shutdown()

        content = path.read_text(encoding="utf-8")
        self.assertIn("Processing failed", content)
        self.assertIn("ValueError: boom", content)
        self.assertIn("Traceback", content)

    def test_setup_logging_falls_back_to_temp(self):
        from utils import applog

        # A path that cannot be created (parent is a file, not a dir)
        blocker = Path(tempfile.mkdtemp()) / "blocker"
        blocker.write_text("not a dir")
        path = applog.setup_logging(blocker / "sub")
        self.assertIsNotNone(path)
        self.assertEqual(path.parent, Path(tempfile.gettempdir()))
        applog.shutdown()

    def test_setup_logging_never_raises(self):
        from utils import applog

        # Unwritable everywhere: both default dir and temp dir are files
        real_gettempdir = tempfile.gettempdir
        real_default = applog.default_log_dir
        blocker = Path(tempfile.mkdtemp()) / "blocker2"
        blocker.write_text("not a dir")
        tempfile.gettempdir = lambda: str(blocker)
        applog.default_log_dir = lambda: blocker
        try:
            path = applog.setup_logging()
            self.assertIsNone(path)
            # Logging calls must be safe no-ops
            applog.log_progress("x")
            applog.log_error("y", RuntimeError("z"))
        finally:
            tempfile.gettempdir = real_gettempdir
            applog.default_log_dir = real_default


if __name__ == "__main__":
    unittest.main()
