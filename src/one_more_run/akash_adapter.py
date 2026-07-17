"""Run a bounded optimization campaign against an Akash worker."""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from one_more_run.protocol import identify_candidate, improves


BASELINE = {"learning_rate": 0.02, "momentum": 0.0, "steps": 80}


@dataclass(frozen=True)
class Axis:
    name: str
    step: float
    minimum: float
    maximum: float
    integral: bool = False


AXES = (
    Axis("learning_rate", 0.03, 0.00001, 1.0),
    Axis("momentum", 0.4, 0.0, 0.99),
    Axis("steps", 40, 1, 500, integral=True),
)


class CoordinateSearch:
    """Small adaptive search that advances only from measured improvements."""

    def __init__(self, maximize: bool = False) -> None:
        self.maximize = maximize
        self.best_candidate = dict(BASELINE)
        self.best_metric: float | None = None
        self.axis_index = 0
        self.direction = 1
        self.scale = 1.0
        self.reason = "establish the baseline"
        self.pending: tuple[dict[str, Any], Axis | None] | None = None

    def propose(self) -> tuple[str, dict[str, Any]]:
        if self.pending is not None:
            raise RuntimeError("observe the pending experiment before proposing another")
        if self.best_metric is None:
            candidate = dict(self.best_candidate)
            self.pending = (candidate, None)
            return self.reason, candidate

        for _ in range(len(AXES) * 2):
            axis = AXES[self.axis_index]
            candidate = self.adjusted(axis)
            if candidate != self.best_candidate:
                action = "increase" if self.direction > 0 else "decrease"
                hypothesis = f"{self.reason}; {action} {axis.name} from the current champion"
                self.pending = (candidate, axis)
                return hypothesis, candidate
            self.reason = f"{axis.name} is at its boundary"
            if self.direction > 0:
                self.direction = -1
            else:
                self.advance_axis()
        raise RuntimeError("adaptive search space is exhausted")

    def observe(self, metric: float) -> bool:
        if self.pending is None:
            raise RuntimeError("cannot observe without a pending experiment")
        if not math.isfinite(metric):
            raise ValueError("observed metric must be finite")
        candidate, axis = self.pending
        self.pending = None

        if self.best_metric is None:
            self.best_candidate = candidate
            self.best_metric = metric
            self.reason = "baseline measured"
            return True

        advanced = improves(metric, self.best_metric, self.maximize)
        if axis is None:
            raise RuntimeError("non-baseline experiment has no search axis")
        if advanced:
            self.best_candidate = candidate
            self.best_metric = metric
            self.reason = f"{axis.name} improved the metric"
            self.advance_axis()
        elif self.direction > 0:
            self.direction = -1
            self.reason = f"increasing {axis.name} regressed"
        else:
            self.reason = f"neither direction for {axis.name} improved"
            self.advance_axis()
        return advanced

    def adjusted(self, axis: Axis) -> dict[str, Any]:
        delta = axis.step * self.scale * self.direction
        value = float(self.best_candidate[axis.name]) + delta
        value = min(axis.maximum, max(axis.minimum, value))
        candidate = dict(self.best_candidate)
        candidate[axis.name] = int(round(value)) if axis.integral else round(value, 8)
        return candidate

    def advance_axis(self) -> None:
        self.axis_index = (self.axis_index + 1) % len(AXES)
        self.direction = 1
        if self.axis_index == 0:
            self.scale /= 2


def main() -> int:
    worker = required("OMR_WORKER_URL").rstrip("/")
    token = required("OMR_WORKER_TOKEN")
    pomerium_jwt = os.environ.get("OMR_POMERIUM_JWT")
    max_runs = int(required("OMR_MAX_RUNS"))
    maximize = os.environ.get("OMR_MAXIMIZE", "0") == "1"
    hourly_usd = float(os.environ.get("OMR_HOURLY_USD", "0"))
    if not math.isfinite(hourly_usd) or hourly_usd < 0:
        raise ValueError("OMR_HOURLY_USD must be a non-negative number")

    health = request(worker, "/healthz", pomerium_jwt=pomerium_jwt)
    if health.get("device") != "cuda" and os.environ.get("OMR_ALLOW_CPU") != "1":
        raise RuntimeError("Akash worker has no CUDA device")
    compute = health.get("gpu") or health.get("device") or "unknown"
    evaluator = text(health, "evaluator")
    bid = os.environ.get("OMR_BID_UACT")
    provider = f"Akash · {compute}" + (f" · {bid} uact/block" if bid else "")
    emit({"type": "campaign.started", "provider": provider})

    search = CoordinateSearch(maximize)
    for run in range(1, max_runs + 1):
        hypothesis, candidate = search.propose()
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
        result = request(
            worker,
            "/v1/experiments",
            candidate,
            token,
            pomerium_jwt,
        )
        if text(result, "candidate_sha256") != candidate_sha256:
            raise RuntimeError("worker measured a different candidate")
        if text(result, "evaluator") != evaluator:
            raise RuntimeError("worker used a different evaluator")
        metric = number(result, "metric")
        seconds = number(result, "seconds")
        search.observe(metric)
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
    pomerium_jwt: str | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode()
    headers = {"User-Agent": "one-more-run/0.1"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if pomerium_jwt:
        headers["X-Pomerium-Authorization"] = pomerium_jwt
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
