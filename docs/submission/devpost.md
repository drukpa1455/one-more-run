# Devpost submission

## Project overview

### Project name

One More Run

### Elevator pitch

Nested research loops where Codex evolves ML programs, Akash GPUs measure them,
Hindsight carries evidence forward, and optional Pomerium Zero protects the evaluator.

### Thumbnail copy

```text
ONE MORE RUN
Autonomous ML research with an empirical outer loop.
```

Use one nested-loop diagram, not a product screenshot. Keep the title in the
upper-left and the candidate → evaluator → memory path readable at thumbnail
size. Export both Opal and Garnet; use one complete mode.

## Project details

Paste everything from the next heading through “One More Run tests it” into
Devpost's **About the project** field.

---

# One More Run

Most coding-agent loops treat a plausible diff as progress. ML does not care
how plausible the diff looks. A cleaner architecture can still lose on
held-out data, and a clever agent can repeat yesterday's failed idea if the
evidence disappears with the session.

One More Run gives autonomous ML research two nested loops and one empirical
rule:

> An agent can change the program. Only an experiment can change the champion.

## What it does

The inner loop is cheap and exploratory. Codex reads the research objective,
the candidate contract, the current champion, measured history, and relevant
long-term memory. It can revise the complete Python training program—features,
model architecture, loss, optimizer, schedule, and module boundaries—across a
bounded number of turns. Static checks run locally. Codex explicitly marks the
candidate ready before any GPU time is spent.

The outer loop is expensive and empirical. One More Run deploys a dedicated
Akash GPU worker and evaluates a content-addressed source bundle against fixed
held-out validation targets. Direct bearer-authenticated Akash is the proven
default; protected mode routes the same request through Pomerium Zero. The
worker returns the candidate hash, evaluator identity, metric, duration, and
any failure. The controller verifies that receipt and makes one of three
decisions: `KEEP`, `REJECT`, or `CRASH`.

Only a measured improvement becomes the next champion.

```text
                         Hindsight memory
                  recall ▲              │ retain verified evidence
                         │              ▼
objective ──► [ INNER: Codex inspect → edit → check → ready? ]
                         │ candidate source + SHA-256
                         ▼
             [ OUTER: Akash GPU fixed evaluation ]
                         │ metric + evaluator receipt
                         ▼
                  KEEP / REJECT / CRASH
                         │
                         └──────────────► next outer iteration
```

## Long-term research memory

An append-only JSONL ledger remains the source of truth. After a receipt is
validated and durably recorded, One More Run retains the objective,
hypothesis, candidate identity, evaluator, metric, decision, and provider in a
Hindsight memory bank.

Hindsight organizes memories across entities, relationships, and time. Its
semantic, keyword, graph, and temporal retrieval paths bring relevant wins and
failures back into the next inner loop. The agent does not merely remember the
last message. It can reuse evidence from previous campaigns without allowing a
memory outage to consume an experiment budget.

## Secure remote measurement

The mutable research agent and the fixed evaluator do not share authority.

- Codex receives only the candidate workspace and its bounded research
  context.
- The local controller owns credentials, budgets, deployment, receipts, and
  the champion.
- Akash supplies ephemeral GPU compute through an immutable deployment
  manifest.
- In protected mode, Pomerium Zero is the deployment's only public service. Its
  policy validates service-account identity before forwarding to the private
  worker.
- The worker separately verifies its bearer token, serializes experiments, and
  executes the candidate in a child process with a bounded payload, scrubbed
  environment, and hard timeout.
- Pomerium consumes its identity header; the worker sees only the application
  credential it owns.

Before spending in protected mode, the controller verifies the exact Pomerium
route, private upstream, and attached policy. Cleanup independently restores
the prior Zero cluster IP and closes the Akash deployment, including on
failure.

```text
LOCAL CONTROL PLANE                         AKASH DATA PLANE

Codex ──candidate──► One More Run ──HTTPS──► Pomerium Zero :443
                           │                  identity policy
                    budgets + ledger                │ private route
                           │                         ▼
                    Hindsight memory           worker :8080
                                             fixed evaluator
```

## How we built it

The controller is a small Python package run with `uv`. Adapters communicate
through a strict JSONL event protocol, so the same ledger and terminal can
supervise local experiments or remote compute. Candidates are normalized and
hashed with SHA-256. A finished event is accepted only when its candidate and
evaluator identities match the experiment plan.

