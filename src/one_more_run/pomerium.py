"""Pomerium Zero control-plane boundary for ephemeral Akash clusters."""

from __future__ import annotations

import ipaddress
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit


API_URL = "https://console.pomerium.app/api/v0"


class PomeriumError(ValueError):
    """Pomerium Zero could not be configured safely."""


@dataclass(frozen=True)
class Cluster:
    organization_id: str
    id: str
    namespace_id: str
    name: str
    fqdn: str
    override_ip: str | None


class ZeroAPI:
    def __init__(
        self,
        api_token: str,
        deadline: float,
        base_url: str = API_URL,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.deadline = deadline
        self.id_token = self.authenticate(api_token)

    def cluster_for_route(self, route_url: str) -> Cluster:
        hostname = route_hostname(route_url)
        matches = []
        for organization in objects(
            self.request("GET", "/organizations"), "organizations"
        ):
            organization_id = text(organization, "id")
            path = f"/organizations/{organization_id}/clusters"
            for value in objects(self.request("GET", path), "clusters"):
                cluster = cluster_from_response(value, organization_id)
                if hostname == cluster.fqdn or hostname.endswith("." + cluster.fqdn):
                    matches.append(cluster)
        if not matches:
            raise PomeriumError(
                f"no Pomerium Zero cluster owns route hostname {hostname}"
            )
        if len(matches) > 1:
            raise PomeriumError(
                f"multiple Pomerium Zero clusters own route hostname {hostname}"
            )
        return matches[0]

    def validate_route(self, cluster: Cluster, route_url: str) -> None:
        query = urlencode(
            {"namespaceId": cluster.namespace_id, "includeDescendants": "false"}
        )
        path = f"/organizations/{cluster.organization_id}/routes?{query}"
        expected_origin = route_origin(route_url)
        matches = [
            route
            for route in objects(self.request("GET", path), "routes")
            if route_origin(text(route, "from")) == expected_origin
        ]
        if not matches:
            raise PomeriumError(f"Pomerium Zero route is not configured: {route_url}")
        if len(matches) > 1:
            raise PomeriumError(f"Pomerium Zero route is ambiguous: {route_url}")

        route = matches[0]
        if text(route, "namespaceId") != cluster.namespace_id:
            raise PomeriumError(
                "Pomerium Zero route belongs to an unexpected namespace"
            )
        if route.get("to") != ["http://worker:8080"]:
            raise PomeriumError(
                "Pomerium Zero route must target only http://worker:8080"
            )
        policy_ids = route.get("policyIds")
        enforced_policy_ids = route.get("enforcedPolicyIds")
        if not isinstance(policy_ids, list) or not isinstance(
            enforced_policy_ids, list
        ):
            raise PomeriumError("Pomerium Zero route policies must be lists")
        policies = policy_ids + enforced_policy_ids
        if not policies or not all(
            isinstance(value, str) and value for value in policies
        ):
            raise PomeriumError("Pomerium Zero route must have an access policy")

    def point_cluster(self, cluster: Cluster, ip: str) -> None:
        try:
            address = str(ipaddress.IPv4Address(ip))
        except ipaddress.AddressValueError as error:
            raise PomeriumError(
                f"Akash returned an invalid Pomerium IP: {ip}"
            ) from error
        if cluster.override_ip == address:
            return
        self.update_cluster(cluster, address)

    def restore_cluster(
        self,
        cluster: Cluster,
        assigned_ip: str,
        deadline: float | None = None,
    ) -> None:
        if cluster.override_ip == assigned_ip:
            return
        current = self.get_cluster(cluster, deadline)
        if current.override_ip == cluster.override_ip:
            return
        if current.override_ip != assigned_ip:
            raise PomeriumError(
                "Pomerium cluster IP changed during the campaign; refusing to overwrite it"
            )
        self.update_cluster(cluster, cluster.override_ip, deadline)

    def get_cluster(
        self,
        cluster: Cluster,
        deadline: float | None = None,
    ) -> Cluster:
        path = f"/organizations/{cluster.organization_id}/clusters/{cluster.id}"
        value = self.request("GET", path, deadline=deadline)
        if not isinstance(value, dict):
            raise PomeriumError("Pomerium cluster response must be an object")
        return cluster_from_response(value, cluster.organization_id)

    def update_cluster(
        self,
        cluster: Cluster,
        ip: str | None,
        deadline: float | None = None,
    ) -> None:
        properties = {"name": cluster.name}
        if ip:
            properties["manualOverrideIpAddress"] = ip
        path = f"/organizations/{cluster.organization_id}/clusters/{cluster.id}"
        value = self.request("PUT", path, properties, deadline=deadline)
        if not isinstance(value, dict):
            raise PomeriumError("Pomerium update response must be an object")

    def authenticate(self, api_token: str) -> str:
        if not api_token:
            raise PomeriumError("POMERIUM_ZERO_API_TOKEN must not be empty")
        value = self.request(
            "POST",
            "/token",
            {"refreshToken": api_token},
            authenticated=False,
        )
        if not isinstance(value, dict):
            raise PomeriumError("Pomerium token response must be an object")
        return text(value, "idToken")

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        *,
        authenticated: bool = True,
        deadline: float | None = None,
    ) -> Any:
        body = (
            None
            if payload is None
            else json.dumps(payload, separators=(",", ":")).encode()
        )
        headers = {"User-Agent": "one-more-run/0.1"}
        if authenticated:
            headers["Authorization"] = f"Bearer {self.id_token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        request_deadline = self.deadline if deadline is None else deadline
        try:
            with urllib.request.urlopen(
                request,
                timeout=min(30, remaining(request_deadline)),
            ) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise PomeriumError(api_error(error)) from error
        except (OSError, ValueError) as error:
            raise PomeriumError(f"Pomerium Zero API request failed: {error}") from error


