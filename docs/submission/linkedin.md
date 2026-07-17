# LinkedIn launch post

## Primary post

Most coding-agent loops treat a plausible diff as progress.

ML does not.

A cleaner model can still lose on held-out data. A longer context window can
still repeat last week's failed idea. And an autonomous loop that holds its own
evaluator credentials is being asked to grade its own work.

So I built **One More Run** around two nested loops:

→ The inner loop gives Codex a bounded workspace, measured history, and
graph-backed recall. It can rewrite the complete training program—features,
architecture, loss, optimizer, schedule—then explicitly mark a candidate ready.

→ The outer loop spends the scarce resource. It sends the content-addressed
candidate to a fixed evaluator on an Akash GPU, verifies the candidate and
evaluator identities, and returns one decision: `KEEP`, `REJECT`, or `CRASH`.

Only measured improvements become the next champion.

The evidence survives the run. After the JSONL receipt is durable, Hindsight
retains the hypothesis, candidate, metric, and decision across entities,
relationships, and time. The next campaign can recall relevant wins and
failures instead of rediscovering them.

The evaluator is private. Pomerium Zero is the only public Akash service and
enforces service identity before proxying to the worker. The worker still owns
its separate bearer token. Identity at the edge; application auth at the
service.

The interesting part is not that an agent can edit code. It is the system
around the edit: readiness, measurement, receipts, memory, spend, identity, and
cleanup.

Built for the Loop Engineering Hackathon with Codex, Akash Network, Pomerium
Zero, Hindsight, PyTorch, Rich, and uv.

Source: https://github.com/drukpa1455/one-more-run

#LoopEngineering #AutonomousAgents #MLOps #AkashNetwork #Pomerium

## Short alternate

An agent can change the program. Only an experiment can change the champion.

**One More Run** nests a bounded Codex edit loop inside an empirical GPU loop:

- Codex recalls prior evidence and evolves the complete training program.
- Akash measures a content-addressed candidate against a fixed evaluator.
- The controller accepts only `KEEP`, `REJECT`, or `CRASH` receipts.
- Hindsight carries measured evidence across campaigns.
- Pomerium Zero protects the private evaluator with service identity.

The result is an autonomous research loop that can improve, remember, and
explain exactly why the champion changed.

https://github.com/drukpa1455/one-more-run

#LoopEngineering #AutonomousAgents #MLOps

## Posting notes

- Attach the eight-page PDF from [`carousel.md`](carousel.md).
- Pick one complete theme: Opal Light or Garnet Dark.
- Put the repository link in the post body and first comment if LinkedIn reduces
  its reach.
- Tag the event, Akash, Pomerium, and Hindsight only where the exact company
  page resolves.
- Do not add benchmark claims from the illustrative terminal frame.
