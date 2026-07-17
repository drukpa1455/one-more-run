"""Render an illustrative One More Run terminal frame for design capture.

This is a deterministic visual mock, not a recorded experiment or benchmark.
"""

from __future__ import annotations

import argparse

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from one_more_run.theme import PALETTES


def main() -> int:
    args = parser().parse_args()
    palette = PALETTES[args.theme]
    console = Console(theme=palette.rich(), width=104, color_system="truecolor")

    title = Text("ONE MORE RUN", style="omr.title")
    title.append("  nested research · outer 03/03", style="omr.muted")
    console.print(
        Panel(
            Text.from_markup(
                "minimize held-out validation MSE\n"
                "[omr.muted]Akash · NVIDIA T4 · protected mode · memory recalled[/omr.muted]"
            ),
            title=title,
            border_style="omr.accent",
        )
    )

    console.print(" INNER LOOP  ", style="omr.title", end="")
    console.print("Codex turn 2/3", style="omr.muted")
    console.print("  recall   ", style="omr.info", end="")
    console.print("Fourier features helped this task family; wide MLPs overfit.")
    console.print("  edit     ", style="omr.accent", end="")
    console.print("features.py +24 −3   model.py +11 −6   train.py +8 −4")
    console.print("  verify   ", style="omr.keep", end="")
    console.print("contract ✓   syntax ✓   candidate 9b18e0a4 ready")

    table = Table(
        title="OUTER LOOP  measured evidence",
        title_style="omr.title",
        border_style="omr.muted",
        header_style="omr.muted",
        expand=True,
    )
    table.add_column("RUN", justify="right", width=4)
    table.add_column("SHA", width=9)
    table.add_column("HYPOTHESIS", ratio=1)
    table.add_column("MSE", justify="right", width=10)
    table.add_column("DECISION", width=9)
    table.add_column("GPU", justify="right", width=8)
    table.add_row("1", "a91c27bf", "baseline program", "0.084210", "KEEP", "18.2s")
    table.add_row(
        "2", "4d03f1aa", "residual MLP + cosine decay", "0.031844", "KEEP", "24.7s"
    )
    table.add_row(
        "3",
        "9b18e0a4",
        "Fourier features + smaller residual trunk",
        "0.019736",
        Text("KEEP", style="omr.keep"),
        "22.9s",
    )
    console.print(table)
    console.print(" receipt  ", style="omr.info", end="")
    console.print("candidate 9b18e0a4 · evaluator code.nonlinear-regression.v1")
    console.print(" memory   ", style="omr.info", end="")
    console.print("retained hypothesis → candidate → metric → KEEP")
    console.print(
        " illustrative design mock · replace with live evidence when available",
        style="omr.muted",
    )
    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--theme", choices=PALETTES, default="garnet")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
