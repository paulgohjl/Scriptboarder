"""Drag-and-drop zone widget."""

from tkinter import Canvas


class DropZone(Canvas):
    """A canvas widget that accepts click-to-browse and file drops.

    The caller registers this widget as a tkdnd drop target; the drop target
    has to be a child widget because the Tk root window does not inherit the
    tkinterdnd2 methods on Python 3.14.
    """

    def __init__(self, master, callback, **kwargs):
        super().__init__(master, bg="#2a2a2e", highlightbackground="#3a3a3e",
                         highlightthickness=2, cursor="hand2", **kwargs)

        self.callback = callback

        self._text = self.create_text(
            250, 75, text="Drop video here\nor click Browse",
            fill="#888", font=("Segoe UI", 14),
        )
        self._line = self.create_line(
            50, 145, 450, 145, fill="#3a3a3e", dash=(4, 4),
        )
