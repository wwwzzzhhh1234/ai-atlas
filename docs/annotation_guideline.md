# Annotation guideline (skeleton — completed in M2)

Applies to the gold-standard set (~250 projects). Labels follow `config/taxonomy.yaml` (v3).

## 1. What you label per project
| Field | Rule |
|---|---|
| `asset_type` | Exactly one of: skill, mcp, agent, workflow, app, governance, model, resource |
| `sector_primary` | One sector ID (S01–S10) or OTHER |
| `field_primary` | One field ID inside `sector_primary` (or OTHER if sector is OTHER) |
| `fields_secondary` | 0–3 other field IDs, any sector, never repeating the primary |
| `notes` | Free text: doubts, tie-break used |

## 2. Asset-type definitions
_TODO (M2): one paragraph + 2 real examples per type; boundary cases (agent vs app, skill vs mcp,
governance vs model, when something is a `resource`)._

## 3. Choosing the primary sector / field
_TODO (M2): "who is the end user / which business task" rule; generic horizontal tools
(e.g. a general agent framework) → S06 unless clearly domain-specific; when to use OTHER._

## 4. Tie-break rules
_TODO (M2)._

## 5. Examples per sector
_TODO (M2): 2–3 real projects per sector with the label and a one-line reason._

## 6. Process
- Annotator 1: Zhiheng Wang (all items). Annotator 2: TBD (≥ 50 overlap items) → Cohen's kappa.
- Label independently; do not look at LLM labels first.
