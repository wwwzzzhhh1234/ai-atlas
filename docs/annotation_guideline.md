# Annotation guideline — AI-Atlas gold set (v1, 2026-11-23)

Applies to the gold-standard sample (`data/gold/gold_sample.csv`, 250 projects) labeled with the tool
`streamlit run app/label_gold.py`. Labels follow `config/taxonomy.yaml` (v3: 10 sectors / 50 fields).
Examples below are real projects from our candidate pool.

**Golden rules**
1. Label what the project **is and is for**, from its README, description and topics. Open the repo link
   when the excerpt is unclear. Do not guess from the name alone.
2. Work independently. Never look at LLM labels or another annotator's labels first.
3. Aim for ~1–2 minutes per item. If still unsure after ~3 minutes: pick the best option, say why in Notes.
4. The "sample stratum" shown in the tool is how the item was sampled — **it is not a label hint**.

## 1. What you label

| Field | Rule |
|---|---|
| Asset type | Exactly one (Section 2) |
| Primary sector | One of S01–S10, or OTHER only when nothing fits |
| Primary field | One field inside the primary sector (OTHER if the sector is OTHER) |
| Secondary fields | 0–3 fields from any sector, only for a **substantial** second use. Never repeat the primary |
| Not an AI project | Tick if the project has no AI/ML component at all (e.g. a plain message broker). Still fill the other fields |
| Notes | Doubts, which tie-break rule you used, anything odd |

## 2. Asset types

| Type | Choose when… | Real examples |
|---|---|---|
| `skill` | Agent Skills (SKILL.md packs) or tool/API connectors meant to be loaded **into** an agent | `k-dense-ai/scientific-agent-skills`, `nexscope-ai/ecommerce-skills`, `shawnpang/startup-founder-skills` |
| `mcp` | Implements an MCP server (or an MCP client/SDK/gateway as its main deliverable) | `glips/figma-context-mcp`, `apify/apify-mcp-server`, `oaslananka/kicad-mcp-pro` |
| `agent` | An agent **framework** developers build with, or a ready autonomous agent that performs tasks by itself | `browser-use/browser-use`, `tauricresearch/tradingagents`, `vxcontrol/pentagi` |
| `workflow` | Automation workflow templates / flows for n8n, Dify, LangGraph etc. | `enescingoz/awesome-n8n-templates` is a *list* of templates → see `resource` rule; a repo that *is* a workflow template → `workflow` |
| `app` | An end-to-end application, platform or tool a user runs for a task — **including general ML libraries/toolkits** that are not agents, MCP, skills, governance or models (provisional, see Section 6) | `hkuds/deeptutor`, `abhinavxd/libredesk`, `canner/wrenai`, `microsoft/qlib` |
| `governance` | Guardrails, sandboxing, permission auditing, red-teaming / LLM security testing, evaluation benchmarks | `guardrails-ai/guardrails`, `promptfoo/promptfoo` |
| `model` | Trained / fine-tuned models (incl. HF model pages) and context assets: prompt / rule libraries | `hf:vidore/colpali`, `nvidia/cosmos`, `khazp/vibe-coding-prompt-template` |
| `resource` | Not a usable project: awesome-lists, tutorials, courses, workshops, paper-only code, collections of links | `szenergy/awesome-lidar`, `patchy631/ai-engineering-hub`, `microsoft/generative-ai-with-javascript` |

Tie-breaks for asset type
- **MCP vs skill:** ships an MCP server → `mcp`; ships SKILL.md files / prompts loaded by an agent → `skill`. Both → the one the README leads with.
- **Agent vs app:** the user gives a goal and the system plans/acts on its own (or it is a framework for that) → `agent`; the user drives a product UI for a defined task → `app`.
- **Governance vs app:** primary purpose is to *constrain, test, audit or evaluate* AI systems → `governance` (`promptfoo/promptfoo`), even if it is also an app. Security tools that attack *other* software (pentest agents such as `vxcontrol/pentagi`) are `agent`/`app`, sector S05.5.
- **Model vs app:** a HF **Space** is usually `app` (users run it); a HF **model** page is `model`.
- **Resource:** paper code that only reproduces experiments (no usable tool) and "awesome-…" lists are `resource`, even if popular. Still give the sector/field of the topic they cover.

## 3. Primary sector and field

**Main rule: classify by the end use — whose job or which industry the project serves — not by the
technology it uses.** A RAG chatbot for hospitals is S01, not S06.

