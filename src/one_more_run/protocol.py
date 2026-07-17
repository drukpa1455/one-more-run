"""Stable identities shared by the controller, adapters, and workers."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
from typing import Any


MAX_CANDIDATE_BYTES = 256 * 1024
NUMERIC_EVALUATOR = "smoke.linear-regression.v1"
CODE_EVALUATOR = "code.nonlinear-regression.v1"


def improves(metric: float, incumbent: float | None, maximize: bool) -> bool:
    """Return whether a measured metric advances the campaign."""
    if incumbent is None:
        return True
    return metric > incumbent if maximize else metric < incumbent


def identify_candidate(value: Any) -> tuple[dict[str, Any], str]:
    """Return a normalized JSON object and its SHA-256 digest."""
    if not isinstance(value, dict):
        raise ValueError("candidate must be a JSON object")
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ValueError("candidate must contain only finite JSON values") from error
    if len(encoded) > MAX_CANDIDATE_BYTES:
        raise ValueError(f"candidate exceeds {MAX_CANDIDATE_BYTES} bytes")
    normalized = json.loads(encoded)
    return normalized, hashlib.sha256(encoded).hexdigest()


def identify_code_candidate(value: Any) -> tuple[dict[str, Any], str]:
    """Validate and identify a bounded, modular Python candidate."""
    if not isinstance(value, dict) or value.keys() != {"files"}:
        raise ValueError("code candidate must contain a files object")
    files = value.get("files")
    if not isinstance(files, dict) or not 1 <= len(files) <= 32:
        raise ValueError("code candidate must contain 1-32 files")
    for name, source in files.items():
        if not isinstance(name, str) or not safe_code_path(name):
            raise ValueError(f"unsafe candidate path: {name!r}")
        if not isinstance(source, str):
            raise ValueError(f"candidate file must be source text: {name}")
    if not files.get("train.py", "").strip():
        raise ValueError("candidate must contain a non-empty train.py")
    return identify_candidate(value)


def safe_code_path(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        len(name) <= 160
        and "\\" not in name
        and not path.is_absolute()
        and path.as_posix() == name
        and all(
            part not in {"", ".", ".."} and not part.startswith(".")
            for part in path.parts
        )
        and path.suffix == ".py"
    )
