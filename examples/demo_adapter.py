"""Run the adaptive search against the fixed evaluator in this process."""

import json
import os
import sys

from one_more_run.akash_adapter import CoordinateSearch
from one_more_run.protocol import identify_candidate
from one_more_run.worker import EVALUATOR, device_info, run_experiment


def emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


device = device_info()
provider = f"local · {device['gpu'] or device['device']}"
memory = os.environ.get("OMR_MEMORY", "").strip()
if memory:
    print(f"recalled research memory:\n{memory}", file=sys.stderr, flush=True)
emit({"type": "campaign.started", "provider": provider})
search = CoordinateSearch(os.environ.get("OMR_MAXIMIZE", "0") == "1")
for run in range(1, int(os.environ["OMR_MAX_RUNS"]) + 1):
    hypothesis, candidate = search.propose()
    _, candidate_sha256 = identify_candidate(candidate)
    emit(
        {
            "type": "experiment.started",
            "run": run,
            "hypothesis": hypothesis,
            "candidate": candidate,
            "evaluator": EVALUATOR,
        }
    )
    result = run_experiment(candidate)
    assert result["candidate_sha256"] == candidate_sha256
    assert result["evaluator"] == EVALUATOR
    search.observe(result["metric"])
    emit(
        {
            "type": "experiment.finished",
            "run": run,
            "metric": result["metric"],
            "seconds": result["seconds"],
            "cost_usd": 0.0,
            "candidate_sha256": result["candidate_sha256"],
            "evaluator": result["evaluator"],
        }
    )
emit({"type": "campaign.finished"})