| Situation | Rule |
|---|---|
| Domain-specific tool | Sector of that domain (e.g. `tauricresearch/tradingagents` → S05.1) |
| Horizontal developer tooling (agent frameworks, SDKs, coding agents, IDE plugins, test tools, deployment) | **S06** — pick the field by what the developer does: S06.1 coding, S06.2 data/analytics/RAG pipelines, S06.3 DevOps/cloud/LLM serving, S06.4 testing, S06.5 UI/frontend |
| Browser / desktop / OS automation agents | S04.5 (`browser-use/browser-use`) |
| General personal assistants, chat clients for individuals, note/productivity tools | S08.4 (`leon-ai/leon`) |
| Company-internal knowledge base / enterprise RAG products | S03.5 (`vectifyai/openkb`); a generic RAG *library* → S06.2 |
| LLM guardrails, AI safety, agent permissions, AI compliance | S05.4 |
| Cybersecurity (pentest, vuln detection) | S05.5 |
| Research-paper search / literature agents | S07.1 |
| General-purpose foundation models, LLM gateways, inference engines (no domain) | **Provisional:** S06.3 for serving/gateways/inference (`berriai/litellm`), S06.2 for embeddings/retrieval models (`hf:vidore/colpali`); a general chat LLM with no clear use → OTHER + note "general LLM" (see Section 6) |

Choosing the field inside a sector: the field that best names the **main task**. If two fit equally, take the
more specific one and put the other in secondary fields.

When to use OTHER: only when no sector fits (e.g. astrology tools such as `openfate-ai/openfate-mcp`,
general chat LLMs). Always add a note.

## 4. Secondary fields
- Add a secondary field only if the README presents it as a real use, not a passing mention.
- Do **not** add S06.x just because the project is software; add it when developers are a second target audience.
- Maximum 3; most projects need 0–1.

## 5. Examples per sector (real projects, suggested labels)

| Sector | Example → label |
|---|---|
| S01 Healthcare | `kaapana/kaapana` → app, S01.2 · `ssinder/bioinformatics-agent-skills` → skill, S01.3 · `guangshu100/wellhealth` (chronic-disease AI platform) → app, S01.1 (+S01.4) |
| S02 Agriculture/Energy/Climate | `spytensor/plants_disease_detection` → resource (competition code), S02.1 · `mila-iqia/climate-cooperation-competition` → app, S02.2 · `beckybams/renewable-energy-generation-forecasting` → app, S02.3 |
| S03 Enterprise | `abhinavxd/libredesk` → app, S03.1 · `frappe/crm` → app, S03.1 (+S03.2) · `speedyapply/jobspy` → app, S03.3 · `nexscope-ai/ecommerce-skills` → skill, S03.6 |
| S04 Automation/Robotics | `atsushisakai/pythonrobotics` → resource, S04.1 · `nvidia/cosmos` → model, S04.1 (+S09.1) · `alibaba/mnn` → app, S04.3 · `browser-use/browser-use` → agent, S04.5 |
| S05 Finance/Legal/Governance | `microsoft/qlib` → app, S05.1 · `vas3k/taxhacker` → app, S05.2 · `guardrails-ai/guardrails` → governance, S05.4 · `vxcontrol/pentagi` → agent, S05.5 |
| S06 Software/DevTools | `funador/claude-code-merge-queue` → app, S06.1 · `canner/wrenai` → app, S06.2 · `keploy/keploy` → app, S06.4 · `glips/figma-context-mcp` → mcp, S06.5 |
| S07 Science/Education | `startrail-org/leann` → app (check README), S07.1 or S06.2 · `deepchem/deepchem` → app, S07.3 · `hkuds/deeptutor` → app, S07.4 · `pdfmathtranslate/pdfmathtranslate` → app, S07.5 |
| S08 Media/Everyday | `hbai-ltd/toonflow-app` → app, S08.1 · `sandflow-ai/sand3d` → app, S08.2 · `akshitireddy/interactive-llm-powered-npcs` → app, S08.3 · `leon-ai/leon` → agent, S08.4 · `liketrek/trek` → app, S08.5 |
| S09 Smart City/Transport | `nv-tlabs/cosmos-drive-dreams` → model, S09.1 · `megvii-research/mctrack` → resource (paper code), S09.1 · `kircova/car-crash-detection` → app, S09.5 |
| S10 Startup | `cmn-labs/autogtm` → agent, S10.5 · `rameerez/claude-code-startup-skills` → skill, S10.3 · `shawnpang/startup-founder-skills` → skill, S10.1 |

These suggestions were written before annotation; if your reading of a README differs, trust the README and note it.

## 6. Known taxonomy gaps (to confirm with the advisor — do not change the taxonomy yourself)
1. **General-purpose foundation models & LLM infrastructure** have no field. Provisional rule in Section 3.
   Proposal for taxonomy v4: add field "S06.6 Foundation Models & LLM Infrastructure".
2. **Generic ML libraries/toolkits** have no asset type; provisionally `app`. Proposal: add asset type `library`.
3. **Non-AI projects** reached the pool (e.g. a message broker tagged `mcp`). Tick "Not an AI project"; we use
   these ticks to measure collection precision.

Track every item labeled under a provisional rule with a note (`gap:foundation`, `gap:library`) so it can be
relabeled automatically if the taxonomy changes.

## 7. Process
- Annotator 1: Zhiheng Wang (ID `zw`) labels all 250 items.
- Annotator 2 (TBD) ticks "Only overlap items" and labels the 60 overlap items → Cohen's kappa
  (`python -m atlas.evaluate.agreement`).
- Labels are saved on every click to `data/atlas.db` and `data/gold/gold_labels.csv`. Commit the CSV after each session.
