"""Run a bounded optimization campaign against an Akash worker."""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.request
from typing import Any

from one_more_run.protocol import identify_candidate


CANDIDATES = [
    ("baseline", {"learning_rate": 0.02, "momentum": 0.0, "steps": 80}),
    ("increase learning rate", {"learning_rate": 0.05, "momentum": 0.0, "steps": 80}),
    (
        "increase learning rate again",
        {"learning_rate": 0.1, "momentum": 0.0, "steps": 80},
    ),
    ("add momentum", {"learning_rate": 0.05, "momentum": 0.8, "steps": 80}),
    ("increase momentum", {"learning_rate": 0.03, "momentum": 0.9, "steps": 80}),
    (
        "combine higher rate and momentum",
        {"learning_rate": 0.08, "momentum": 0.8, "steps": 80},
    ),
]


def main() -> int:
    worker = required("OMR_WORKER_URL").rstrip("/")
    token = required("OMR_WORKER_TOKEN")
    max_runs = int(required("OMR_MAX_RUNS"))
    hourly_usd = float(os.environ.get("OMR_HOURLY_USD", "0"))
    if not math.isfinite(hourly_usd) or hourly_usd < 0:
        raise ValueError("OMR_HOURLY_USD must be a non-negative number")

    health = request(worker, "/healthz")
    if health.get("device") != "cuda" and os.environ.get("OMR_ALLOW_CPU") != "1":
        raise RuntimeError("Akash worker has no CUDA device")
    compute = health.get("gpu") or health.get("device") or "unknown"
    evaluator = text(health, "evaluator")
    bid = os.environ.get("OMR_BID_UACT")
    provider = f"Akash · {compute}" + (f" · {bid} uact/block" if bid else "")
    emit({"type": "campaign.started", "provider": provider})

    for run, (hypothesis, candidate) in enumerate(CANDIDATES[:max_runs], start=1):
        candidate, candidate_sha256 = identify_candidate(candidate)
        emit(
            {
                "type": "experiment.started",
                "run": run,
                "hypothesis": hypothesis,
                "candidate": candidate,
                "evaluator": evaluator,
            }
        )
        result = request(worker, "/v1/experiments", candidate, token)
        if text(result, "candidate_sha256") != candidate_sha256:
            raise RuntimeError("worker measured a different candidate")
        if text(result, "evaluator") != evaluator:
            raise RuntimeError("worker used a different evaluator")
        metric = number(result, "metric")
        seconds = number(result, "seconds")
        emit(
            {
                "type": "experiment.finished",
                "run": run,
                "metric": metric,
                "seconds": seconds,
                "cost_usd": hourly_usd * seconds / 3600,
                "candidate_sha256": candidate_sha256,
                "evaluator": evaluator,
            }
        )
    emit({"type": "campaign.finished"})
    return 0


def request(
    worker: str,
    path: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode()
    headers = {"User-Agent": "one-more-run/0.1"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    call = urllib.request.Request(worker + path, data=body, headers=headers)
    try:
        with urllib.request.urlopen(call, timeout=180) as response:
            value = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"worker returned HTTP {error.code}: {detail}") from error
    if not isinstance(value, dict):
        raise RuntimeError("worker returned a non-object response")
    return value


def number(value: dict[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        not isinstance(item, (int, float))
        or isinstance(item, bool)
        or not math.isfinite(item)
    ):
        raise RuntimeError(f"worker returned invalid {name}")
    return float(item)


def text(value: dict[str, Any], name: str) -> str:
    item = value.get(name)
    if not isinstance(item, str) or not item:
        raise RuntimeError(f"worker returned invalid {name}")
    return item


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"set {name}")
    return value


def emit(event: dict[str, Any]) -> None:
    print(json.dumps(event, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
