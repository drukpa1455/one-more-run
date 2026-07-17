from __future__ import annotations

import argparse
import json
import math
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from one_more_run.protocol import identify_candidate, improves


class ProtocolError(ValueError):
    """An adapter emitted an invalid event."""


@dataclass(frozen=True)
class ExperimentPlan:
    run: int
    hypothesis: str
    candidate: dict[str, Any]
    candidate_sha256: str
    evaluator: str


@dataclass(frozen=True)
class Experiment:
    plan: ExperimentPlan
    metric: float | None
    decision: str
    seconds: float
    cost_usd: float
    provider: str


@dataclass
class Campaign:
    goal: str
    maximize: bool = False
    provider: str = "waiting"
    status: str = "starting"
    current_plan: ExperimentPlan | None = None
    current_metric: float | None = None
    experiments: list[Experiment] = field(default_factory=list)

    @property
    def best(self) -> Experiment | None:
        measured = [item for item in self.experiments if item.metric is not None]
        if not measured:
            return None
        return (max if self.maximize else min)(measured, key=lambda item: float(item.metric))

    def apply(self, event: dict[str, Any]) -> Experiment | None:
        kind = text_field(event, "type")

        if kind == "campaign.started":
            if self.status != "starting":
                raise ProtocolError("campaign already started")
            self.provider = text_field(event, "provider")
            self.status = "running"
            return None

        if kind == "experiment.started":
            if self.status != "running" or self.current_plan is not None:
                raise ProtocolError("cannot start an experiment now")
            plan = plan_from_event(event)
            expected = len(self.experiments) + 1
            if plan.run != expected:
                raise ProtocolError(f"expected run {expected}, got {plan.run}")
            self.current_plan = plan
            self.current_metric = None
            self.status = "running"
            return None

        if kind == "experiment.progress":
            self.require_current(event)
            self.current_metric = number_field(event, "metric")
            return None

        if kind == "experiment.finished":
            plan = self.require_current(event)
            if text_field(event, "candidate_sha256") != plan.candidate_sha256:
                raise ProtocolError("worker measured a different candidate")
            if text_field(event, "evaluator") != plan.evaluator:
                raise ProtocolError("worker used a different evaluator")
            metric = optional_number_field(event, "metric")
            experiment = Experiment(
                plan=plan,
                metric=metric,
                decision=self.decision(metric),
                seconds=number_field(event, "seconds"),
                cost_usd=number_field(event, "cost_usd", default=0.0),
                provider=self.provider,
            )
            self.experiments.append(experiment)
            self.current_plan = None
            self.current_metric = None
            return experiment

        if kind == "campaign.finished":
            if self.status != "running" or self.current_plan is not None:
                raise ProtocolError("cannot finish the campaign now")
            self.status = "complete"
            return None

        raise ProtocolError(f"unknown event type: {kind}")

    def require_current(self, event: dict[str, Any]) -> ExperimentPlan:
        run = int_field(event, "run")
        if self.current_plan is None or self.current_plan.run != run:
            current = None if self.current_plan is None else self.current_plan.run
            raise ProtocolError(f"event for run {run}, current run is {current}")
        return self.current_plan

    def decision(self, metric: float | None) -> str:
        if metric is None:
            return "crash"
        best = self.best
        incumbent = None if best is None else best.metric
        return "keep" if improves(metric, incumbent, self.maximize) else "reject"


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    adapter = split_adapter(arguments)
    args = parser().parse_args(arguments)
    try:
        if args.command_name == "run":
            args.adapter = adapter
            return run(args)
        if args.command_name == "akash":
            from one_more_run.akash import run as run_on_akash

            return run_on_akash(args, run)
        if args.command_name == "status":
            return status(args)
    except (OSError, ProtocolError, ValueError) as error:
        Console(stderr=True).print(f"[red]error:[/red] {error}")
        return 1
    return 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="omr", description="Autonomous research runs on any compute")
    commands = root.add_subparsers(dest="command_name", required=True)

    run_command = commands.add_parser("run", help="run a campaign adapter and track its experiments")
    run_command.add_argument("research", type=Path, help="research objective in Markdown")
    run_command.add_argument("--ledger", type=Path, default=Path("experiments.jsonl"))
    run_command.add_argument("--max-runs", type=positive_int, default=6)
    run_command.add_argument("--timeout", type=positive_float, default=3600.0, metavar="SECONDS")
    run_command.add_argument("--maximize", action="store_true", help="higher metrics are better")
    run_command.add_argument("--plain", action="store_true", help="print events without a live display")

    akash_command = commands.add_parser("akash", help="deploy, run, and close an Akash GPU worker")
    akash_command.add_argument("research", type=Path, help="research objective in Markdown")
    akash_command.add_argument("--sdl", type=Path, default=Path("deploy/akash.yaml"))
    akash_command.add_argument("--ledger", type=Path, default=Path("experiments.jsonl"))
    akash_command.add_argument("--max-runs", type=positive_int, default=3)
    akash_command.add_argument("--timeout", type=positive_float, default=600.0, metavar="SECONDS")
    akash_command.add_argument("--deposit", type=positive_float, default=0.5, metavar="USD")
    akash_command.add_argument("--max-bid", type=positive_float, default=1000.0, metavar="UACT")
    akash_command.add_argument("--maximize", action="store_true", help="higher metrics are better")
    akash_command.add_argument("--plain", action="store_true", help="print events without a live display")
    akash_command.add_argument("--yes", action="store_true", help="authorize the displayed spend limits")

    status_command = commands.add_parser("status", help="show a saved experiment ledger")
    status_command.add_argument("ledger", type=Path, nargs="?", default=Path("experiments.jsonl"))
    status_command.add_argument("--maximize", action="store_true", help="higher metrics are better")
    return root


