import io
import json
import time

import pytest

from one_more_run import pomerium
from one_more_run.pomerium import Cluster, PomeriumError, ZeroAPI


def response(value):
    return io.BytesIO(json.dumps(value).encode())


def test_zero_api_finds_route_cluster_and_moves_then_restores_it(monkeypatch):
    responses = iter(
        [
            response({"idToken": "short-lived-id-token"}),
            response([{"id": "org-1"}]),
            response(
                [
                    {
                        "id": "cluster-1",
                        "namespaceId": "namespace-1",
                        "name": "hackathon",
                        "fqdn": "swift-fox-1234.pomerium.app",
                        "manualOverrideIpAddress": "192.0.2.1",
                    }
                ]
            ),
            response(
                [
                    {
                        "namespaceId": "namespace-1",
                        "from": "https://worker.swift-fox-1234.pomerium.app",
                        "to": ["http://worker:8080"],
                        "policyIds": ["policy-1"],
                        "enforcedPolicyIds": [],
                    }
                ]
            ),
            response({}),
            response(
                {
                    "id": "cluster-1",
                    "namespaceId": "namespace-1",
                    "name": "hackathon",
                    "fqdn": "swift-fox-1234.pomerium.app",
                    "manualOverrideIpAddress": "203.0.113.8",
                }
            ),
            response({}),
        ]
    )
    calls = []

    def urlopen(request, timeout):
        calls.append((request, timeout))
        return next(responses)

    monkeypatch.setattr(pomerium.urllib.request, "urlopen", urlopen)
    api = ZeroAPI(
        "api-user-token", time.monotonic() + 60, "https://zero.example/api/v0"
    )

    cluster = api.cluster_for_route("https://worker.swift-fox-1234.pomerium.app")
    api.validate_route(cluster, "https://worker.swift-fox-1234.pomerium.app")
    api.point_cluster(cluster, "203.0.113.8")
    api.restore_cluster(cluster, "203.0.113.8")

    token_request, token_timeout = calls[0]
    assert token_request.full_url == "https://zero.example/api/v0/token"
    assert token_request.get_header("Authorization") is None
    assert json.loads(token_request.data) == {"refreshToken": "api-user-token"}
    assert 0 < token_timeout <= 30

    route_request = calls[3][0]
    assert route_request.full_url == (
        "https://zero.example/api/v0/organizations/org-1/routes?"
        "namespaceId=namespace-1&includeDescendants=false"
    )

    update_request = calls[4][0]
    assert update_request.method == "PUT"
    assert update_request.get_header("Authorization") == "Bearer short-lived-id-token"
    assert json.loads(update_request.data) == {
        "name": "hackathon",
        "manualOverrideIpAddress": "203.0.113.8",
    }

    restore_request = calls[6][0]
    assert json.loads(restore_request.data) == {
        "name": "hackathon",
        "manualOverrideIpAddress": "192.0.2.1",
    }


def test_zero_api_refuses_to_overwrite_a_concurrent_cluster_change(monkeypatch):
    responses = iter(
        [
            response({"idToken": "id-token"}),
            response(
                {
                    "id": "cluster-1",
                    "namespaceId": "namespace-1",
                    "name": "hackathon",
                    "fqdn": "swift-fox-1234.pomerium.app",
                    "manualOverrideIpAddress": "198.51.100.9",
                }
            ),
        ]
    )
    monkeypatch.setattr(
        pomerium.urllib.request,
        "urlopen",
        lambda request, timeout: next(responses),
    )
    api = ZeroAPI("api-user-token", time.monotonic() + 60)
    original = Cluster(
        organization_id="org-1",
        id="cluster-1",
        namespace_id="namespace-1",
        name="hackathon",
        fqdn="swift-fox-1234.pomerium.app",
        override_ip=None,
    )

    with pytest.raises(PomeriumError, match="changed during the campaign"):
        api.restore_cluster(original, "203.0.113.8")


@pytest.mark.parametrize(
    "value",
    [
        "http://worker.example.com",
        "https://worker.example.com/path",
        "https://worker.example.com?token=secret",
        "https://user@worker.example.com",
    ],
)
def test_route_url_must_be_a_bare_https_origin(value):
    with pytest.raises(PomeriumError, match="HTTPS origin"):
        pomerium.route_hostname(value)


def test_point_cluster_rejects_a_non_ipv4_endpoint(monkeypatch):
    monkeypatch.setattr(
        pomerium.urllib.request,
        "urlopen",
        lambda request, timeout: response({"idToken": "id-token"}),
    )
    api = ZeroAPI("api-user-token", time.monotonic() + 60)
    cluster = Cluster(
        "org-1", "cluster-1", "namespace-1", "hackathon", "example.com", None
    )

    with pytest.raises(PomeriumError, match="invalid Pomerium IP"):
        api.point_cluster(cluster, "not-an-ip")


def test_hosted_cluster_cannot_be_repointed():
    with pytest.raises(PomeriumError, match="standard Zero cluster"):
        pomerium.cluster_from_response(
            {
                "id": "cluster-1",
                "namespaceId": "namespace-1",
                "name": "hosted",
                "fqdn": "hosted.pomerium.app",
                "flavor": "hosted",
            },
            "org-1",
        )
