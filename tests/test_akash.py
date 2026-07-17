import argparse
import io
import json
import time
from decimal import Decimal

import pytest

from one_more_run import akash
from one_more_run.akash import Bid, ConsoleAPI, Deployment, PomeriumRoute
from one_more_run.pomerium import Cluster
from one_more_run.protocol import CODE_EVALUATOR


class FakeConsole:
    def __init__(self):
        self.closed = []
        self.leased = []

    def create(self, sdl, deposit):
        assert sdl == "rendered sdl"
        assert deposit == 0.5
        return Deployment("123", "manifest")

    def bids(self, dseq):
        assert dseq == "123"
        return [
            Bid("123", 1, 1, "expensive", Decimal("1001"), "uact", "open"),
            Bid("123", 1, 1, "closed", Decimal("1"), "uact", "closed"),
            Bid("123", 1, 1, "provider", Decimal("90"), "uact", "open"),
        ]

    def lease(self, deployment, bid):
        self.leased.append((deployment, bid))

    def deployment(self, dseq):
        return {
            "leases": [
                {
                    "id": {
                        "dseq": dseq,
                        "gseq": 1,
                        "oseq": 1,
                        "provider": "provider",
                    },
                    "state": "active",
                    "status": {
                        "services": {
                            "worker": {"uris": ["worker.example"]},
                        }
                    },
                }
            ]
        }

    def close(self, dseq):
        self.closed.append(dseq)


class FakeZero:
    def __init__(self):
        self.pointed = []
        self.restored = []

    def point_cluster(self, cluster, ip):
        self.pointed.append((cluster, ip))

    def restore_cluster(self, cluster, ip, deadline=None):
        self.restored.append((cluster, ip))


def arguments():
    return argparse.Namespace(
        deposit=0.5,
        max_bid=1000.0,
        timeout=60.0,
    )


def test_spend_requires_explicit_authorization(tmp_path):
    args = arguments()
    args.yes = False
    args.research = tmp_path / "missing.md"
    args.ledger = tmp_path / "ledger.jsonl"
    args.sdl = tmp_path / "missing.yaml"

    with pytest.raises(akash.AkashError, match="pass --yes"):
        akash.run(args, lambda _: 0)


def test_local_inputs_are_checked_before_deployment(tmp_path, monkeypatch):
    args = arguments()
    args.yes = True
    args.research = tmp_path / "missing.md"
    args.ledger = tmp_path / "ledger.jsonl"
    args.sdl = tmp_path / "missing.yaml"
    monkeypatch.setenv("AKASH_API_KEY", "unused")
    monkeypatch.setattr(
        akash,
        "ConsoleAPI",
        lambda *args, **kwargs: pytest.fail("deployment client was constructed"),
    )

    with pytest.raises(akash.AkashError, match="research objective not found"):
        akash.run(args, lambda _: 0)


def test_orchestrate_runs_with_bounded_bid_and_closes(monkeypatch):
    client = FakeConsole()
    monkeypatch.setattr(
        akash,
        "worker_health",
        lambda uri, deadline: {"evaluator": akash.EVALUATOR, "device": "cuda"},
    )

    def campaign(args):
        assert args.environment == {
            "OMR_WORKER_URL": "https://worker.example",
            "OMR_WORKER_TOKEN": "worker-token",
            "OMR_BID_UACT": "90",
        }
        assert args.drop_environment == ["AKASH_API_KEY", *akash.POMERIUM_ENVIRONMENT]
        return 0

    result = akash.orchestrate(
        client,
        arguments(),
        campaign,
        "rendered sdl",
        "worker-token",
        time.monotonic() + 60,
    )

    assert result == 0
    assert client.leased[0][1].provider == "provider"
    assert client.closed == ["123"]


def test_pomerium_is_an_optional_worker_boundary(monkeypatch):
    client = FakeConsole()
    zero = FakeZero()
    cluster = Cluster("org", "cluster", "namespace", "hackathon", "example.com", None)
    route = PomeriumRoute(
        zero=zero,
        cluster=cluster,
        url="https://worker.example.com",
        jwt="service-account-jwt",
        zero_token="zero-token",
    )
    monkeypatch.setattr(akash, "wait_for_pomerium_ip", lambda *args: "203.0.113.8")
    monkeypatch.setattr(
        akash,
        "worker_health",
        lambda uri, deadline, jwt: {
            "evaluator": akash.EVALUATOR,
            "device": "cuda",
        },
    )

    def campaign(args):
        assert args.environment["OMR_WORKER_URL"] == route.url
        assert args.environment["OMR_POMERIUM_JWT"] == route.jwt
        return 0

    result = akash.orchestrate(
        client,
        arguments(),
        campaign,
        "rendered sdl",
        "worker-token",
        time.monotonic() + 60,
        route,
    )

    assert result == 0
    assert zero.pointed == [(cluster, "203.0.113.8")]
    assert zero.restored == [(cluster, "203.0.113.8")]


