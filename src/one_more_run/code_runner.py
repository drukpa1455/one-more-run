"""Fixed hidden-data harness for a submitted training program."""

from __future__ import annotations

import json
import math
import runpy
import sys
import time
from pathlib import Path
from typing import Any

import torch


def main() -> int:
    candidate = Path(sys.argv[1]).resolve()
    result = Path(sys.argv[2]).resolve()
    try:
        value = evaluate(candidate)
    except Exception as error:
        value = {"metric": None, "error": f"{type(error).__name__}: {error}"}
    result.write_text(json.dumps(value, allow_nan=False, separators=(",", ":")))
    return 0


def evaluate(candidate: Path) -> dict[str, Any]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(2026)
    train_inputs = torch.randn(4096, 8, device=device)
    validation_inputs = torch.randn(1024, 8, device=device)
    train_targets = target(train_inputs)
    validation_targets = target(validation_inputs)

    sys.path.insert(0, str(candidate))
    namespace = runpy.run_path(str(candidate / "train.py"), run_name="omr_candidate")
    train = namespace.get("train")
    if not callable(train):
        raise ValueError(
            "train.py must define train(inputs, targets, validation_inputs)"
        )

    torch.manual_seed(7)
    started = time.monotonic()
    predictions = train(train_inputs, train_targets, validation_inputs)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    training_seconds = time.monotonic() - started
    if not isinstance(predictions, torch.Tensor):
        raise ValueError("train() must return a torch.Tensor")
    if predictions.shape != validation_targets.shape:
        raise ValueError(
            f"train() returned shape {tuple(predictions.shape)}, expected {tuple(validation_targets.shape)}"
        )
    metric = torch.mean((predictions.detach() - validation_targets) ** 2).item()
    if not math.isfinite(metric):
        raise ValueError("validation metric is not finite")
    return {
        "metric": metric,
        "training_seconds": training_seconds,
        "device": device.type,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def target(inputs: torch.Tensor) -> torch.Tensor:
    values = (
        torch.sin(2 * inputs[:, 0])
        + 0.5 * inputs[:, 1] * inputs[:, 2]
        + 0.25 * inputs[:, 3].square()
        - 0.5 * inputs[:, 4]
    )
    return values.unsqueeze(1)


if __name__ == "__main__":
    raise SystemExit(main())
