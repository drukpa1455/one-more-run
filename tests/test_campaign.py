import json
from dataclasses import asdict

import pytest

from one_more_run import cli
from one_more_run.cli import (
    Campaign,
    Experiment,
    ExperimentPlan,
    ProtocolError,
    format_metric,
    load,
    split_adapter,
)
from one_more_run.protocol import identify_candidate


CANDIDATE = {"learning_rate": 0.1, "momentum": 0.0, "steps": 80}
EVALUATOR = "test.v1"


def start(run: int) -> dict:
    return {
        "type": "experiment.started",
        "run": run,
        "hypothesis": f"idea {run}",
        "candidate": {**CANDIDATE, "run": run},
        "evaluator": EVALUATOR,
    }


def finish(run: int, metric: float) -> dict:
    _, candidate_sha256 = identify_candidate({**CANDIDATE, "run": run})
    return {
        "type": "experiment.finished",
        "run": run,
        "metric": metric,
        "seconds": 1,
        "candidate_sha256": candidate_sha256,
        "evaluator": EVALUATOR,
    }


def test_campaign_keeps_only_improvements():
    campaign = Campaign("lower is better")
    campaign.apply({"type": "campaign.started", "provider": "test"})

    decisions = []
    for run, metric in enumerate((1.0, 1.1, 0.9), start=1):
        campaign.apply(start(run))
        result = campaign.apply(finish(run, metric))
        decisions.append(result.decision)

    assert decisions == ["keep", "reject", "keep"]
    assert campaign.best.metric == 0.9


def test_campaign_rejects_out_of_order_events():
    campaign = Campaign("goal")

    with pytest.raises(ProtocolError, match="current run"):
        campaign.apply({"type": "experiment.progress", "run": 1, "metric": 1.0})


def test_campaign_requires_sequential_runs():
    campaign = Campaign("goal")
    campaign.apply({"type": "campaign.started", "provider": "test"})

    with pytest.raises(ProtocolError, match="expected run 1"):
        campaign.apply(start(2))


def test_campaign_rejects_a_mismatched_receipt():
    campaign = Campaign("goal")
    campaign.apply({"type": "campaign.started", "provider": "test"})
    campaign.apply(start(1))

    receipt = finish(1, 1.0)
    receipt["candidate_sha256"] = "0" * 64
    with pytest.raises(ProtocolError, match="different candidate"):
        campaign.apply(receipt)


def test_load_replays_ledger(tmp_path):
    candidate, candidate_sha256 = identify_candidate(CANDIDATE)
    plan = ExperimentPlan(1, "baseline", candidate, candidate_sha256, EVALUATOR)
    record = Experiment(plan, 1.0, "keep", 3.0, 0.1, "test")
    ledger = tmp_path / "experiments.jsonl"
    ledger.write_text(json.dumps(asdict(record)) + "\n")

    assert load(ledger) == [record]


def test_load_rejects_a_candidate_changed_after_measurement(tmp_path):
    candidate, candidate_sha256 = identify_candidate(CANDIDATE)
    plan = ExperimentPlan(1, "baseline", candidate, candidate_sha256, EVALUATOR)
    record = asdict(Experiment(plan, 1.0, "keep", 3.0, 0.1, "test"))
    record["plan"]["candidate"]["steps"] = 81
    ledger = tmp_path / "experiments.jsonl"
    ledger.write_text(json.dumps(record) + "\n")

    with pytest.raises(ProtocolError, match="invalid ledger record"):
        load(ledger)


def test_split_adapter_keeps_run_options():
    arguments = ["run", "research.md", "--plain", "--", "python", "adapter.py"]

    assert split_adapter(arguments) == ["python", "adapter.py"]
    assert arguments == ["run", "research.md", "--plain"]


def test_small_metrics_remain_visible():
    assert format_metric(7.155e-8) == "7.155e-08"


def test_doctor_checks_pomerium_only_when_requested(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setenv("CODEX_API_KEY", "codex-secret")
    monkeypatch.setenv("AKASH_API_KEY", "akash-secret")

    assert cli.doctor() == 0
    assert cli.doctor(pomerium=True) == 1

    for name in (
        "POMERIUM_ZERO_TOKEN",
        "POMERIUM_ZERO_API_TOKEN",
        "POMERIUM_ROUTE_URL",
        "POMERIUM_SERVICE_ACCOUNT_JWT",
    ):
        monkeypatch.setenv(name, "configured")

    assert cli.doctor(pomerium=True) == 0
