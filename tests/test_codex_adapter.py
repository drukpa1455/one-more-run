import io
import json

from one_more_run import codex_adapter
from one_more_run.codex_adapter import Research


def test_research_keeps_only_measured_code_improvements():
    baseline = {"train.py": "baseline"}
    worse = {"train.py": "worse"}
    broken = {"train.py": "broken"}
    better = {"train.py": "better"}
    state = Research(baseline)

    assert state.observe(baseline, "baseline", 1.0, None) == "keep"
    assert state.observe(worse, "try worse", 1.1, None) == "reject"
    assert state.observe(broken, "try broken", None, "crash") == "crash"
    assert state.observe(better, "try better", 0.9, None) == "keep"
    assert state.best_files == better
    assert state.best_metric == 0.9


def test_codex_environment_excludes_compute_credentials(tmp_path, monkeypatch):
    credentials = tmp_path / "credentials.json"
    credentials.write_text('{"CODEX_API_KEY":"codex-secret"}\n')
    credentials.chmod(0o600)
    monkeypatch.setenv("OMR_CREDENTIALS", str(credentials))
    monkeypatch.setenv("OMR_WORKER_TOKEN", "worker-secret")
    monkeypatch.setenv("AKASH_API_KEY", "akash-secret")

    environment = codex_adapter.codex_environment()

    assert environment["CODEX_API_KEY"] == "codex-secret"
    assert "OMR_WORKER_TOKEN" not in environment
    assert "AKASH_API_KEY" not in environment


def test_proposal_can_take_multiple_turns_and_create_modules(tmp_path, monkeypatch):
    workspace = tmp_path / "campaign"
    baseline = {"train.py": "baseline\n"}
    codex_adapter.prepare(workspace, baseline, "objective\n")
    state = Research(baseline, best_metric=1.0)
    state.history.append({"run": 1, "metric": 1.0, "decision": "keep"})
    monkeypatch.setattr(codex_adapter, "codex_command", lambda: "codex")
    monkeypatch.setattr(codex_adapter, "codex_environment", lambda: {})

    calls = 0

    def run(command, **kwargs):
        nonlocal calls
        calls += 1
        (workspace / "candidate" / "model.py").write_text("class Model: pass\n")
        if calls == 2:
            (workspace / "candidate" / "train.py").write_text("improved\n")
        output = command[command.index("--output-last-message") + 1]
        with open(output, "w") as result:
            json.dump(
                {
                    "hypothesis": "use a modular nonlinear model",
                    "summary": "split the model from training",
                    "ready": calls == 2,
                },
                result,
            )
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(codex_adapter.subprocess, "run", run)

    hypothesis, files = codex_adapter.propose(workspace, state)

    assert calls == 2
    assert hypothesis == "use a modular nonlinear model"
    assert files == {
        "model.py": "class Model: pass\n",
        "train.py": "improved\n",
    }


def test_pomerium_identity_is_forwarded_to_code_evaluation(monkeypatch):
    calls = []

    def urlopen(request, timeout):
        calls.append(request)
        return io.BytesIO(b'{"metric":0.5}')

    monkeypatch.setattr(codex_adapter.urllib.request, "urlopen", urlopen)

    codex_adapter.request(
        "https://worker.example",
        "/v1/code-experiments",
        {"files": {"train.py": "pass"}},
        "worker-token",
        "pomerium-jwt",
    )

    request = calls[0]
    assert request.get_header("Authorization") == "Bearer worker-token"
    assert request.get_header("X-pomerium-authorization") == "pomerium-jwt"
