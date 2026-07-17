import pytest

from one_more_run.worker import run_python, validate


def test_python_evaluator_is_deterministic():
    first = run_python(learning_rate=0.05, momentum=0.8, steps=40)
    second = run_python(learning_rate=0.05, momentum=0.8, steps=40)

    assert first["metric"] == second["metric"]
    assert first["device"] == "cpu"


def test_candidate_is_bounded():
    with pytest.raises(ValueError, match="steps"):
        validate({"learning_rate": 0.1, "steps": 501})

    with pytest.raises(ValueError, match="unknown candidate fields"):
        validate({"learning_rate": 0.1, "command": "nvidia-smi"})
