"""Progress panel with phase progress bars and log display."""

from tkinter import scrolledtext
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *


class ProgressPanel(ttkb.Frame):
    """Shows processing progress and log output."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Phase labels + progress
        self.phases = []
        for label in ["Scene Detection", "Capture Screenshots", "Transcribe Audio", "Generate Output"]:
            phase_frame = ttkb.Frame(self)
            phase_frame.pack(fill=X, pady=(2, 0))

            lbl = ttkb.Label(phase_frame, text=label, font=("Segoe UI", 9), width=20)
            lbl.pack(side=LEFT, padx=(0, 8))

            pbar = ttkb.Progressbar(phase_frame, bootstyle="info-striped", length=300)
            pbar.pack(side=LEFT, fill=X, expand=True)

            lbl_status = ttkb.Label(phase_frame, text="Ready", font=("Segoe UI", 9), foreground="#888")
            lbl_status.pack(side=LEFT, padx=(8, 0))

            self.phases.append((lbl, pbar, lbl_status))

        # Log area
        log_frame = ttkb.Frame(self)
        log_frame.pack(fill=BOTH, expand=True, pady=(10, 0))
        ttkb.Label(log_frame, text="Log:", font=("Segoe UI", 9)).pack(anchor=W)

        self.log = scrolledtext.ScrolledText(
            log_frame, height=8, wrap=WORD,
            font=("Consolas", 9), state=DISABLED,
            bg="#1a1a1e", fg="#ccc",
        )
        self.log.pack(fill=BOTH, expand=True)

    def set_phase_status(self, idx: int, pct: float, status: str):
        if idx < len(self.phases):
            lbl, pbar, lbl_status = self.phases[idx]
            pbar.config(value=pct)
            lbl_status.config(text=status)

    def reset(self):
        """Clear bars and log; a second run must not open on the first run's state."""
        for _lbl, pbar, lbl_status in self.phases:
            pbar.config(value=0)
            lbl_status.config(text="Ready")
        self.log.config(state=NORMAL)
        self.log.delete("1.0", END)
        self.log.config(state=DISABLED)

    def log_message(self, msg: str):
        self.log.config(state=NORMAL)
        self.log.insert(END, f"[{self._now()}] {msg}\n")
        self.log.see(END)
        self.log.config(state=DISABLED)

    def _now(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
