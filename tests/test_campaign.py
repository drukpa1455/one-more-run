import json

import pytest

from one_more_run.cli import Campaign, Experiment, ProtocolError, load, split_adapter


def test_campaign_keeps_only_improvements():
    campaign = Campaign("lower is better")
    campaign.apply({"type": "campaign.started", "provider": "test"})

    decisions = []
    for run, metric in enumerate((1.0, 1.1, 0.9), start=1):
        campaign.apply({"type": "experiment.started", "run": run, "hypothesis": f"idea {run}"})
        result = campaign.apply(
            {"type": "experiment.finished", "run": run, "metric": metric, "seconds": 1}
        )
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
        campaign.apply({"type": "experiment.started", "run": 2, "hypothesis": "skip"})


def test_load_replays_ledger(tmp_path):
    record = Experiment(1, "baseline", 1.0, "keep", 3.0, 0.1, "test")
    ledger = tmp_path / "experiments.jsonl"
    ledger.write_text(json.dumps(record.__dict__) + "\n")

    assert load(ledger) == [record]


def test_split_adapter_keeps_run_options():
    arguments = ["run", "research.md", "--plain", "--", "python", "adapter.py"]

    assert split_adapter(arguments) == ["python", "adapter.py"]
    assert arguments == ["run", "research.md", "--plain"]