def run(args: argparse.Namespace) -> int:
    if not args.research.is_file():
        raise ValueError(f"research objective not found: {args.research}")
    adapter = list(args.adapter)
    if not adapter:
        raise ValueError("missing adapter command; place it after --")

    campaign = Campaign(goal=args.research.read_text().strip(), maximize=args.maximize)
    if args.ledger.exists():
        raise ValueError(f"ledger already exists: {args.ledger}")
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        OMR_RESEARCH=str(args.research.resolve()),
        OMR_MAX_RUNS=str(args.max_runs),
        OMR_MAXIMIZE="1" if args.maximize else "0",
    )
    environment.update(getattr(args, "environment", {}))
    for name in getattr(args, "drop_environment", ()):
        environment.pop(name, None)
    process = subprocess.Popen(
        adapter,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        bufsize=1,
        env=environment,
    )

    try:
        return consume(process, campaign, args.ledger, args.max_runs, args.timeout, args.plain)
    finally:
        stop(process)


def consume(
    process: subprocess.Popen[str],
    campaign: Campaign,
    ledger: Path,
    max_runs: int,
    timeout: float,
    plain: bool,
) -> int:
    lines: queue.Queue[str | None] = queue.Queue()
    reader = threading.Thread(target=read_lines, args=(process, lines), daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    console = Console()

    live = None if plain else Live(render(campaign), console=console, refresh_per_second=8)
    if live:
        live.start(refresh=True)

    try:
        while True:
            if time.monotonic() >= deadline:
                raise ProtocolError(f"campaign exceeded {timeout:g} seconds")
            try:
                line = lines.get(timeout=0.1)
            except queue.Empty:
                if process.poll() is not None and not reader.is_alive():
                    break
                continue
            if line is None:
                break

            event = parse_event(line)
            experiment = campaign.apply(event)
            if experiment:
                append(ledger, experiment)
                if plain:
                    console.print(Text(summary(experiment)))
                if len(campaign.experiments) >= max_runs:
                    campaign.status = "budget reached"
                    break
            if live:
                live.update(render(campaign), refresh=True)
    finally:
        if live:
            live.update(render(campaign), refresh=True)
            live.stop()

    if len(campaign.experiments) >= max_runs:
        return 0
    return_code = process.wait()
    if return_code:
        raise ProtocolError(f"adapter exited with status {return_code}")
    if not campaign.experiments:
        raise ProtocolError("adapter completed without an experiment")
    return 0


def status(args: argparse.Namespace) -> int:
    records = load(args.ledger)
    campaign = Campaign(goal=f"Ledger: {args.ledger}", maximize=args.maximize, status="saved")
    campaign.experiments.extend(records)
    if records:
        campaign.provider = records[-1].provider
    Console().print(render(campaign))
    return 0


def read_lines(process: subprocess.Popen[str], lines: queue.Queue[str | None]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        lines.put(line)
    lines.put(None)


def stop(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def parse_event(line: str) -> dict[str, Any]:
    try:
        event = json.loads(line)
    except json.JSONDecodeError as error:
        raise ProtocolError(f"adapter emitted non-JSON output: {line.rstrip()}") from error
    if not isinstance(event, dict):
        raise ProtocolError("adapter events must be JSON objects")
    return event


def append(path: Path, experiment: Experiment) -> None:
    with path.open("a") as ledger:
        ledger.write(json.dumps(asdict(experiment), separators=(",", ":")) + "\n")
        ledger.flush()
        os.fsync(ledger.fileno())


def load(path: Path) -> list[Experiment]:
    if not path.is_file():
        raise ValueError(f"ledger not found: {path}")
    records = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ProtocolError("ledger records must be JSON objects")
            records.append(experiment_from_record(record))
        except (TypeError, json.JSONDecodeError, ProtocolError) as error:
            raise ProtocolError(f"invalid ledger record on line {number}") from error
    return records


def render(campaign: Campaign) -> Group:
    title = Text("ONE MORE RUN", style="bold cyan")
    title.append(f"  {campaign.status}", style="dim")
    goal = campaign.goal.splitlines()[0].lstrip("# ") if campaign.goal else ""
    header = Panel(Text(goal), title=title, subtitle=f"compute: {campaign.provider}", border_style="cyan")

    table = Table(expand=True)
    table.add_column("RUN", justify="right", width=4)
    table.add_column("CANDIDATE", width=10)
    table.add_column("HYPOTHESIS", ratio=1)
    table.add_column("METRIC", justify="right", width=10)
    table.add_column("DECISION", width=9)
    table.add_column("TIME", justify="right", width=8)
    table.add_column("COST", justify="right", width=8)
    for experiment in campaign.experiments[-10:]:
        style = "green" if experiment.decision == "keep" else "red"
        metric = format_metric(experiment.metric)
        table.add_row(
            str(experiment.plan.run),
            experiment.plan.candidate_sha256[:8],
            Text(experiment.plan.hypothesis),
            metric,
            Text(experiment.decision, style=style),
            f"{experiment.seconds:.1f}s",
            f"${experiment.cost_usd:.2f}",
        )

    if campaign.current_plan is not None:
        metric = "waiting" if campaign.current_metric is None else f"metric {campaign.current_metric:.6f}"
        plan = campaign.current_plan
        current = Panel(
            plan.hypothesis,
            title=f"Run {plan.run} · {plan.candidate_sha256[:8]} · {metric}",
        )
    else:
        best = campaign.best
        detail = (
            "No measured experiments yet"
            if best is None
            else f"Best: run {best.plan.run} · {format_metric(best.metric)}"
        )
        current = Panel(detail)
    return Group(header, table, current)


def summary(experiment: Experiment) -> str:
    metric = "crash" if experiment.metric is None else format_metric(experiment.metric)
    plan = experiment.plan
    return f"run {plan.run} #{plan.candidate_sha256[:8]}: {metric} · {experiment.decision} · {plan.hypothesis}"


def format_metric(metric: float | None) -> str:
    if metric is None:
        return "—"
    if metric and abs(metric) < 0.0001:
        return f"{metric:.3e}"
    return f"{metric:.6f}"


def text_field(event: dict[str, Any], name: str) -> str:
    value = event.get(name)
    if not isinstance(value, str) or not value:
        raise ProtocolError(f"{name} must be a non-empty string")
    return value


def int_field(event: dict[str, Any], name: str) -> int:
    value = event.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ProtocolError(f"{name} must be a positive integer")
    return value


def number_field(event: dict[str, Any], name: str, default: float | None = None) -> float:
    value = event.get(name, default)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProtocolError(f"{name} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise ProtocolError(f"{name} must be finite")
    if value < 0 and name in {"seconds", "cost_usd"}:
        raise ProtocolError(f"{name} cannot be negative")
    return value


def optional_number_field(event: dict[str, Any], name: str) -> float | None:
    if event.get(name) is None:
        return None
    return number_field(event, name)


def experiment_from_record(record: dict[str, Any]) -> Experiment:
    plan_record = record.get("plan")
    if not isinstance(plan_record, dict):
        raise ProtocolError("plan must be an object")
    plan = plan_from_event(plan_record)
    recorded_sha256 = text_field(plan_record, "candidate_sha256")
    if recorded_sha256 != plan.candidate_sha256:
        raise ProtocolError("candidate_sha256 does not match candidate")
    decision = text_field(record, "decision")
    if decision not in {"keep", "reject", "crash"}:
        raise ProtocolError("decision must be keep, reject, or crash")
    return Experiment(
        plan=plan,
        metric=optional_number_field(record, "metric"),
        decision=decision,
        seconds=number_field(record, "seconds"),
        cost_usd=number_field(record, "cost_usd"),
        provider=text_field(record, "provider"),
    )


def plan_from_event(event: dict[str, Any]) -> ExperimentPlan:
    try:
        candidate, candidate_sha256 = identify_candidate(event.get("candidate"))
    except ValueError as error:
        raise ProtocolError(str(error)) from error
    return ExperimentPlan(
        run=int_field(event, "run"),
        hypothesis=text_field(event, "hypothesis"),
        candidate=candidate,
        candidate_sha256=candidate_sha256,
        evaluator=text_field(event, "evaluator"),
    )


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def split_adapter(arguments: list[str]) -> list[str]:
    if not arguments or arguments[0] != "run" or "--" not in arguments:
        return []
    separator = arguments.index("--")
    adapter = arguments[separator + 1 :]
    del arguments[separator:]
    return adapter
