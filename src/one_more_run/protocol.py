"""Stable identities shared by the controller, adapters, and workers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


MAX_CANDIDATE_BYTES = 256 * 1024


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
