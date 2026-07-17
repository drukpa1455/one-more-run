import json

import pytest

from one_more_run import settings


def test_environment_overrides_saved_credential(tmp_path, monkeypatch):
    location = tmp_path / "credentials.json"
    settings.save({"AKASH_API_KEY": "saved"}, location)
    monkeypatch.setenv("OMR_CREDENTIALS", str(location))
    monkeypatch.setenv("AKASH_API_KEY", "process")

    assert settings.secret("AKASH_API_KEY") == "process"


def test_configure_imports_environment_with_private_permissions(tmp_path, monkeypatch):
    location = tmp_path / "credentials.json"
    monkeypatch.setenv("OMR_CREDENTIALS", str(location))
    monkeypatch.setenv("CODEX_API_KEY", "codex-secret")
    monkeypatch.setenv("AKASH_API_KEY", "akash-secret")

    assert settings.configure(from_environment=True) == location
    assert json.loads(location.read_text()) == {
        "AKASH_API_KEY": "akash-secret",
        "CODEX_API_KEY": "codex-secret",
    }
    assert location.stat().st_mode & 0o077 == 0


def test_load_rejects_public_credentials(tmp_path):
    if settings.os.name == "nt":
        pytest.skip("POSIX permission test")
    location = tmp_path / "credentials.json"
    location.write_text('{"AKASH_API_KEY":"secret"}\n')
    location.chmod(0o644)

    with pytest.raises(ValueError, match="group/world"):
        settings.load(location)
