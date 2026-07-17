# Three-minute demo

Record evidence from a completed campaign. Do not spend the presentation
waiting for marketplace bidding or image startup.

## Verified result

The repository includes a [real three-run Akash campaign](../demo/README.md).
Run 2 reduced MSE from `0.854451` to `0.002781` with a standard neural training
program. Run 3 reached `3.0408e-15` after Codex inspected the public evaluator
source and synthesized an exact feature basis. Say that distinction plainly;
validation rows stayed held out, but run 3 was not blind function discovery.

## Live terminal replay

```bash
uv run omr replay demo/experiments.jsonl --seconds 165
```

This is the preferred live presentation. It replays the exact checked-in
receipts over 2:45 and is permanently labeled as a replay with no active
compute. Each run gets about 50 seconds: candidate and hypothesis first, then
the measured receipt. A `WHY IT MATTERS` panel supplies three concise talking points
for every phase. The last 16 seconds hold the complete campaign table.

- 0:00–0:50: establish the fixed baseline and receipt identity.
- 0:50–1:39: explain the run 2 neural program and 99.67% MSE reduction.
- 1:39–2:29: show whole-program replacement; disclose the public evaluator
  source used by run 3.
- 2:29–2:45: close on the verified ledger and automatic cleanup.

## If a judge asks for a fresh run

The reliable, zero-spend live path exercises the real controller, adaptive
proposal logic, evaluator receipts, and keep/reject decisions. It does not call
Codex or rewrite a program:

```bash
DEMO_LEDGER="$(mktemp -d)/experiments.jsonl"
uv run omr run research.md \
  --max-runs 6 \
  --ledger "$DEMO_LEDGER" \
  -- uv run python examples/demo_adapter.py
```

If the judge specifically requires a fresh Codex rewrite on Akash, run two
experiments: a baseline and one Codex candidate. This authorizes a $0.50 deposit,
a `1000 uact/block` bid ceiling, and up to ten minutes; marketplace startup means
it is not a safe three-minute-stage dependency.

```bash
RUN_ROOT="$(mktemp -d)"
uv run omr research research.md \
  --max-runs 2 \
  --workspace "$RUN_ROOT/workspace" \
  --ledger "$RUN_ROOT/experiments.jsonl" \
  --timeout 600 \
  --codex-timeout 120 \
  --proposal-turns 1 \
  --deposit 0.5 \
  --max-bid 1000 \
  --yes
```

## Before recording

```bash
uv run omr doctor
uv run omr research research.md \
  --max-runs 3 \
  --workspace .omr/demo \
  --ledger demo/experiments.jsonl \
  --yes
```

Keep the full terminal capture, ledger, and winning workspace. They are the
evidence behind the edited three-minute video.

## Shot list and narration

### 0:00–0:25 — The rule

Show the README architecture diagram.

> Coding agents can make plausible changes forever. Machine learning gives us
> a harder test: did the change improve held-out performance? One More Run lets
> Codex change the program, but only a fixed experiment can change the champion.

### 0:25–0:55 — The inner loop

Show `research.md` and `examples/code_candidate/`.

> Codex gets bounded edit turns. It sees the objective, current champion, and
> measured history. It may refactor features, architecture, loss, optimizer,
> schedule, or modules, and explicitly says when the candidate is ready. That
> readiness gate keeps cheap reasoning inside and expensive GPU runs outside.

### 0:55–1:45 — Real measured evidence

Run:

```bash
uv run omr status demo/experiments.jsonl
```

Show the real capture briefly, then point to baseline, changed source hash,
metric, and `KEEP`/`REJECT`/`CRASH`.

> This is a real Akash campaign. The first row is the baseline. Every later row
> is code Codex chose after observing prior measurements. The worker returns the
> exact source hash and fixed evaluator identity. One More Run verifies both,
> records the receipt, and keeps only a measured improvement. Run 2 gives us a
> 99.67% MSE reduction with a general neural candidate. Run 3 shows whole-program
> synthesis against a public evaluator, which we disclose separately.

### 1:45–2:20 — Trust and bounds

Show `docs/architecture.md` and `deploy/akash.yaml`.

> The local controller owns credentials, spend, the ledger, and cleanup. The
> Akash GPU owns evaluation and never receives the Codex or Akash key. Candidate
> code runs with a bounded payload, scrubbed environment, one-at-a-time lock,
> and hard timeout. The optional Pomerium path adds service identity without
> replacing the worker's own bearer token.

### 2:20–2:50 — The product

Show the one-command invocation and winning candidate files.

> The product is an agentic CLI and durable experiment ledger, not a dashboard.
> It can supervise this compact task today and carry the same edit, evaluate,
> verify, keep-or-revert contract to any training repository or cloud adapter.

### 2:50–3:00 — Close

> One More Prompt starts the idea. One More Run tests it.

Stop. A clean 2:50 is safer than racing the platform's three-minute limit.
