"""Platform layer tests: everything the macOS port depends on.

The app was Windows-only in five places that no single test covered:
  - os.startfile() to open the finished document (AttributeError on macOS)
  - ffmpeg.exe / %LOCALAPPDATA% hard-coded in two divergent finders
  - a Windows-only ffmpeg zip as the only download source
  - Segoe UI / Consolas font families that do not exist on macOS
  - sys.exit() in the ffmpeg download path, which raises SystemExit on the
    pipeline's worker thread, past the thread's `except Exception`, leaving
    the UI parked on the progress phase with no error shown
"""

import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from utils import platform_paths as pp  # noqa: E402


class TestBinaryName(unittest.TestCase):
    def test_windows_uses_the_exe_suffix(self):
        with patch.object(pp, "IS_WINDOWS", True), patch.object(pp, "IS_MACOS", False):
            self.assertEqual(pp.ffmpeg_binary_name(), "ffmpeg.exe")

    def test_posix_has_no_suffix(self):
        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", True):
            self.assertEqual(pp.ffmpeg_binary_name(), "ffmpeg")


class TestCacheDir(unittest.TestCase):
    def test_windows_uses_localappdata_layout(self):
        home = Path(tempfile.gettempdir()) / "sb_home_win"
        with patch.object(pp, "IS_WINDOWS", True), patch.object(pp, "IS_MACOS", False):
            with patch("pathlib.Path.home", return_value=home):
                self.assertEqual(
                    pp.cache_dir(),
                    home / "AppData" / "Local" / "scriptboarder",
                )

    def test_macos_uses_the_application_support_folder(self):
        home = Path(tempfile.gettempdir()) / "sb_home_mac"
        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", True):
            with patch("pathlib.Path.home", return_value=home):
                self.assertEqual(
                    pp.cache_dir(),
                    home / "Library" / "Application Support" / "scriptboarder",
                )

    def test_linux_uses_the_xdg_layout(self):
        home = Path(tempfile.gettempdir()) / "sb_home_linux"
        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", False):
            with patch("pathlib.Path.home", return_value=home):
                self.assertEqual(
                    pp.cache_dir(), home / ".local" / "share" / "scriptboarder"
                )

    def test_cache_dir_is_never_the_windows_path_on_macos(self):
        """The bug this guards: a mac build writing to ~/AppData/Local.

        Checked below the home prefix because a Windows temp dir already
        contains 'AppData' in its own path.
        """
        home = Path(tempfile.gettempdir()) / "sb_home_mac2"
        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", True):
            with patch("pathlib.Path.home", return_value=home):
                below_home = pp.cache_dir().relative_to(home)
                self.assertNotIn("AppData", below_home.parts)
                self.assertEqual(below_home.parts[:2], ("Library", "Application Support"))


class TestFonts(unittest.TestCase):
    def test_macos_gets_a_font_that_exists_there(self):
        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", True):
            self.assertNotEqual(pp.ui_font(), "Segoe UI")
            self.assertNotEqual(pp.mono_font(), "Consolas")

    def test_windows_keeps_segoe_ui(self):
        with patch.object(pp, "IS_WINDOWS", True), patch.object(pp, "IS_MACOS", False):
            self.assertEqual(pp.ui_font(), "Segoe UI")
            self.assertEqual(pp.mono_font(), "Consolas")


class TestOpenFile(unittest.TestCase):
    def test_windows_uses_startfile(self):
        import utils.platform_paths as mod

        with patch.object(mod, "IS_WINDOWS", True), patch.object(mod, "IS_MACOS", False):
            with patch("os.startfile") as startfile:
                pp.open_file("out.xlsx")
                startfile.assert_called_once_with("out.xlsx")

    def test_macos_uses_open(self):
        """os.startfile does not exist on macOS; `open` is its equivalent."""
        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", True):
            with patch("subprocess.run") as run:
                pp.open_file("out.xlsx")
                self.assertEqual(run.call_args[0][0], ["open", "out.xlsx"])

    def test_linux_uses_xdg_open(self):
        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", False):
            with patch("subprocess.run") as run:
                pp.open_file("out.xlsx")
                self.assertEqual(run.call_args[0][0], ["xdg-open", "out.xlsx"])

    def test_app_opens_the_output_without_startfile(self):
        """gui.app must not call os.startfile directly — it is Windows-only."""
        import inspect

        import gui.app as app

        source = inspect.getsource(app.MainWindow._open_output)
        self.assertNotIn("os.startfile", source)