def test_orchestrate_closes_when_campaign_fails(monkeypatch):
    client = FakeConsole()
    monkeypatch.setattr(
        akash,
        "worker_health",
        lambda uri, deadline: {"evaluator": akash.EVALUATOR, "device": "cuda"},
    )

    with pytest.raises(RuntimeError, match="campaign failed"):
        akash.orchestrate(
            client,
            arguments(),
            lambda args: (_ for _ in ()).throw(RuntimeError("campaign failed")),
            "rendered sdl",
            "worker-token",
            time.monotonic() + 60,
        )

    assert client.closed == ["123"]


def test_orchestrate_selects_the_code_research_adapter(monkeypatch):
    client = FakeConsole()
    args = arguments()
    args.evaluator = CODE_EVALUATOR
    args.adapter_module = "one_more_run.codex_adapter"
    args.adapter_environment = {"OMR_CANDIDATE": "/candidate.py"}
    monkeypatch.setattr(
        akash,
        "worker_health",
        lambda uri, deadline: {
            "evaluator": akash.EVALUATOR,
            "evaluators": [akash.EVALUATOR, CODE_EVALUATOR],
            "device": "cuda",
        },
    )

    def campaign(campaign_args):
        assert campaign_args.adapter[-1] == "one_more_run.codex_adapter"
        assert campaign_args.environment["OMR_CANDIDATE"] == "/candidate.py"
        return 0

    assert (
        akash.orchestrate(
            client,
            args,
            campaign,
            "rendered sdl",
            "worker-token",
            time.monotonic() + 60,
        )
        == 0
    )
    assert client.closed == ["123"]


def test_worker_token_is_injected_without_changing_the_source_file():
    sdl = """version: \"2.0\"
services:
  worker:
    image: example/image@sha256:abc
    expose: []
"""

    rendered = akash.inject_worker_token(sdl, "generated-token")

    assert "      - OMR_WORKER_TOKEN=generated-token\n" in rendered
    assert "OMR_WORKER_TOKEN" not in sdl


def test_pomerium_manifest_receives_only_runtime_secrets():
    sdl = """services:
  worker:
    image: worker
  pomerium:
    image: pomerium
"""

    rendered = akash.inject_pomerium_secrets(sdl, "worker-token", "zero-token")

    assert "      - OMR_WORKER_TOKEN=worker-token\n" in rendered
    assert "      - POMERIUM_ZERO_TOKEN=zero-token\n" in rendered
    assert "POMERIUM_SERVICE_ACCOUNT_JWT" not in rendered


def test_worker_token_injection_rejects_an_existing_environment():
    sdl = """services:
  worker:
    image: example/image
    env:
      - EXISTING=value
profiles: {}
"""

    with pytest.raises(akash.AkashError, match="must be owned"):
        akash.inject_worker_token(sdl, "generated-token")


def test_console_create_uses_the_managed_wallet_contract(monkeypatch):
    response = io.BytesIO(b'{"data":{"dseq":"123","manifest":"rendered"}}')
    calls = []

    def urlopen(request, timeout):
        calls.append((request, timeout))
        return response

    monkeypatch.setattr(akash.urllib.request, "urlopen", urlopen)
    client = ConsoleAPI("console-secret", "https://console.example")

    deployment = client.create("sdl", 0.5)

    request, timeout = calls[0]
    assert deployment == Deployment("123", "rendered")
    assert request.full_url == "https://console.example/v1/deployments"
    assert request.method == "POST"
    assert request.get_header("X-api-key") == "console-secret"
    assert json.loads(request.data) == {"data": {"sdl": "sdl", "deposit": 0.5}}
    assert timeout == 30.0


def test_console_lease_and_close_use_the_managed_wallet_contract(monkeypatch):
    responses = iter(
        [
            io.BytesIO(b'{"data":{"leases":[]}}'),
            io.BytesIO(b'{"data":{"success":true}}'),
        ]
    )
    calls = []

    def urlopen(request, timeout):
        calls.append((request, timeout))
        return next(responses)

    monkeypatch.setattr(akash.urllib.request, "urlopen", urlopen)
    client = ConsoleAPI("console-secret", "https://console.example")
    deployment = Deployment("123", "manifest")
    bid = Bid("123", 2, 3, "provider", Decimal("90"), "uact", "open")

    client.lease(deployment, bid)
    client.close("123")

    lease, lease_timeout = calls[0]
    assert lease.full_url == "https://console.example/v1/leases"
    assert lease.method == "POST"
    assert json.loads(lease.data) == {
        "manifest": "manifest",
        "leases": [
            {
                "dseq": "123",
                "gseq": 2,
                "oseq": 3,
                "provider": "provider",
            }
        ],
    }
    assert lease_timeout == 30.0

    close, close_timeout = calls[1]
    assert close.full_url == "https://console.example/v1/deployments/123"
    assert close.method == "DELETE"
    assert close.data is None
    assert close_timeout == 30
