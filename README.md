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
event protocol; the CLI enforces the run and time budgets, records durable
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
{"type":"experiment.started","run":1,"hypothesis":"baseline"}
{"type":"experiment.progress","run":1,"metric":1.12}
{"type":"experiment.finished","run":1,"metric":1.04,"seconds":300,"cost_usd":0.17}
{"type":"campaign.finished"}
```

One More Run passes `OMR_RESEARCH` and `OMR_MAX_RUNS` to the adapter. The CLI is
the sole owner of the ledger. The next adapter submits `train.py` to a
Pomerium-protected evaluator on an Akash GPU. The evaluator and dataset stay
fixed; only the candidate file crosses the boundary.

The `autoresearch` submodule supplies the initial research workload.

## Hackathon target

- Local research agent that changes one candidate file.
- Akash GPU evaluator behind Pomerium identity-aware access.
- Fixed evaluation and bounded runs, time, and spend.
- Live results with hypotheses, metrics, decisions, duration, and cost.
- A content-addressed winning candidate and replayable `experiments.jsonl`.

One More Prompt starts the idea. **One More Run tests it.**
