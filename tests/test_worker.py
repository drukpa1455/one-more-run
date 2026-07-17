import pytest

from one_more_run.protocol import identify_candidate
from one_more_run import worker
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


def test_code_worker_binds_source_to_a_fixed_evaluator(monkeypatch):
    candidate = {"files": {"train.py": "def train(*args):\n    return args[-1]\n"}}
    _, candidate_sha256 = identify_candidate(candidate)
    monkeypatch.setattr(
        worker, "evaluate_code", lambda source: {"metric": 0.25, "seconds": 1.0}
    )

    result = worker.run_code_experiment(candidate)

    assert result == {
        "candidate_sha256": candidate_sha256,
        "evaluator": worker.CODE_EVALUATOR,
        "metric": 0.25,
        "seconds": 1.0,
    }


def test_code_worker_rejects_extra_files():
    with pytest.raises(ValueError, match="unsafe candidate path"):
        worker.validate_code(
            {"files": {"train.py": "pass", "../prepare.py": "changed"}}
        )


def test_code_worker_accepts_modular_candidates():
    candidate = {
        "files": {
            "train.py": "from model import Model\n",
            "model.py": "class Model: pass\n",
            "layers/block.py": "class Block: pass\n",
        }
    }

    assert worker.validate_code(candidate) == candidate["files"]


def test_evaluator_environment_excludes_controller_credentials(monkeypatch):
    monkeypatch.setenv("AKASH_API_KEY", "akash-secret")
    monkeypatch.setenv("CODEX_API_KEY", "codex-secret")
    monkeypatch.setenv("OMR_WORKER_TOKEN", "worker-secret")

    environment = worker.evaluator_environment()

    assert "AKASH_API_KEY" not in environment
    assert "CODEX_API_KEY" not in environment
    assert "OMR_WORKER_TOKEN" not in environment
