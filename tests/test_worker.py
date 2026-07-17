import pytest

from one_more_run.protocol import identify_candidate
from one_more_run.worker import EVALUATOR, run_experiment, run_python, validate


def test_python_evaluator_is_deterministic():
    first = run_python(learning_rate=0.05, momentum=0.8, steps=40)
    second = run_python(learning_rate=0.05, momentum=0.8, steps=40)

    assert first["metric"] == second["metric"]
    assert first["device"] == "cpu"


def test_candidate_is_bounded():
    with pytest.raises(ValueError, match="steps"):
        validate({"learning_rate": 0.1, "momentum": 0.0, "steps": 501})

    with pytest.raises(ValueError, match="unknown candidate fields"):
        validate(
            {
                "learning_rate": 0.1,
                "momentum": 0.0,
                "steps": 80,
                "command": "nvidia-smi",
            }
        )


def test_worker_receipt_identifies_the_candidate_and_evaluator():
    candidate = {"learning_rate": 0.05, "momentum": 0.8, "steps": 40}
    _, candidate_sha256 = identify_candidate(candidate)

    result = run_experiment(candidate)

    assert result["candidate_sha256"] == candidate_sha256
    assert result["evaluator"] == EVALUATOR
