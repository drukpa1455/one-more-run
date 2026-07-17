# Research objective

Minimize validation mean squared error for the fixed linear-regression evaluator.

## Search space

- Learning rate: `0.00001` to `1.0`
- Momentum: `0.0` to `0.99`
- Training steps: `1` to `500`

## Constraints

- Evaluate one candidate at a time.
- Keep the evaluator, data, and random seed fixed.
- Choose each next candidate from observed results.
- Stop at the CLI's experiment, time, or spend limit.
