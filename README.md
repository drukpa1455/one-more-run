# One More Run

**Autoresearch on any compute.**

One More Run is a small control plane for bounded, autonomous ML research. A
research agent proposes an experiment, a compute adapter evaluates it, and One
More Run keeps only measured improvements.

```text
research agent
      │
      ▼
  One More Run ── experiment ledger ── live terminal
      │
      ▼
compute adapter
  ├─ local
  ├─ Akash
  └─ any future cloud
```

The core does not know how a GPU is provisioned. An adapter emits a tiny JSONL
event protocol; the CLI enforces the run and time budgets, verifies that each
measurement matches its proposed candidate and evaluator, records durable
results, and renders the campaign.

## Try the vertical slice

Clone the submodule and run the deterministic adapter:

```bash
git clone --recurse-submodules https://github.com/drukpa1455/one-more-run.git
cd one-more-run
uv sync
uv run omr run research.md --plain -- uv run python examples/demo_adapter.py
uv run omr status experiments.jsonl
```

Remove `--plain` for the live terminal display. The demo adapter performs no
training; it exists to exercise the real process boundary, budget enforcement,
ledger, and UI without a GPU.

## Adapter protocol

Adapters write one JSON object per line to standard output and send human logs
to standard error:

```json
{"type":"campaign.started","provider":"akash"}
{"type":"experiment.started","run":1,"hypothesis":"baseline","candidate":{"learning_rate":0.02,"momentum":0.0,"steps":80},"evaluator":"smoke.linear-regression.v1"}
{"type":"experiment.progress","run":1,"metric":1.12}
{"type":"experiment.finished","run":1,"candidate_sha256":"12865576f004f19fb233e2b4abe1f35a491f63e4e55f39f5479408e772a195bb","evaluator":"smoke.linear-regression.v1","metric":1.04,"seconds":300,"cost_usd":0.17}
{"type":"campaign.finished"}
```

One More Run passes `OMR_RESEARCH` and `OMR_MAX_RUNS` to the adapter. The CLI is
the sole owner of the ledger. It normalizes and hashes the candidate before the
run, then requires the finished event to carry the same hash and evaluator ID.
The ledger therefore preserves rejected candidates instead of retaining only a
score and description. The next adapter submits `train.py` to a
Pomerium-protected evaluator on an Akash GPU. The evaluator and dataset stay
fixed; only the candidate file crosses the boundary.

The `autoresearch` submodule supplies the initial research workload.

## Try the Akash worker

The first real adapter runs a fixed, bounded optimization workload on one GPU.
It proves the remote execution path before we allow an agent to submit code.

1. Start the [$100 Akash Console trial](https://akash.network/docs/getting-started/quick-start/)
   or use an existing funded account.
2. Deploy [`deploy/akash.yaml`](deploy/akash.yaml) in Akash Console.
3. Open the deployment logs and copy the generated `worker token`.
4. Set the endpoint and token only in your shell, then run:

```bash
export OMR_WORKER_URL=https://your-worker.provider.example
read -s "OMR_WORKER_TOKEN?Worker token: "
export OMR_WORKER_TOKEN
uv run omr run research.md -- uv run python examples/akash_adapter.py
```

The worker accepts exactly three bounded numeric parameters; it cannot execute
submitted code. It serializes experiments, rejects oversized requests, returns
a receipt identifying the normalized candidate and fixed evaluator, and
generates a fresh bearer token on every start. The SDL accepts several
trial-eligible NVIDIA models and caps bids at `1000 uact` per block (about
$0.60/hour at six-second blocks). Close the deployment immediately after the
test.

The worker image is published to GHCR from pinned GitHub Actions, and the Akash
SDL pins its immutable OCI digest.

## Hackathon target

- Local research agent that changes one candidate file.
- Akash GPU evaluator behind Pomerium identity-aware access.
- Fixed evaluation and bounded runs, time, and spend.
- Live results with hypotheses, metrics, decisions, duration, and cost.
- A content-addressed winning candidate and replayable `experiments.jsonl`.

One More Prompt starts the idea. **One More Run tests it.**
