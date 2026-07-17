import argparse
import io
import json
import time
from decimal import Decimal

import pytest

from one_more_run import akash
from one_more_run.akash import Bid, ConsoleAPI, Deployment
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
                        "ips": {
                            "pomerium": [
                                {
                                    "IP": "203.0.113.8",
                                    "Port": 443,
                                    "ExternalPort": 30443,
                                    "Protocol": "TCP",
                                }
                            ]
                        },
                        "services": {},
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


CLUSTER = Cluster(
    organization_id="org-1",
    id="cluster-1",
    namespace_id="namespace-1",
    name="hackathon",
    fqdn="swift-fox-1234.pomerium.app",
    override_ip="192.0.2.1",
)


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


def test_pomerium_credentials_are_checked_before_deployment(tmp_path, monkeypatch):
    args = arguments()
    args.yes = True
    args.research = tmp_path / "research.md"
    args.research.write_text("objective")
    args.ledger = tmp_path / "ledger.jsonl"
    args.sdl = tmp_path / "akash.yaml"
    args.sdl.write_text('version: "2.0"')
    monkeypatch.setenv("AKASH_API_KEY", "unused")
    for name in akash.POMERIUM_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        akash,
        "ConsoleAPI",
        lambda *args, **kwargs: pytest.fail("deployment client was constructed"),
    )

    with pytest.raises(akash.AkashError, match="set POMERIUM_ZERO_TOKEN"):
        akash.run(args, lambda _: 0)


def test_orchestrate_runs_with_bounded_bid_and_closes(monkeypatch):
    client = FakeConsole()
    zero = FakeZero()
    monkeypatch.setattr(
        akash,
        "worker_health",
        lambda uri, jwt, deadline: {
            "evaluator": akash.EVALUATOR,
            "device": "cuda",
        },
    )

    def campaign(args):
        assert args.environment == {
            "OMR_WORKER_URL": "https://worker.swift-fox-1234.pomerium.app",
            "OMR_WORKER_TOKEN": "worker-token",
            "OMR_POMERIUM_JWT": "service-account-jwt",
            "OMR_BID_UACT": "90",
        }
        assert args.drop_environment == [
            "AKASH_API_KEY",
            *akash.POMERIUM_ENVIRONMENT,
        ]
        return 0

    result = akash.orchestrate(
        client,
        zero,
        CLUSTER,
        arguments(),
        campaign,
        "rendered sdl",
        "https://worker.swift-fox-1234.pomerium.app",
        "worker-token",
        "service-account-jwt",
        time.monotonic() + 60,
    )

    assert result == 0
    assert client.leased[0][1].provider == "provider"
    assert client.closed == ["123"]
    assert zero.pointed == [(CLUSTER, "203.0.113.8")]
    assert zero.restored == [(CLUSTER, "203.0.113.8")]


def test_orchestrate_closes_when_campaign_fails(monkeypatch):
    client = FakeConsole()
    zero = FakeZero()
    monkeypatch.setattr(
        akash,
        "worker_health",
        lambda uri, jwt, deadline: {
            "evaluator": akash.EVALUATOR,
            "device": "cuda",
        },
    )

    with pytest.raises(RuntimeError, match="campaign failed"):
        akash.orchestrate(
            client,
            zero,
            CLUSTER,
            arguments(),
            lambda args: (_ for _ in ()).throw(RuntimeError("campaign failed")),
            "rendered sdl",
            "https://worker.swift-fox-1234.pomerium.app",
            "worker-token",
            "service-account-jwt",
            time.monotonic() + 60,
        )

    assert client.closed == ["123"]
    assert zero.restored == [(CLUSTER, "203.0.113.8")]


def test_orchestrate_selects_the_code_research_adapter(monkeypatch):
    client = FakeConsole()
    zero = FakeZero()
    args = arguments()
    args.evaluator = CODE_EVALUATOR
    args.adapter_module = "one_more_run.codex_adapter"
    args.adapter_environment = {"OMR_CANDIDATE": "/candidate.py"}
    monkeypatch.setattr(
        akash,
        "worker_health",
        lambda uri, jwt, deadline: {
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
            zero,
            CLUSTER,
            args,
            campaign,
            "rendered sdl",
            "https://worker.swift-fox-1234.pomerium.app",
            "worker-token",
            "service-account-jwt",
            time.monotonic() + 60,
        )
        == 0
    )
    assert client.closed == ["123"]
    assert zero.restored == [(CLUSTER, "203.0.113.8")]


def test_runtime_secrets_are_injected_without_changing_the_source_file():
    sdl = """version: \"2.0\"
services:
  worker:
    image: example/image@sha256:abc
    expose: []
  pomerium:
    image: pomerium/pomerium@sha256:def
    expose: []
"""

    rendered = akash.inject_secrets(sdl, "generated-token", "zero-token")

    assert "      - OMR_WORKER_TOKEN=generated-token\n" in rendered
    assert "      - POMERIUM_ZERO_TOKEN=zero-token\n" in rendered
    assert "      - TMPDIR=/tmp/pomerium\n" in rendered
    assert "      - XDG_CACHE_HOME=/tmp/pomerium/cache\n" in rendered
    assert "      - XDG_DATA_HOME=/tmp/pomerium/cache\n" in rendered
    assert "OMR_WORKER_TOKEN" not in sdl
    assert "POMERIUM_ZERO_TOKEN" not in sdl


def test_worker_token_injection_rejects_an_existing_environment():
    sdl = """services:
  worker:
    image: example/image
    env:
      - EXISTING=value
  pomerium:
    image: pomerium/pomerium
profiles: {}
"""

    with pytest.raises(akash.AkashError, match="must be owned"):
        akash.inject_secrets(sdl, "generated-token", "zero-token")


def test_worker_health_authenticates_to_pomerium(monkeypatch):
    response = io.BytesIO(
        json.dumps({"evaluator": akash.EVALUATOR, "device": "cuda"}).encode()
    )
    calls = []

    def urlopen(request, timeout):
        calls.append((request, timeout))
        return response

    monkeypatch.setattr(akash.urllib.request, "urlopen", urlopen)

    health = akash.worker_health(
        "https://worker.example",
        "service-account-jwt",
        time.monotonic() + 60,
    )

    request, timeout = calls[0]
    assert health == {"evaluator": akash.EVALUATOR, "device": "cuda"}
    assert request.full_url == "https://worker.example/healthz"
    assert request.get_header("X-pomerium-authorization") == "service-account-jwt"
    assert 0 < timeout <= 10


def test_pomerium_ip_reads_the_dedicated_endpoint():
    client = FakeConsole()
    bid = Bid("123", 1, 1, "provider", Decimal("90"), "uact", "open")

    assert akash.pomerium_ip(client.deployment("123"), bid) == "203.0.113.8"


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
