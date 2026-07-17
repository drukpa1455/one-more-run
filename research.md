# Research objective

Minimize hidden validation mean squared error by improving the complete training
program in the candidate workspace.

## Search space

- Model architecture
- Loss function
- Optimizer and schedule
- Training algorithm and data transformations

## Constraints

- Evaluate one candidate at a time.
- Edit only the candidate workspace; keep `train.py`'s callable contract.
- Keep the hidden evaluator, validation data, and random seed fixed.
- Choose each next candidate from observed results.
- Stop at the CLI's experiment, time, or spend limit.
