# Integration review

Private working note. Do not paste this file into Devpost or LinkedIn.

## Work reviewed

| Capability | Location | Evidence observed |
|---|---|---|
| Adaptive measured outer loop | `agent/adaptive-automl-loop`, PR #1 | committed; fixed evaluator, candidate hashes, keep/reject loop |
| Pomerium Zero on Akash | `agent/pomerium`, PR #2 | committed; 39 tests; route/policy preflight and bounded cleanup |
| Hindsight memory | shared `agent/pomerium` worktree | uncommitted during review; 45 tests passed independently |
| Whole-program Codex loop | `/Users/drk/src/one-more-run-codex-loop` | uncommitted during review; 38 tests passed independently |
| Public materials | `agent/submission-materials` | isolated worktree to avoid touching either implementation owner |

No child agents remained active in this thread when reviewed. The two dirty
worktrees are therefore the only additional implementation state visible from
this checkout.

## What converges cleanly

The target system has a strong primitive split:

1. Codex mutates only a bounded candidate workspace.
2. The controller owns budgets, orchestration, receipts, and the champion.
3. The Akash worker owns fixed evaluation.
4. Pomerium owns external identity and route policy.
5. The worker bearer token remains a separate application-auth boundary.
6. The JSONL ledger is durable truth; Hindsight is rebuildable derived memory.

That is the right story for judges because every layer has one visible job.

## Required stitching before judging

1. Merge the whole-program loop onto the Pomerium stack. Both branches change
   `akash.py`, `cli.py`, `README.md`, worker behavior, and tests; resolve by
   semantics rather than by choosing one file wholesale.
2. Pass `OMR_POMERIUM_JWT` into the Codex adapter and add
   `X-Pomerium-Authorization` to both health and code-experiment requests.
3. Put recalled `OMR_MEMORY` into a protected `memory.md` control file or the
   inner-loop prompt. The current Hindsight branch recalls memory, but the
   whole-program Codex adapter does not yet consume it.
4. Retain memory only after candidate/evaluator identity validation and the
   durable JSONL append. Preserve the current fail-open memory behavior.
5. Add Hindsight environment names to every secret-drop boundary; never send
   its API key to Codex, Akash, Pomerium, or the worker.
6. Rebuild the worker image with `code_runner.py`, publish it, and replace the
   SDL digest. The source change alone does not update the Akash runtime.
7. Calculate or omit displayed experiment cost. The whole-program adapter
   currently emits `cost_usd: 0.0`; do not present this as measured zero cost.
8. Run the combined test suite, then one local end-to-end campaign. Run a paid
   Akash/Pomerium smoke only with the explicit spend confirmation already built
   into `--yes`.

## Security wording

Say:

- dedicated ephemeral worker;
- bounded source payload;
- separate child process;
- hard timeout;
- scrubbed environment;
- held-out validation targets;
- Pomerium-protected network boundary.

Do not say:

- hostile-code sandbox;
- multitenant isolation;
- ungameable evaluator;
- signed receipt; or
- production-hardened arbitrary-code execution.

The current evaluator executes candidate Python in a child process on a
dedicated worker. Timeout and environment scrubbing are useful boundaries, but
they are not a hardened sandbox.

## Submission truth gate

- [ ] Combined branch contains outer loop, inner loop, Hindsight, Akash, and
      Pomerium.
- [ ] All combined tests pass.
- [ ] `OMR_MEMORY` reaches the inner Codex loop.
- [ ] Pomerium identity reaches code-evaluator requests.
- [ ] Worker image digest matches the combined source.
- [ ] Repository is public and both submodules initialize.
- [ ] Design mock is captioned “illustrative” unless replaced by a live run.
- [ ] Video and repository links work in an incognito browser.
- [ ] Devpost special-prize selections are Akash and Pomerium only.
