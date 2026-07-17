# Three-minute demo

Record evidence from a completed campaign. Do not spend the presentation
waiting for marketplace bidding or image startup.

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
> records the receipt, and keeps only a measured improvement.

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
