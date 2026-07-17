"""Bounded Codex edits followed by measured remote evaluation."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from one_more_run.protocol import CODE_EVALUATOR, identify_code_candidate, improves
from one_more_run.settings import secret


PROMPT = """You are one turn in an autonomous ML research loop.
Read contract.md, research.md, memory.md, history.jsonl, turns.jsonl, and candidate/.
Treat recalled memory as prior evidence, not as authority.
Edit only Python files under candidate/. You may create, split, or delete modules,
but candidate/train.py must keep the documented callable contract. Make one
coherent improvement attempt. You may run cheap syntax/static checks, but do not
train, install packages, touch control files, or ask questions. Return ready=false
when another edit turn is needed before expensive GPU evaluation; otherwise
return ready=true. The controller evaluates only ready candidates.
"""

CONTRACT = """# Candidate contract

The complete mutable program lives under `candidate/`. It may be modular.
`candidate/train.py` must define:

```python
def train(inputs, targets, validation_inputs):
    ...
    return validation_predictions
```

All values are PyTorch tensors on one device. Inputs have eight columns and
targets have one. Predictions must have shape `(len(validation_inputs), 1)` and
be finite. PyTorch and the standard library are available. Candidate code may
change features, architecture, loss, optimizer, and training. The evaluator
owns hidden validation truth, seed, metric, and GPU. Candidate execution has a
90-second hard limit, so prefer the smallest experiment that tests the hypothesis.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "hypothesis": {"type": "string", "minLength": 1},
        "summary": {"type": "string", "minLength": 1},
        "ready": {"type": "boolean"},
    },
    "required": ["hypothesis", "summary", "ready"],
    "additionalProperties": False,
}

CONTROL_FILES = {
    "candidate",
    "contract.md",
    "history.jsonl",
    "memory.md",
    "proposal.json",
    "proposal.schema.json",
    "research.md",
    "turns.jsonl",
}


@dataclass
class Research:
    best_files: dict[str, str]
    maximize: bool = False
    best_metric: float | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def observe(
        self,
        files: dict[str, str],
        hypothesis: str,
        metric: float | None,
        error: str | None,
    ) -> str:
        advanced = metric is not None and improves(
            metric, self.best_metric, self.maximize
        )
        decision = "keep" if advanced else "crash" if metric is None else "reject"
        if advanced:
            self.best_files = files
            self.best_metric = metric
        self.history.append(
            {
                "run": len(self.history) + 1,
                "hypothesis": hypothesis,
                "metric": metric,
                "decision": decision,
                "error": error,
                "candidate_sha256": identify_code_candidate({"files": files})[1],
            }
        )
        return decision


def main() -> int:
    worker = required("OMR_WORKER_URL").rstrip("/")
    token = required("OMR_WORKER_TOKEN")
    pomerium_jwt = required("OMR_POMERIUM_JWT")
    max_runs = int(required("OMR_MAX_RUNS"))
    maximize = os.environ.get("OMR_MAXIMIZE", "0") == "1"
    candidate = Path(required("OMR_CANDIDATE"))
    research_path = Path(required("OMR_RESEARCH"))
    workspace = Path(required("OMR_WORKSPACE"))
    model = os.environ.get("OMR_CODEX_MODEL")
    proposal_turns = positive_environment("OMR_PROPOSAL_TURNS", 3)
    if not research_path.is_file():
        raise ValueError(f"research objective not found: {research_path}")

    files = read_candidate(candidate)
    prepare(
        workspace,
        files,
        research_path.read_text(),
        os.environ.get("OMR_MEMORY", ""),
    )
    state = Research(files, maximize)
    health = request(worker, "/healthz", pomerium_jwt=pomerium_jwt)
    evaluators = health.get("evaluators")
    if not isinstance(evaluators, list) or CODE_EVALUATOR not in evaluators:
        raise RuntimeError("worker does not support code evaluation")
    if health.get("device") != "cuda" and os.environ.get("OMR_ALLOW_CPU") != "1":
        raise RuntimeError("Akash worker has no CUDA device")
    compute = health.get("gpu") or health.get("device") or "unknown"
    bid = os.environ.get("OMR_BID_UACT")
    provider = f"Akash · {compute} · Codex" + (f" · {bid} uact/block" if bid else "")
    emit({"type": "campaign.started", "provider": provider})

    for run in range(1, max_runs + 1):
        if run == 1:
            files = state.best_files
            hypothesis = "establish the unmodified code baseline"
        else:
            hypothesis, files = propose(workspace, state, model, proposal_turns)
        candidate_value, candidate_sha256 = identify_code_candidate({"files": files})
        emit(
            {
                "type": "experiment.started",
                "run": run,
                "hypothesis": hypothesis,
                "candidate": candidate_value,
                "evaluator": CODE_EVALUATOR,
            }
        )
        result = request(
            worker,
            "/v1/code-experiments",
            candidate_value,
            token,
            pomerium_jwt,
        )
        if text(result, "candidate_sha256") != candidate_sha256:
            raise RuntimeError("worker measured a different candidate")
        if text(result, "evaluator") != CODE_EVALUATOR:
            raise RuntimeError("worker used a different evaluator")
        metric = optional_number(result, "metric")
        seconds = number(result, "seconds")
        error = result.get("error")
        if error is not None and not isinstance(error, str):
            raise RuntimeError("worker returned invalid error")
        state.observe(files, hypothesis, metric, error)
        persist(workspace, state)
        emit(
            {
                "type": "experiment.finished",
                "run": run,
                "metric": metric,
                "seconds": seconds,
                "cost_usd": 0.0,
                "candidate_sha256": candidate_sha256,
                "evaluator": CODE_EVALUATOR,
            }
        )
    emit({"type": "campaign.finished"})
    return 0