class TestFindFfmpeg(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        # Nothing installed on the host must leak into these assertions.
        for name in ("bundled_ffmpeg", "vendored_ffmpeg", "system_ffmpeg"):
            p = patch.object(pp, name, return_value=None)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(pp, "cache_dir", return_value=self.tmp)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        self.env.stop()

    def test_falls_back_to_a_bare_command_when_nothing_is_found(self):
        self.assertEqual(pp.find_ffmpeg(), "ffmpeg")

    def test_env_var_is_honoured(self):
        target = self.tmp / "my-ffmpeg"
        target.write_bytes(b"x")
        os.environ["FFMPEG_PATH"] = str(target)
        self.assertEqual(pp.find_ffmpeg(), str(target))

    def test_downloaded_copy_is_used(self):
        cached = self.tmp / pp.ffmpeg_binary_name()
        cached.write_bytes(b"x")
        self.assertEqual(pp.find_ffmpeg(), str(cached))

    def test_bundle_wins_over_the_downloaded_copy(self):
        """A packaged app must use its pinned ffmpeg, not a stale download."""
        bundle = self.tmp / "bundle" / pp.ffmpeg_binary_name()
        bundle.parent.mkdir(exist_ok=True)
        bundle.write_bytes(b"x")
        (self.tmp / pp.ffmpeg_binary_name()).write_bytes(b"x")
        pp.bundled_ffmpeg.return_value = str(bundle)
        self.assertEqual(pp.find_ffmpeg(), str(bundle))

    def test_system_ffmpeg_is_used_before_giving_up(self):
        brew = self.tmp / "opt_homebrew_bin_ffmpeg"
        brew.write_bytes(b"x")
        pp.system_ffmpeg.return_value = str(brew)
        self.assertEqual(pp.find_ffmpeg(), str(brew))


class TestSystemFfmpeg(unittest.TestCase):
    """Runs unstubbed: TestFindFfmpeg stubs system_ffmpeg, this class must not."""

    def test_macos_looks_where_homebrew_installs(self):
        """A packaged mac app does not inherit the user's shell PATH.

        Paths are compared as Path objects: str() of a POSIX path normalises
        to backslashes when the test runs on a Windows host.
        """
        homebrew = Path("/opt/homebrew/bin/ffmpeg")
        found = []

        def fake_access(path, mode):
            found.append(Path(path))
            return Path(path) == homebrew

        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", True):
            with patch("shutil.which", return_value=None), patch(
                "pathlib.Path.is_file", return_value=True
            ), patch("os.access", side_effect=fake_access):
                self.assertEqual(Path(pp.system_ffmpeg()), homebrew)
        self.assertIn(homebrew, found)

    def test_returns_none_when_no_ffmpeg_is_installed(self):
        """So the caller knows to download rather than run a missing binary."""
        with patch("shutil.which", return_value=None), patch(
            "pathlib.Path.is_file", return_value=False
        ):
            self.assertIsNone(pp.system_ffmpeg())


class TestDownloadSource(unittest.TestCase):
    def test_windows_downloads_the_gyan_build(self):
        with patch.object(pp, "IS_WINDOWS", True), patch.object(pp, "IS_MACOS", False):
            self.assertIn("gyan.dev", pp.ffmpeg_download_url())

    def test_macos_does_not_download_a_windows_archive(self):
        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", True):
            url = pp.ffmpeg_download_url()
            self.assertNotIn("gyan.dev", url)
            self.assertTrue(url.startswith("https://"))

    def test_arm64_note_mentions_rosetta(self):
        with patch.object(pp, "IS_MACOS", True), patch(
            "platform.machine", return_value="arm64"
        ):
            self.assertIn("Rosetta", pp.ffmpeg_arch_note())


class TestEnsureFfmpeg(unittest.TestCase):
    """utils.deps must return a usable ffmpeg and fail in a way the GUI shows."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        for name in ("bundled_ffmpeg", "vendored_ffmpeg", "system_ffmpeg"):
            p = patch.object(pp, name, return_value=None)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(pp, "cache_dir", return_value=self.tmp)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        self.env.stop()

    def test_returns_the_bundled_binary_name_on_macos(self):
        from utils.deps import ensure_ffmpeg_path

        bundle = self.tmp / "bundle" / "ffmpeg"
        bundle.parent.mkdir(exist_ok=True)
        bundle.write_bytes(b"x")
        pp.bundled_ffmpeg.return_value = str(bundle)
        self.assertEqual(ensure_ffmpeg_path(), str(bundle))

    def test_download_failure_raises_runtime_error_not_systemexit(self):
        """sys.exit() on the worker thread bypasses `except Exception` and
        leaves the UI on the progress phase with no message."""
        from utils.deps import ensure_ffmpeg_path

        with patch.object(pp, "IS_WINDOWS", True), patch.object(pp, "IS_MACOS", False):
            with patch("urllib.request.urlretrieve", side_effect=OSError("no net")):
                with self.assertRaises(RuntimeError):
                    ensure_ffmpeg_path()

    @unittest.skipIf(pp.IS_WINDOWS, "Windows chmod does not model the exec bit")
    def test_download_writes_an_executable_binary(self):
        """POSIX needs the exec bit; a downloaded ffmpeg without it is 'not found'."""
        import stat

        from utils.deps import ensure_ffmpeg_path

        def fake_download(url, dest):
            with zipfile.ZipFile(dest, "w") as z:
                # evermeet.cx and gyan.dev both nest the binary under bin/
                z.writestr("ffmpeg-7.0/bin/ffmpeg", "#!/bin/sh\nexit 0\n")
                z.writestr("ffmpeg-7.0/LICENSE.txt", "license")

        with patch.object(pp, "IS_WINDOWS", False), patch.object(pp, "IS_MACOS", True):
            with patch("urllib.request.urlretrieve", side_effect=fake_download):
                result = ensure_ffmpeg_path()

        self.assertEqual(result, str(self.tmp / "ffmpeg"))
        self.assertTrue(Path(result).is_file())
        mode = Path(result).stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "downloaded ffmpeg is not executable")
        self.assertFalse((self.tmp / "ffmpeg.zip").exists(), "the zip was left behind")


class TestSpecIsPlatformAware(unittest.TestCase):
    def test_spec_does_not_hardcode_the_exe_suffix(self):
        """A mac build must bundle `ffmpeg`, not `ffmpeg.exe`."""
        spec = (SRC.parent / "scriptboarder.spec").read_text(encoding="utf-8")
        self.assertIn('"ffmpeg.exe" if IS_WINDOWS else "ffmpeg"', spec)
        self.assertIn("BUNDLE", spec)

    def test_spec_does_not_force_x86_64_on_macos(self):
        """target_arch='x86_64' fails the build on an Apple Silicon host."""
        spec = (SRC.parent / "scriptboarder.spec").read_text(encoding="utf-8")
        self.assertIn("if IS_WINDOWS:\n    exe_kwargs['target_arch'] = 'x86_64'", spec)


if __name__ == "__main__":
    unittest.main()
