# Devpost copy

## One More Run

**Autoresearch on any compute.**

Most coding-agent loops treat a plausible diff as progress. ML does not. A
cleaner architecture can still lose on held-out data.

One More Run is a small control plane for bounded autonomous ML research. Codex
gets a few cheap edit turns to improve a complete modular training program. It
can change features, architecture, loss, optimizer, schedule, and module
boundaries, then explicitly marks the candidate ready. A fixed evaluator on an
ephemeral Akash GPU measures the content-addressed source bundle against hidden
validation targets. One More Run verifies the source and evaluator receipts,
records `KEEP`, `REJECT`, or `CRASH`, and advances only a measured improvement.

The controller owns the run, time, deposit, bid, credential, and cleanup
boundaries. Codex never receives Akash or worker credentials. The worker never
receives the Codex or Akash key. Candidate code runs one experiment at a time
with a bounded source payload, scrubbed environment, and hard timeout. An
optional Pomerium Zero path adds service identity in front of the private
worker while preserving independent application authentication.

The durable result is a tiny JSONL protocol, an append-only experiment ledger,
and a winning source bundle tied to its measurement. The same contract can
move from this compact nonlinear regression task to a real training repository
or another compute adapter.

One More Prompt starts the idea. **One More Run tests it.**

## Built with

Python, OpenAI Codex, Akash Network, Pomerium Zero, PyTorch, Docker, uv, Rich,
GitHub Actions, JSONL, SHA-256.

## Links

- Source: <https://github.com/drukpa1455/one-more-run>
- Demo video: add the public or unlisted video URL.

## Submission checklist

- Public repository opens in an incognito window.
- Three-minute video opens without login.
- The video and text distinguish the proven direct Akash path from optional
  Pomerium protection.
- The ledger contains no credentials or private data.
- Select Akash and Pomerium sponsor categories only if their required fields
  match the final demonstrated build.
