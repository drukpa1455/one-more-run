# Architecture

One More Run has one rule: an agent may change the program, but only a fixed
evaluation may change the champion.

```mermaid
sequenceDiagram
    participant O as One More Run
    participant C as Codex
    participant P as Pomerium (optional)
    participant W as Akash worker
    participant E as Hidden evaluator

    O->>W: evaluate baseline bundle + SHA-256
    W->>E: fixed data, seed, metric, timeout
    E-->>O: metric + evaluator receipt
    loop until run, time, or spend limit
        O->>C: objective + champion + measured history
        loop bounded edit turns
            C->>C: inspect, edit, static check
        end
        C-->>O: ready candidate + hypothesis
        alt direct
            O->>W: candidate + worker bearer token
        else --pomerium
            O->>P: candidate + service identity
            P->>W: private route + worker bearer token
        end
        W->>E: isolated fixed evaluation
        E-->>O: metric + source/evaluator receipt
        O->>O: keep improvement; otherwise restore champion
    end
    O->>O: close Akash deployment
```

## Ownership

| Owner | Holds | Never receives |
|---|---|---|
| One More Run | budgets, champion, ledger, Akash credential | hidden targets |
| Codex | objective, candidate files, measured history | Akash key, worker token, hidden targets |
| Pomerium | optional route and service identity | Codex key, Akash key, candidate environment |
| Worker | bearer token, source bundle, fixed evaluator | Codex key, Akash key |
| Candidate process | training tensors and candidate code | controller credentials, validation targets |

## Durable facts

- The controller alone appends `experiments.jsonl`.
- Every candidate is normalized and content-addressed.
- A finish event is accepted only when candidate and evaluator identities match
  the corresponding start event.
- `KEEP`, `REJECT`, and `CRASH` all remain visible.
- Candidate code cannot change the hidden targets, metric, seed, timeout, or
  campaign limits.
- Cleanup owns both deployment closure and optional Pomerium route restoration.

The local numeric adapter, direct Akash adapter, and Pomerium-protected Akash
adapter all implement the same JSONL protocol. Compute is replaceable; evidence
semantics are not.