The whole-program evaluator accepts at most 32 Python files and 256 KiB of
source. It holds the validation targets and seed outside the candidate
contract, runs one experiment at a time, and reports crashes as evidence rather
than erasing them.

Akash deployment lifecycle calls are bounded by one campaign deadline and an
explicit deposit/bid ceiling. Runtime credentials are injected only into the
in-memory manifest. Pomerium is pinned by both source revision and immutable
container digest. Hindsight is optional and fail-open; its index can be rebuilt
from the durable ledger.

## Challenges we faced

The hardest part was not asking an agent to edit code. It was deciding which
component gets to call a change “better.” Keeping mutation local and
measurement remote gave the evaluator a stable identity and made regressions
visible.

The second challenge was authority. Pomerium identity, worker authentication,
Akash account access, Codex credentials, and memory credentials each needed a
different path and lifetime. Combining them into one token would have made the
demo simpler and the system weaker.

The third challenge was memory timing. Storing every thought would turn memory
into a larger prompt log. One More Run retains evidence only after the
candidate/evaluator receipt is verified and the ledger write is durable.

## What we learned

- Nested loops need different budgets. Inner edits are cheap; outer measurements
  spend GPU time and therefore need an explicit readiness gate.
- A failed candidate is useful evidence when its identity and failure are
  retained.
- An identity-aware proxy does not replace application authentication. The two
  layers protect different boundaries.
- Long-term memory should be a rebuildable index over durable evidence, not a
  second source of truth.
- Cleanup is part of the research algorithm. A loop that cannot release compute
  or restore routing is not autonomous.

## What's next

The same edit/evaluate/remember contract can move from the compact held-out
regression task to larger open-source training systems and domain prediction
repositories. The evaluator can change; the invariants do not: bounded
mutation, fixed measurement, content-addressed evidence, explicit spend, and
memory earned by results.

One More Prompt starts the idea. **One More Run tests it.**

---

## Built with

Use these Devpost tags, up to the site's limit:

1. Python
2. OpenAI Codex
3. Akash Network
4. Pomerium Zero
5. Hindsight
6. PyTorch
7. Docker
8. uv
9. Rich
10. GitHub Actions
11. JSONL
12. SHA-256
13. GPU computing
14. AutoML
15. Autonomous agents
16. Zero Trust
17. Open source

## Try it out links

- Source: <https://github.com/drukpa1455/one-more-run>
- Demo video: add the final public video URL; omit this link rather than
  submitting a placeholder.

## Project media

Upload these carousel pages as 3:2 crops in this order:

1. Nested-loop architecture.
2. Candidate/evaluator receipt contract.
3. Hindsight evidence-memory graph.
4. Pomerium/Akash trust boundary.
5. CLI experiment ledger.
6. Full system sequence.

Use either the complete Opal set or the complete Garnet set. Do not alternate.

## Video demo outline

Target 90–120 seconds:

1. State the problem and thesis, 15 seconds.
2. Show `omr research ... --yes` and the inner-loop readiness gate, 20 seconds.
3. Show `--pomerium`, the protected Akash deployment, and one outer
   measurement, 30 seconds.
4. Show `KEEP`/`REJECT`, candidate/evaluator hashes, and the JSONL receipt,
   20 seconds.
5. Start a second campaign and show relevant Hindsight recall, 20 seconds.
6. Close on the architecture diagram and repository, 10 seconds.

## Additional info for judges and organizers

### Sponsor / Special Prizes

Select **Akash** and **Pomerium** only.

#### Akash

Akash is the empirical outer loop's compute owner. One More Run creates a
bounded deployment, accepts only bids below the user-authorized ceiling, waits
for a CUDA evaluator, runs content-addressed experiments, records provider and
timing evidence, and closes compute in cleanup. The GPU is not a logo in the
diagram; it is where the champion is decided.

#### Pomerium

In protected mode, Pomerium Zero is the identity boundary for the agentic
runtime and the worker has no public route. A standard Zero cluster receives
the Akash IP lease, enforces the route policy and service-account identity, and
proxies only authorized requests to the private evaluator. One More Run
preflights the route and policy before spend, separates Pomerium identity from
worker bearer authentication, and restores the prior cluster IP during cleanup.

### Final submission checks

- Repository visibility: public.
- Team: solo unless another teammate is actually added.
- Video: public/unlisted and viewable without login.
- Source link: test in an incognito window.
- Terms: accept only after reviewing the official rules.
