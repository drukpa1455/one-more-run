"""Deterministic adapter used to exercise the CLI without a GPU."""

import json
import os
import time


HYPOTHESES = [
    ("baseline", 1.0412),
    ("increase learning rate", 1.0298),
    ("replace activation with GELU", 1.0341),
    ("tie input and output embeddings", 1.0217),
    ("deepen the model", 1.0264),
    ("reduce weight decay", 1.0189),
]


def emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


emit({"type": "campaign.started", "provider": "local demo"})
for run, (hypothesis, metric) in enumerate(HYPOTHESES[: int(os.environ["OMR_MAX_RUNS"])], start=1):
    emit({"type": "experiment.started", "run": run, "hypothesis": hypothesis})
    time.sleep(0.2)
    emit({"type": "experiment.progress", "run": run, "metric": metric + 0.08})
    time.sleep(0.2)
    emit(
        {
            "type": "experiment.finished",
            "run": run,
            "metric": metric,
            "seconds": 300.0,
            "cost_usd": 0.17,
        }
    )
emit({"type": "campaign.finished"})