def route_hostname(route_url: str) -> str:
    route = urlsplit(route_url)
    if (
        route.scheme != "https"
        or not route.hostname
        or route.username
        or route.password
        or route.port not in (None, 443)
        or route.path not in ("", "/")
        or route.query
        or route.fragment
    ):
        raise PomeriumError(
            "POMERIUM_ROUTE_URL must be an HTTPS origin without a path, query, or fragment"
        )
    return route.hostname.lower()


def route_origin(route_url: str) -> str:
    return f"https://{route_hostname(route_url)}"


def cluster_from_response(value: Any, organization_id: str) -> Cluster:
    if not isinstance(value, dict):
        raise PomeriumError("Pomerium cluster must be an object")
    flavor = value.get("flavor", "standard")
    if flavor != "standard":
        raise PomeriumError("Pomerium route must belong to a standard Zero cluster")
    override = value.get("manualOverrideIpAddress")
    if override is not None and not isinstance(override, str):
        raise PomeriumError("Pomerium cluster override IP must be a string")
    return Cluster(
        organization_id=organization_id,
        id=text(value, "id"),
        namespace_id=text(value, "namespaceId"),
        name=text(value, "name"),
        fqdn=text(value, "fqdn").lower().rstrip("."),
        override_ip=override or None,
    )


def objects(value: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise PomeriumError(f"Pomerium {name} response must be a list of objects")
    return value


def text(value: dict[str, Any], name: str) -> str:
    item = value.get(name)
    if not isinstance(item, str) or not item:
        raise PomeriumError(f"Pomerium {name} must be a non-empty string")
    return item


def remaining(deadline: float) -> float:
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise PomeriumError("timed out waiting for Pomerium Zero")
    return seconds


def api_error(error: urllib.error.HTTPError) -> str:
    message = error.reason
    try:
        value = json.loads(error.read(16_384))
        if isinstance(value, dict):
            message = value.get("message") or value.get("error") or message
    except (OSError, ValueError):
        pass
    return f"Pomerium Zero API returned HTTP {error.code}: {message}"
