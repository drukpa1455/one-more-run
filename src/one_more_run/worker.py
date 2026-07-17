"""Fixed, bounded experiment evaluator."""

from __future__ import annotations

import json
import math
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from one_more_run.protocol import identify_candidate

try:
    import torch
except ImportError:
    torch = None


MAX_BODY_BYTES = 4_096
RUN_LOCK = threading.Lock()
EVALUATOR = "smoke.linear-regression.v1"
CONFIGURED_TOKEN = os.environ.get("OMR_WORKER_TOKEN")
TOKEN = CONFIGURED_TOKEN or secrets.token_urlsafe(32)


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"one-more-run worker listening on :{port}", file=sys.stderr, flush=True)
    if CONFIGURED_TOKEN:
        print("worker token supplied by environment", file=sys.stderr, flush=True)
    else:
        print(f"worker token: {TOKEN}", file=sys.stderr, flush=True)
    server.serve_forever()


class Handler(BaseHTTPRequestHandler):
    server_version = "one-more-run/0.1"

    def do_GET(self) -> None:
        if self.path != "/healthz":
            self.send_json(404, {"error": "not found"})
            return
        self.send_json(200, {"status": "ok", "evaluator": EVALUATOR, **device_info()})

    def do_POST(self) -> None:
        if self.path != "/v1/experiments":
            self.send_json(404, {"error": "not found"})
            return
        if not self.authorized():
            self.send_json(401, {"error": "unauthorized"})
            return
        if not RUN_LOCK.acquire(blocking=False):
            self.send_json(409, {"error": "an experiment is already running"})
            return

        try:
            result = run_experiment(self.read_json())
            self.send_json(200, result)
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
        except Exception as error:
            print(f"experiment failed: {error}", file=sys.stderr, flush=True)
            self.send_json(500, {"error": "experiment failed"})
        finally:
            RUN_LOCK.release()

    def authorized(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        return secrets.compare_digest(supplied, f"Bearer {TOKEN}")

    def read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("invalid content length") from error
        if length < 1 or length > MAX_BODY_BYTES:
            raise ValueError(f"request body must be 1-{MAX_BODY_BYTES} bytes")
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as error:
            raise ValueError("request body must be JSON") from error
        if not isinstance(value, dict):
            raise ValueError("request body must be an object")
        return value

    def send_json(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def run_experiment(candidate: dict[str, Any]) -> dict[str, Any]:
    learning_rate, momentum, steps = validate(candidate)
    _, candidate_sha256 = identify_candidate(
        {"learning_rate": learning_rate, "momentum": momentum, "steps": steps}
    )
    if torch is not None and torch.cuda.is_available():
        result = run_torch(learning_rate, momentum, steps)
    else:
        result = run_python(learning_rate, momentum, steps)
    return {
        "candidate_sha256": candidate_sha256,
        "evaluator": EVALUATOR,
        **result,
    }


def validate(candidate: dict[str, Any]) -> tuple[float, float, int]:
    unknown = candidate.keys() - {"learning_rate", "momentum", "steps"}
    if unknown:
        raise ValueError(f"unknown candidate fields: {', '.join(sorted(unknown))}")
    learning_rate = finite_number(candidate, "learning_rate")
    momentum = finite_number(candidate, "momentum")
    steps = candidate.get("steps")
    if not isinstance(steps, int) or isinstance(steps, bool) or not 1 <= steps <= 500:
        raise ValueError("steps must be an integer from 1 to 500")
    if not 0.00001 <= learning_rate <= 1.0:
        raise ValueError("learning_rate must be from 0.00001 to 1.0")
    if not 0.0 <= momentum <= 0.99:
        raise ValueError("momentum must be from 0.0 to 0.99")
    return learning_rate, momentum, steps


def finite_number(candidate: dict[str, Any], name: str) -> float:
    value = candidate.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def device_info() -> dict[str, str | None]:
    if torch is not None and torch.cuda.is_available():
        return {"device": "cuda", "gpu": torch.cuda.get_device_name(0)}
    return {"device": "cpu", "gpu": None}


def run_torch(learning_rate: float, momentum: float, steps: int) -> dict[str, Any]:
    device = torch.device("cuda")
    torch.manual_seed(2026)
    inputs = torch.randn(4096, 256, device=device) / math.sqrt(256)
    truth = torch.randn(256, 64, device=device)
    targets = inputs @ truth
    weights = torch.zeros_like(truth, requires_grad=True)
    velocity = torch.zeros_like(weights)

    torch.cuda.synchronize()
    started = time.monotonic()
    for _ in range(steps):
        loss = ((inputs @ weights - targets) ** 2).mean()
        loss.backward()
        with torch.no_grad():
            velocity.mul_(momentum).add_(weights.grad)
            weights.sub_(velocity, alpha=learning_rate)
            weights.grad = None
    with torch.no_grad():
        metric = ((inputs @ weights - targets) ** 2).mean().item()
    torch.cuda.synchronize()

    return {
        "metric": metric,
        "seconds": time.monotonic() - started,
        **device_info(),
    }


def run_python(learning_rate: float, momentum: float, steps: int) -> dict[str, Any]:
    inputs = [index / 32 for index in range(-32, 33)]
    targets = [3 * value - 0.25 for value in inputs]
    weight = bias = weight_velocity = bias_velocity = 0.0

    started = time.monotonic()
    for _ in range(steps):
        errors = [
            weight * value + bias - target for value, target in zip(inputs, targets)
        ]
        weight_gradient = (
            2 * sum(error * value for error, value in zip(errors, inputs)) / len(inputs)
        )
        bias_gradient = 2 * sum(errors) / len(inputs)
        weight_velocity = momentum * weight_velocity + weight_gradient
        bias_velocity = momentum * bias_velocity + bias_gradient
        weight -= learning_rate * weight_velocity
        bias -= learning_rate * bias_velocity
    metric = sum(
        (weight * value + bias - target) ** 2 for value, target in zip(inputs, targets)
    )
    metric /= len(inputs)

    return {
        "metric": metric,
        "seconds": time.monotonic() - started,
        "device": "cpu",
        "gpu": None,
    }


if __name__ == "__main__":
    main()
