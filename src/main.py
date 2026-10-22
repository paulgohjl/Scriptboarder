"""Scriptboarder — Convert video to annotated transcript (XLSX or HTML)."""

import sys
from pathlib import Path

# Add src to path for PyInstaller
sys.path.insert(0, str(Path(__file__).parent))

from gui.app import MainWindow
from utils import applog


def main():
    applog.setup_logging()
    applog.log_progress(
        f"Scriptboarder starting (Python {sys.version.split()[0]}, "
        f"frozen={getattr(sys, 'frozen', False)})"
    )
    app = MainWindow()
    app.run()
    applog.shutdown()


if __name__ == "__main__":
    main()
