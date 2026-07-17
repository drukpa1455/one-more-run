# Integration review

Private working note. Do not paste this file into Devpost or LinkedIn.

## Converged build

| Capability | Canonical owner | Fresh evidence |
|---|---|---|
| Bounded inner Codex loop | `codex_adapter.py` | complete-program edits, readiness gate, protected memory input |
| Empirical outer loop | `cli.py` | candidate/evaluator verification, fsynced JSONL, keep/reject/crash |
| Akash lifecycle | `akash.py` | explicit spend approval, bounded bid/deadline, independent cleanup |
| Pomerium Zero boundary | `pomerium.py`, `deploy/akash.yaml` | route/upstream/policy validation, private worker, route restoration |
| Long-term memory | `hindsight.py` | bounded fail-open recall and idempotent post-receipt retention |
| Fixed code evaluator | `worker.py`, `code_runner.py` | bounded payload, hidden targets, child-process timeout |
| Public materials | `docs/submission/` | Devpost, LinkedIn, carousel, judging script, two complete themes |

The final integration keeps one owner per fact:

1. Codex mutates only the candidate workspace.
2. The controller owns budgets, orchestration, receipts, and the champion.
3. The Akash worker owns fixed measurement.
4. Pomerium owns external service identity and route policy.
5. The worker bearer token remains separate application authentication.
6. The JSONL ledger is durable truth; Hindsight is rebuildable derived memory.

## Verified stitching

- The Codex research adapter sends `X-Pomerium-Authorization` on health and
  code-experiment requests while keeping the worker bearer token separate.
- Recalled `OMR_MEMORY` is materialized as protected `memory.md`; Hindsight,
  Akash, Pomerium, and worker credentials are excluded from Codex.
- Retention happens only after the controller validates the receipt and fsyncs
  the JSONL ledger.
- The final SDL keeps the published code-worker digest from PR #4 and adds a
  digest-pinned Pomerium service as the only public endpoint.
- Both source submodules initialize at their pinned revisions.
- `uv run pytest -q` passes all 58 combined tests.
- The repository is public and the design CLI renders in both Opal and Garnet.

## Remaining operator-only steps

These require external state or user-owned accounts and are intentionally not
fabricated:

1. Run a paid Akash/Pomerium smoke only if the displayed deposit, bid, deadline,
   and temporary route mutation are acceptable; `--yes` is the confirmation.
2. Keep the carousel terminal marked “illustrative design mock” unless it is
   replaced with a real receipt.
3. Upload the final public/unlisted video and test its URL and the repository
   URL in an incognito window.
4. Select Akash and Pomerium in Devpost's sponsor-prize field and submit.

## Security wording

Say:

- dedicated ephemeral worker;
- bounded source payload;
- separate child process;
- hard timeout;
- scrubbed environment;
- held-out validation targets; and
- Pomerium-protected network boundary.

Do not say:

- hostile-code sandbox;
- multitenant isolation;
- ungameable evaluator;
- signed receipt; or
- production-hardened arbitrary-code execution.

The evaluator executes candidate Python in a child process on a dedicated
worker. Timeout and environment scrubbing are useful boundaries, but they are
not a hardened sandbox.

## Submission truth gate

- [x] Outer loop, inner loop, Hindsight, Akash, and Pomerium converge.
- [x] `OMR_MEMORY` reaches the protected Codex context.
- [x] Pomerium identity reaches both code-evaluator requests.
- [x] Worker image digest includes the code evaluator.
- [x] Repository is public and both submodules initialize.
- [x] Both complete design modes and the captioned illustrative CLI exist.
- [ ] Optional paid infrastructure smoke is recorded.
- [ ] Final video and public links are tested without login.
- [ ] Devpost fields are pasted, sponsor prizes selected, and submission sent.
