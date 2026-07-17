# Judging script

## Three-minute talk track

### 0:00–0:25 — Observation

“Most coding-agent loops treat a plausible diff as progress. ML does not. A
candidate can compile, read beautifully, and still lose on held-out data. One
More Run separates the agent that changes the program from the experiment that
decides whether the change survives.”

Show page 2.

### 0:25–0:55 — Nested loops

“Inside, Codex gets a bounded number of cheap edit turns. It sees the objective,
current champion, measured history, and recalled evidence. It can change the
whole training program, then explicitly says when the candidate is ready.

Outside, the expensive loop runs one fixed evaluation on an Akash GPU. It
verifies the source hash and evaluator identity, then records `KEEP`, `REJECT`,
or `CRASH`. Only measured improvement changes the champion.”

Show page 3.

### 0:55–1:30 — Demo

Run or show:

```bash
uv run omr research research.md --max-runs 3 --yes
```

Point to:

1. recalled memory;
2. inner-loop turn and candidate readiness;
3. candidate SHA-256;
4. fixed evaluator identity;
5. metric and decision; and
6. explicit run/time/spend limits.

Say: “The interface is a projection. The JSONL receipt is the durable result.”

### 1:30–2:00 — Memory

“After the receipt is verified and appended, Hindsight retains the objective,
hypothesis, candidate, evaluator, metric, and decision. Its semantic, keyword,
graph, and temporal retrieval brings relevant wins and failures into the next
campaign. Memory can fail without consuming a GPU run because the ledger stays
the source of truth.”

Show page 5.

### 2:00–2:35 — Akash and Pomerium

“Direct bearer-authenticated Akash is the proven default, bounded by an explicit
deposit and bid ceiling. With `--pomerium`, Zero becomes the only public service
and validates service identity before proxying to the private worker. The
worker still checks its own bearer token. Those are separate trust boundaries.

Before spend, One More Run validates the exact Zero route and policy. On exit,
it restores the previous cluster IP and closes compute independently.”

Show page 6.

### 2:35–3:00 — Consequence

“The reusable result is not this compact regression task. It is the contract:
bounded mutation, fixed measurement, content-addressed evidence, graph-backed
memory, explicit spend, and identity-aware compute.

One More Prompt starts the idea. One More Run tests it.”

Show page 8 and stop.

## Demo fallback

If live Akash bidding, DNS, or GPU startup would consume the judging window:

1. show the deterministic CLI capture from `carousel_cli.py`;
2. run the local numeric loop to prove the event protocol and ledger;
3. open one real JSONL receipt;
4. show the Akash SDL and Pomerium private route; and
5. state exactly which external wait was replaced by recorded evidence.

Never spend the presentation waiting on infrastructure.

## Likely judge questions

### How is this different from a coding agent running tests?

The inner agent cannot declare success. A separate outer loop owns held-out
measurement, candidate/evaluator identity checks, the champion, budgets, and
durable receipts.

### Why call it a Ralph-style loop?

The inner loop gives a fresh bounded Codex turn the same durable objective and
state until the candidate is ready. The outer loop then changes that state only
through measured evidence. Fresh reasoning; durable work.

### What exactly is remembered?

Objective, hypothesis, normalized candidate identity, evaluator, metric,
decision, error, and provider. The JSONL ledger is canonical. Hindsight is the
derived, graph-backed recall layer.

### Can candidate code escape?

The demo uses a dedicated ephemeral worker, bounded payload, scrubbed
environment, separate child process, and hard timeout. It is not presented as a
hardened hostile-code or multitenant sandbox. A production arbitrary-code
service would add an actual isolation runtime.

### Why both Pomerium and a worker token?

Pomerium authenticates the calling service and protects the network route. The
bearer token authenticates the request to the worker application. Removing
either would collapse two distinct authorities.

### Why Akash?

The outer loop needs burstable GPU compute with an explicit market price and a
deployment lifecycle the controller can own. Akash makes compute a measured,
bounded part of the experiment rather than permanent infrastructure.

### What happens when memory is down?

The campaign continues without recalled context. Retention is best-effort after
the durable ledger append, so memory failure does not erase evidence or consume
an experiment budget.

### What prevents cherry-picking?

Every started candidate is content-addressed. `KEEP`, `REJECT`, and `CRASH`
receipts remain in the append-only ledger, and the controller verifies the
candidate and evaluator identities before accepting the result.