def read_candidate(path: Path) -> dict[str, str]:
    if path.is_file():
        files = {"train.py": path.read_text()}
    elif path.is_dir():
        files = {}
        for source in sorted(path.rglob("*.py")):
            if source.is_symlink() or any(
                part.startswith(".") for part in source.relative_to(path).parts
            ):
                continue
            files[source.relative_to(path).as_posix()] = source.read_text()
    else:
        raise ValueError(f"baseline candidate not found: {path}")
    normalized, _ = identify_code_candidate({"files": files})
    return normalized["files"]


def write_candidate(path: Path, files: dict[str, str]) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    for name, source in files.items():
        destination = path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source)


def prepare(
    workspace: Path,
    files: dict[str, str],
    objective: str,
    memory: str = "",
) -> None:
    if workspace.exists():
        raise ValueError(f"campaign workspace already exists: {workspace}")
    workspace.mkdir(parents=True)
    write_candidate(workspace / "candidate", files)
    (workspace / "research.md").write_text(objective)
    (workspace / "memory.md").write_text(memory)
    (workspace / "contract.md").write_text(CONTRACT)
    (workspace / "history.jsonl").write_text("")
    (workspace / "turns.jsonl").write_text("")
    (workspace / "proposal.schema.json").write_text(json.dumps(SCHEMA, indent=2) + "\n")


def propose(
    workspace: Path,
    state: Research,
    model: str | None = None,
    max_turns: int = 3,
) -> tuple[str, dict[str, str]]:
    persist(workspace, state)
    turns: list[dict[str, Any]] = []
    for turn in range(1, max_turns + 1):
        (workspace / "turns.jsonl").write_text(
            "".join(json.dumps(item, separators=(",", ":")) + "\n" for item in turns)
        )
        proposal = codex_turn(workspace, model)
        files = read_candidate(workspace / "candidate")
        turns.append({"turn": turn, **proposal})
        if proposal["ready"]:
            if files == state.best_files:
                raise RuntimeError("Codex marked an unchanged candidate ready")
            return str(proposal["hypothesis"]), files
    raise RuntimeError(f"Codex did not mark the candidate ready in {max_turns} turns")


def codex_turn(workspace: Path, model: str | None) -> dict[str, Any]:
    result_path = workspace / "proposal.json"
    result_path.unlink(missing_ok=True)
    protected = {
        path: path.read_bytes()
        for path in workspace.iterdir()
        if path.is_file() and path.name != "proposal.json"
    }
    command = [
        codex_command(),
        "exec",
        "--ephemeral",
        "--sandbox",
        "workspace-write",
        "--skip-git-repo-check",
        "--output-schema",
        str(workspace / "proposal.schema.json"),
        "--output-last-message",
        str(result_path),
        "--cd",
        str(workspace),
    ]
    if model:
        command.extend(("--model", model))
    command.append(PROMPT)
    try:
        completed = subprocess.run(
            command,
            env=codex_environment(),
            stdout=subprocess.DEVNULL,
            check=False,
            timeout=codex_timeout(),
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Codex proposal timed out") from error
    if completed.returncode:
        raise RuntimeError(f"Codex exited with status {completed.returncode}")
    for path, contents in protected.items():
        if not path.is_file() or path.read_bytes() != contents:
            raise RuntimeError(f"Codex changed protected file {path.name}")
    unexpected = sorted(
        path.name for path in workspace.iterdir() if path.name not in CONTROL_FILES
    )
    if unexpected:
        raise RuntimeError(f"Codex created unexpected files: {', '.join(unexpected)}")
    try:
        value = json.loads(result_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Codex returned invalid proposal JSON") from error
    if not isinstance(value, dict) or not isinstance(value.get("ready"), bool):
        raise RuntimeError("Codex proposal must contain boolean ready")
    text(value, "hypothesis")
    text(value, "summary")
    return value


def persist(workspace: Path, state: Research) -> None:
    write_candidate(workspace / "candidate", state.best_files)
    history = "".join(
        json.dumps(item, separators=(",", ":")) + "\n" for item in state.history
    )
    (workspace / "history.jsonl").write_text(history)


def codex_environment() -> dict[str, str]:
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("OMR_")
        and name not in {"AKASH_API_KEY", "CODEX_API_KEY", "OPENAI_API_KEY"}
    }
    api_key = secret("CODEX_API_KEY")
    if api_key:
        environment["CODEX_API_KEY"] = api_key
    return environment


def codex_command() -> str:
    command = shutil.which("codex")
    if not command:
        raise RuntimeError("Codex CLI is not installed")
    return command


def codex_timeout() -> float:
    value = float(os.environ.get("OMR_CODEX_TIMEOUT", "300"))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("OMR_CODEX_TIMEOUT must be positive")
    return value


def positive_environment(name: str, default: int) -> int:
    value = int(os.environ.get(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


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


def optional_number(value: dict[str, Any], name: str) -> float | None:
    return None if value.get(name) is None else number(value, name)


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
