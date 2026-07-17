"""Bounded Akash Console deployment lifecycle."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from rich.console import Console

from one_more_run.pomerium import Cluster, ZeroAPI
from one_more_run.protocol import NUMERIC_EVALUATOR
from one_more_run.settings import secret


API_URL = "https://console-api.akash.network"
MIN_DEPOSIT_USD = 0.5
POLL_SECONDS = 3.0
EVALUATOR = NUMERIC_EVALUATOR
POMERIUM_ENVIRONMENT = (
    "POMERIUM_ZERO_TOKEN",
    "POMERIUM_ZERO_API_TOKEN",
    "POMERIUM_ROUTE_URL",
    "POMERIUM_SERVICE_ACCOUNT_JWT",
)


class AkashError(ValueError):
    """The Akash lifecycle could not safely continue."""


@dataclass(frozen=True)
class Deployment:
    dseq: str
    manifest: str


@dataclass(frozen=True)
class Bid:
    dseq: str
    gseq: int
    oseq: int
    provider: str
    amount: Decimal
    denom: str
    state: str


def run(
    args: argparse.Namespace, run_campaign: Callable[[argparse.Namespace], int]
) -> int:
    """Deploy a worker, run a campaign, and close the deployment."""
    if not args.yes:
        raise AkashError(
            f"deployment would deposit ${args.deposit:.2f}, accept at most "
            f"{args.max_bid:g} uact/block, run for at most {args.timeout:g}s, "
            "and temporarily point a Pomerium Zero cluster at its Akash IP; "
            "pass --yes to authorize it"
        )
    if args.deposit < MIN_DEPOSIT_USD:
        raise AkashError(f"deposit must be at least ${MIN_DEPOSIT_USD:.2f}")
    if not args.research.is_file():
        raise AkashError(f"research objective not found: {args.research}")
    if args.ledger.exists():
        raise AkashError(f"ledger already exists: {args.ledger}")
    for required_file in getattr(args, "required_files", ()):
        if not required_file.exists():
            raise AkashError(f"required path not found: {required_file}")
    workspace = getattr(args, "workspace", None)
    if workspace is not None and workspace.exists():
        raise AkashError(f"campaign workspace already exists: {workspace}")
    api_key = secret("AKASH_API_KEY")
    if not api_key:
        raise AkashError("run `omr setup` or set AKASH_API_KEY")
    if not args.sdl.is_file():
        raise AkashError(f"Akash SDL not found: {args.sdl}")

    pomerium_environment = {
        name: required_environment(name) for name in POMERIUM_ENVIRONMENT
    }
    route_url = pomerium_environment["POMERIUM_ROUTE_URL"].rstrip("/")
    deadline = time.monotonic() + args.timeout
    zero = ZeroAPI(pomerium_environment["POMERIUM_ZERO_API_TOKEN"], deadline)
    cluster = zero.cluster_for_route(route_url)
    zero.validate_route(cluster, route_url)
    worker_token = secrets.token_urlsafe(32)
    sdl = inject_secrets(
        args.sdl.read_text(),
        worker_token,
        pomerium_environment["POMERIUM_ZERO_TOKEN"],
    )
    client = ConsoleAPI(api_key, deadline=deadline)
    return orchestrate(
        client,
        zero,
        cluster,
        args,
        run_campaign,
        sdl,
        route_url,
        worker_token,
        pomerium_environment["POMERIUM_SERVICE_ACCOUNT_JWT"],
        deadline,
    )


def orchestrate(
    client: ConsoleAPI,
    zero: ZeroAPI,
    cluster: Cluster,
    args: argparse.Namespace,
    run_campaign: Callable[[argparse.Namespace], int],
    sdl: str,
    route_url: str,
    worker_token: str,
    pomerium_jwt: str,
    deadline: float,
) -> int:
    console = Console(stderr=True)
    deployment = client.create(sdl, args.deposit)
    console.print(
        f"Akash deployment [cyan]{deployment.dseq}[/cyan] created · "
        f"deposit ${args.deposit:.2f}"
    )

    failed = False
    assigned_ip = None
    try:
        bid = wait_for_bid(
            client, deployment.dseq, Decimal(str(args.max_bid)), deadline
        )
        console.print(
            f"Accepting [cyan]{format(bid.amount, 'f')} {bid.denom}/block[/cyan] "
            f"from {bid.provider}"
        )
        client.lease(deployment, bid)
        leased_ip = wait_for_pomerium_ip(client, bid, deadline)
        assigned_ip = leased_ip
        zero.point_cluster(cluster, leased_ip)
        wait_for_worker(
            client,
            bid,
            route_url,
            pomerium_jwt,
            deadline,
            getattr(args, "evaluator", EVALUATOR),
        )
        console.print(f"Worker ready behind Pomerium at [cyan]{route_url}[/cyan]")

        campaign_args = argparse.Namespace(**vars(args))
        campaign_args.adapter = [
            sys.executable,
            "-m",
            getattr(args, "adapter_module", "one_more_run.akash_adapter"),
        ]
        campaign_args.environment = {
            "OMR_WORKER_URL": route_url,
            "OMR_WORKER_TOKEN": worker_token,
            "OMR_POMERIUM_JWT": pomerium_jwt,
            "OMR_BID_UACT": str(bid.amount),
            **getattr(args, "adapter_environment", {}),
        }
        campaign_args.drop_environment = ["AKASH_API_KEY", *POMERIUM_ENVIRONMENT]
        campaign_args.timeout = remaining(deadline, "campaign")
        return run_campaign(campaign_args)
    except BaseException:
        failed = True
        raise
    finally:
        cleanup_error = None
        try:
            client.close(deployment.dseq)
            console.print(f"Akash deployment [cyan]{deployment.dseq}[/cyan] closed")
        except Exception as error:
            if failed:
                console.print(f"[red]deployment cleanup failed:[/red] {error}")
            else:
                cleanup_error = error
        if assigned_ip:
            try:
                zero.restore_cluster(
                    cluster,
                    assigned_ip,
                    time.monotonic() + 30,
                )
                console.print("Pomerium cluster route restored")
            except Exception as error:
                if failed or cleanup_error:
                    console.print(f"[red]Pomerium cleanup failed:[/red] {error}")
                else:
                    cleanup_error = error
        if cleanup_error:
            raise cleanup_error


class ConsoleAPI:
    def __init__(
        self,
        api_key: str,
        base_url: str = API_URL,
        deadline: float | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.deadline = deadline

    def create(self, sdl: str, deposit: float) -> Deployment:
        data = self.request(
            "POST",
            "/v1/deployments",
            {"data": {"sdl": sdl, "deposit": deposit}},
        )
        if not isinstance(data, dict):
            raise AkashError("Akash create response data must be an object")
        return Deployment(text(data, "dseq"), text(data, "manifest"))

    def bids(self, dseq: str) -> list[Bid]:
        data = self.request("GET", f"/v1/bids?dseq={dseq}")
        if not isinstance(data, list):
            raise AkashError("Akash bids response data must be a list")
        return [bid_from_response(item, dseq) for item in data]

    def lease(self, deployment: Deployment, bid: Bid) -> None:
        self.request(
            "POST",
            "/v1/leases",
            {
                "manifest": deployment.manifest,
                "leases": [
                    {
                        "dseq": bid.dseq,
                        "gseq": bid.gseq,
                        "oseq": bid.oseq,
                        "provider": bid.provider,
                    }
                ],
            },
        )

    def deployment(self, dseq: str) -> dict[str, Any]:
        data = self.request("GET", f"/v1/deployments/{dseq}")
        if not isinstance(data, dict):
            raise AkashError("Akash deployment response data must be an object")
        return data

    def close(self, dseq: str) -> None:
        data = self.request("DELETE", f"/v1/deployments/{dseq}", timeout=30)
        if not isinstance(data, dict) or data.get("success") is not True:
            raise AkashError("Akash did not confirm deployment closure")

    def request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        timeout: float | None = None,
    ) -> Any:
        body = (
            None
            if payload is None
            else json.dumps(payload, separators=(",", ":")).encode()
        )
        headers = {"User-Agent": "one-more-run/0.1", "x-api-key": self.api_key}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        if timeout is None:
            timeout = 30.0
            if self.deadline is not None:
                timeout = min(timeout, remaining(self.deadline, "the Akash API"))
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                value = json.load(response)
        except urllib.error.HTTPError as error:
            raise AkashError(api_error(error)) from error
        except (OSError, ValueError) as error:
            raise AkashError(f"Akash API request failed: {error}") from error
        if not isinstance(value, dict) or "data" not in value:
            raise AkashError("Akash API response must contain data")
        return value["data"]


def wait_for_bid(
    client: ConsoleAPI, dseq: str, max_bid: Decimal, deadline: float
) -> Bid:
    while True:
        eligible = [
            bid
            for bid in client.bids(dseq)
            if bid.state == "open" and bid.denom == "uact" and bid.amount <= max_bid
        ]
        if eligible:
            return min(eligible, key=lambda bid: (bid.amount, bid.provider))
        pause(deadline, "an eligible bid")


def wait_for_pomerium_ip(client: ConsoleAPI, bid: Bid, deadline: float) -> str:
    while True:
        ip = pomerium_ip(client.deployment(bid.dseq), bid)
        if ip:
            return ip
        pause(deadline, "the Pomerium IP lease")


def wait_for_worker(
    client: ConsoleAPI,
    bid: Bid,
    route_url: str,
    pomerium_jwt: str,
    deadline: float,
    evaluator: str = EVALUATOR,
) -> None:
    while True:
        lease_status(client.deployment(bid.dseq), bid)
        health = worker_health(route_url, pomerium_jwt, deadline)
        if health is not None:
            evaluators = health.get("evaluators")
            supported = (
                evaluator in evaluators
                if isinstance(evaluators, list)
                else health.get("evaluator") == evaluator
            )
            if not supported:
                raise AkashError("worker reported an unexpected evaluator")
            if health.get("device") != "cuda":
                raise AkashError("Akash worker has no CUDA device")
            return
        pause(deadline, "the Pomerium-protected GPU worker")


def lease_status(deployment: dict[str, Any], bid: Bid) -> dict[str, Any] | None:
    leases = deployment.get("leases")
    if not isinstance(leases, list):
        raise AkashError("Akash deployment leases must be a list")
    for lease in leases:
        if not isinstance(lease, dict) or not isinstance(lease.get("id"), dict):
            raise AkashError("Akash lease must be an object")
        lease_id = lease["id"]
        if (
            str(lease_id.get("dseq")) != bid.dseq
            or lease_id.get("gseq") != bid.gseq
            or lease_id.get("oseq") != bid.oseq
            or lease_id.get("provider") != bid.provider
        ):
            continue
        if lease.get("state") == "closed":
            raise AkashError("Akash lease closed before the worker became ready")
        status = lease.get("status")
        if not isinstance(status, dict):
            return None
        return status
    return None


def pomerium_ip(deployment: dict[str, Any], bid: Bid) -> str | None:
    status = lease_status(deployment, bid)
    if status is None:
        return None
    ips = status.get("ips")
    entries = ips.get("pomerium") if isinstance(ips, dict) else None
    if not entries:
        return None
    if not isinstance(entries, list) or not isinstance(entries[0], dict):
        raise AkashError("Akash Pomerium IP lease must be a list of objects")
    endpoint = entries[0]
    protocol = endpoint.get("Protocol")
    if (
        endpoint.get("Port") != 443
        or not isinstance(protocol, str)
        or protocol.lower() != "tcp"
    ):
        raise AkashError("Akash assigned an unexpected Pomerium endpoint")
    return text(endpoint, "IP")


def worker_health(
    uri: str,
    pomerium_jwt: str,
    deadline: float,
) -> dict[str, Any] | None:
    request = urllib.request.Request(
        uri + "/healthz",
        headers={
            "User-Agent": "one-more-run/0.1",
            "X-Pomerium-Authorization": pomerium_jwt,
        },
    )
    try:
        with urllib.request.urlopen(
            request, timeout=min(10, remaining(deadline, "worker health"))
        ) as response:
            value = json.load(response)
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def inject_secrets(sdl: str, worker_token: str, zero_token: str) -> str:
    sdl = inject_environment(
        sdl,
        "worker",
        {"OMR_WORKER_TOKEN": worker_token},
    )
    return inject_environment(
        sdl,
        "pomerium",
        {
            "POMERIUM_ZERO_TOKEN": zero_token,
            "TMPDIR": "/tmp/pomerium",
            "XDG_CACHE_HOME": "/tmp/pomerium/cache",
            "XDG_DATA_HOME": "/tmp/pomerium/cache",
        },
    )


def inject_environment(sdl: str, service: str, environment: dict[str, str]) -> str:
    for name, value in environment.items():
        if not value or any(character in value for character in "\r\n"):
            raise AkashError(f"{name} contains unsupported characters")
        if f"{name}=" in sdl:
            raise AkashError(f"SDL already defines {name}")
    lines = sdl.splitlines()
    try:
        services = lines.index("services:")
        services_end = next(
            (
                index
                for index in range(services + 1, len(lines))
                if lines[index].strip() and not lines[index].startswith(" ")
            ),
            len(lines),
        )
        owner = lines.index(f"  {service}:", services + 1, services_end)
        end = next(
            (
                index
                for index in range(owner + 1, services_end)
                if lines[index].strip()
                and len(lines[index]) - len(lines[index].lstrip()) <= 2
            ),
            services_end,
        )
        image = next(
            index
            for index in range(owner + 1, end)
            if lines[index].startswith("    image:")
        )
    except (StopIteration, ValueError) as error:
        raise AkashError(f"SDL must define services.{service}.image") from error
    if any(line.startswith("    env:") for line in lines[owner + 1 : end]):
        raise AkashError(f"services.{service}.env must be owned by the Akash runner")
    values = [f"      - {name}={value}" for name, value in environment.items()]
    lines[image + 1 : image + 1] = ["    env:", *values]
    return "\n".join(lines) + ("\n" if sdl.endswith("\n") else "")


def bid_from_response(value: Any, expected_dseq: str) -> Bid:
    if not isinstance(value, dict) or not isinstance(value.get("bid"), dict):
        raise AkashError("Akash bid must be an object")
    bid = value["bid"]
    bid_id = bid.get("id")
    price = bid.get("price")
    if not isinstance(bid_id, dict) or not isinstance(price, dict):
        raise AkashError("Akash bid id and price must be objects")
    dseq = str(bid_id.get("dseq"))
    if dseq != expected_dseq:
        raise AkashError(f"Akash returned a bid for deployment {dseq}")
    try:
        amount = Decimal(str(price["amount"]))
    except (InvalidOperation, KeyError) as error:
        raise AkashError("Akash bid amount must be a decimal") from error
    if not amount.is_finite() or amount < 0:
        raise AkashError("Akash bid amount must be finite and non-negative")
    return Bid(
        dseq=dseq,
        gseq=positive_int(bid_id, "gseq"),
        oseq=positive_int(bid_id, "oseq"),
        provider=text(bid_id, "provider"),
        amount=amount,
        denom=text(price, "denom"),
        state=text(bid, "state"),
    )


def api_error(error: urllib.error.HTTPError) -> str:
    message = error.reason
    try:
        value = json.loads(error.read(16_384))
        if isinstance(value, dict) and isinstance(value.get("message"), str):
            message = value["message"]
    except (OSError, ValueError):
        pass
    return f"Akash API returned HTTP {error.code}: {message}"


def pause(deadline: float, target: str) -> None:
    time.sleep(min(POLL_SECONDS, remaining(deadline, target)))


def remaining(deadline: float, target: str) -> float:
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise AkashError(f"timed out waiting for {target}")
    return seconds


def text(value: dict[str, Any], name: str) -> str:
    item = value.get(name)
    if not isinstance(item, str) or not item:
        raise AkashError(f"Akash {name} must be a non-empty string")
    return item


def positive_int(value: dict[str, Any], name: str) -> int:
    item = value.get(name)
    if not isinstance(item, int) or isinstance(item, bool) or item < 1:
        raise AkashError(f"Akash {name} must be a positive integer")
    return item


def required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise AkashError(f"set {name} in the environment")
    if any(character in value for character in "\r\n"):
        raise AkashError(f"{name} contains unsupported characters")
    return value
