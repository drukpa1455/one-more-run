# One More Run design system

One More Run has two complete presentation modes. Build every asset in both;
never alternate modes inside one carousel or deck.

The tokens are adapted from the Reia/Agos `Opal` and `Garnet` themes. The
identity, logo, layout, and copy remain One More Run's.

## Type

- Primary and monospace: **Atkinson Hyperlegible Mono**.
- Fallback: `ui-monospace, SFMono-Regular, Menlo, monospace`.
- Use one family. Hierarchy comes from size, weight, spacing, and color.
- Use tabular numerals for metrics, hashes, time, and cost.

## Opal Light

| Role | Value |
|---|---|
| Canvas | `#f4f7f7` |
| Surface | `#dde7e8` |
| Elevated surface | `#f7f9f9` |
| Text | `#1d2425` |
| Muted text | `#4f7178` |
| Border | `#c6d9de` |
| Signal / primary | `#2f7880` |
| Keep / success | `#1b7108` |
| Crash / warning | `#984f00` |
| Reject / error | `#b83233` |
| Information | `#0067a1` |

Opal is the daylight, analytical version. It should feel like a research
notebook with precise instrumentation, not a generic white SaaS deck.

## Garnet Dark

| Role | Value |
|---|---|
| Canvas | `#2c2122` |
| Surface | `#281e1f` |
| Elevated surface | `#262018` |
| Text | `#f8f8f2` |
| Muted text | `#a97079` |
| Border | `#4d4130` |
| Signal / primary | `#ffd7a0` |
| Keep / success | `#7de972` |
| Crash / warning | `#e6e370` |
| Reject / error | `#e67070` |
| Information | `#75ece0` |

Garnet is the low-light, operator-console version. Preserve the warm canvas;
do not replace it with black, navy, neon gradients, or glass effects.

## Semantic mapping

- Primary: active loop, selected node, current candidate, title rule.
- Success: measured improvement and accepted champion only.
- Error: measured regression and rejected candidate only.
- Warning: crash, timeout, budget edge, or human confirmation.
- Information: external compute, identity, memory, and receipts.
- Muted: inactive branches, previous candidates, annotations, and edge labels.

Color never carries meaning alone. Pair it with `KEEP`, `REJECT`, `CRASH`, a
shape, or a line pattern.

## Diagram grammar

- Rounded rectangles: bounded processes.
- Circles: immutable identities such as candidate and evaluator hashes.
- Cylinders: durable or derived stores.
- Solid arrow: data or authority crossing now.
- Dotted arrow: recall, derivation, or asynchronous retention.
- Double border: trust boundary.
- One diagram, one causal path, one highlighted edge.

Use thin 1.5–2 px rules, 8 px corner radii, and generous negative space. Avoid
decorative AI brains, robots, clouds, glowing orbs, stock imagery, and fake
code wallpaper.

## Output modes

Render identical layouts twice:

1. `opal/` — every page uses Opal Light.
2. `garnet/` — every page uses Garnet Dark.

Do not create a third hybrid set. Do not put an Opal content slide between
Garnet slides. Terminal frames, diagrams, cover, and end card all inherit the
selected mode.
