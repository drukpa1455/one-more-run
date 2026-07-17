"""Visual tokens shared by One More Run terminal and presentation surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from rich.theme import Theme


@dataclass(frozen=True)
class Palette:
    background: str
    surface: str
    elevated: str
    foreground: str
    muted: str
    border: str
    primary: str
    success: str
    warning: str
    error: str
    info: str

    def rich(self) -> Theme:
        return Theme(
            {
                "omr.title": f"bold {self.primary}",
                "omr.accent": self.primary,
                "omr.text": self.foreground,
                "omr.muted": self.muted,
                "omr.keep": f"bold {self.success}",
                "omr.reject": self.error,
                "omr.crash": self.warning,
                "omr.info": self.info,
            }
        )


OPAL = Palette(
    background="#f4f7f7",
    surface="#dde7e8",
    elevated="#f7f9f9",
    foreground="#1d2425",
    muted="#4f7178",
    border="#c6d9de",
    primary="#2f7880",
    success="#1b7108",
    warning="#984f00",
    error="#b83233",
    info="#0067a1",
)

GARNET = Palette(
    background="#2c2122",
    surface="#281e1f",
    elevated="#262018",
    foreground="#f8f8f2",
    muted="#a97079",
    border="#4d4130",
    primary="#ffd7a0",
    success="#7de972",
    warning="#e6e370",
    error="#e67070",
    info="#75ece0",
)


PALETTES = {"opal": OPAL, "garnet": GARNET}
