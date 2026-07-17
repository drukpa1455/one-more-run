# Integration review

Private working note. Do not paste this file into Devpost or LinkedIn.

## Canonical build

One More Run has one straight default and two optional upgrades:

1. `omr research ... --yes` runs the bounded Codex inner loop against the direct
   bearer-authenticated Akash evaluator.
2. `--pomerium` selects the protected SDL, validates the Zero route and policy,
   and makes Pomerium the only public service.
3. `OMR_HINDSIGHT_BANK` enables bounded, fail-open recall and post-receipt
   retention. Without it, the same campaign runs without long-term memory.

Ownership remains explicit:

- Codex mutates only the candidate workspace.
- The controller owns budgets, orchestration, receipts, and the champion.
- The Akash worker owns fixed measurement.
- Pomerium owns service identity and route policy only in protected mode.
- The worker bearer token remains separate application authentication.
- The JSONL ledger is durable truth; Hindsight is rebuildable derived memory.

## Source boundaries

- Recalled memory becomes protected `memory.md` and is treated as evidence, not
  authority.
- Hindsight retention occurs only after candidate/evaluator verification and
  the fsynced JSONL append.
- Hindsight, Pomerium, Akash, and worker credentials are excluded from Codex.
- Retained and recalled memory payloads are bounded.
- Direct Akash remains usable without Pomerium or Hindsight configuration.
- Protected cleanup independently restores the prior Zero IP and closes Akash.

## Security wording

Say:

- dedicated ephemeral worker;
- bounded source payload;
- separate child process;
- hard timeout;
- scrubbed environment;
- held-out validation targets;
- direct bearer-authenticated path; and
- optional Pomerium-protected network boundary.

Do not say:

- hostile-code sandbox;
- multitenant isolation;
- ungameable evaluator;
- signed receipt; or
- production-hardened arbitrary-code execution.

The evaluator executes candidate Python in a child process on a dedicated
worker. Timeout and environment scrubbing are useful boundaries, but they are
not a hardened sandbox.

## Remaining operator-only steps

- [x] Exact branch: 60 tests, Ruff, formatting, compile, both SDL parses, and
      both design CLI themes pass.
- [ ] Run a paid Akash smoke only after accepting the displayed spend.
- [ ] Keep the terminal frame labeled “illustrative” unless replaced by a real
      receipt.
- [ ] Upload the final video and test public links without login.
- [ ] Select Akash and Pomerium on Devpost and submit.
