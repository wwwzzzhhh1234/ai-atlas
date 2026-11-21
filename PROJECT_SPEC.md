# AI-Atlas — Project Spec & Implementation Plan

> **For AI agents (Claude Code, Gemini):** This file is the single source of truth for this project.
> Read it fully before doing anything. Work one milestone at a time (Section 9), meet every
> "Done when" check before moving on, and follow the rules in Section 2.
> When this file and a chat instruction conflict, ask the human.

- **Project lead / developer:** Zhiheng Wang (undergraduate, Data Science, Penn State)
- **Advisor:** Prof. Dhananjay Singh
- **Spec version:** v1 — 2026-11-21
- **Language:** All code, comments, data fields, prompts, UI text and docs are in **English**.

---

## 1. What we are building (one paragraph)

AI-Atlas is a public, open-source discovery platform that **collects high-quality AI projects**
(agent skills, MCP servers, agents, workflows, AI applications, governance/eval tools, domain models)
from GitHub and other sources, **classifies them into a 10-sector / 50-field industry taxonomy**,
explains each project in **two views** (plain-English business view + developer view), and **links
related projects** (similar alternatives + complementary tools). The same pipeline also produces an
**academic deliverable**: a taxonomy + labeled dataset + human-annotated gold-standard benchmark
for evaluating LLM classification, plus a landscape analysis of where open-source AI is concentrated.

Target scale: ~10,000 projects. Built in stages; each stage must work end to end before scaling.

### Decisions already confirmed with the advisor
| Topic | Decision |
|---|---|
| Positioning | Long-term public platform **and** an academic deliverable (taxonomy paper + human-annotated benchmark) |
| Data scope | Multi-source (GitHub primary + MCP registries + Hugging Face; workflow libraries later). Date/star thresholds are **flexible guidelines**, relaxed for niche domains |
| Taxonomy | Two tiers. Advisor asked to add Smart City / Intelligent Transportation and Entrepreneur / Startup Pipeline → now 10 sectors / 50 fields (Section 5) |
| V1 scope | Directory browsing + dual-view cards + related-project grouping + fuzzy semantic search. Graph visualizations and chatbot are later |
| Validation | Manually labeled gold-standard sample (~200–300 projects), precision / recall / F1, plus automated LLM cross-checks and spot checks |
| Resources | Advisor has small funds; we tell him **what** we need and **when**. Regular progress updates expected |

---

## 2. Rules for AI agents (read before every session)

1. **One milestone at a time.** Find the current milestone in `docs/progress_log.md`. Do not start
   the next milestone until every "Done when" item of the current one is true.
2. **Never invent data.** No made-up star counts, licenses, URLs, project names, or metrics. If a value
   cannot be fetched, store `null` and log why.
3. **Stop and ask the human before:** spending money beyond the cap in `config/models.yaml`;
   changing the taxonomy; deleting data in `data/`; publishing anything publicly; changing the
   database schema after Milestone 1.
4. **Secrets:** API keys live only in `.env` (gitignored). Never print, log or commit them.
5. **Be polite to APIs:** respect rate limits, use backoff, cache every raw response so nothing is
   fetched or paid for twice. All scripts must be **idempotent** and **resumable**.
6. **Small steps:** make small, testable changes. Run tests after each change. Keep functions short.
7. **Record decisions** in `docs/decisions.md` (date, decision, reason) and progress in
   `docs/progress_log.md` at the end of every session.
8. **Configuration over code:** thresholds, queries, model IDs, prices and prompt versions live in
   `config/*.yaml`, not hard-coded.
9. **Windows environment:** the developer's laptop runs Windows. Prefer cross-platform Python;
   use `pathlib`; give PowerShell commands when showing shell commands.
10. **Licenses & terms:** use official APIs where available; follow each platform's terms; store our
    own summaries plus links, never republish full README text in the public site.

---

## 3. Roles: who does what

| Who | Role |
|---|---|
| **Claude Code** | Main builder: writes and runs code, tests, debugging, data pipeline, Streamlit app, analysis notebooks |
| **Gemini 4 Neon (API)** | Candidate **labeling model** inside the pipeline (classification, dual-view summaries, input/output extraction). Compared against a cheaper model on the gold set before the full run |
| **Gemini 4 Neon (app / AI Studio)** | Reviewer: second opinion on prompts, annotation guideline, taxonomy edge cases, paper drafts |
| **Zhiheng (human)** | Approves decisions, labels the gold set (annotator 1), reviews low-confidence labels, sends advisor updates |
| **Prof. Singh** | Strategic direction, funding, taxonomy review; possibly annotator 2 (to confirm) |

Model notes (verify before use):
- Gemini 4 Neon launched 2026-11-18; reported launch API price **$3 / 1M input tokens, $15 / 1M output
  tokens**, 1M-token context, multiple thinking levels. **Check the exact model ID and current price in
  Google AI Studio** and put them in `config/models.yaml`.
- Gemini 4 Hydrogen is the faster, cheaper sibling. Its price is not recorded here — look it up.
- Thinking tokens are billed as output. Use the **lowest thinking level** that meets the quality bar.

---

## 4. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Data science friendly |
| Env | `venv` + `requirements.txt` (or `uv`) | Simple on Windows |
| HTTP / APIs | `httpx` (or `requests`), `PyGithub` optional, GitHub GraphQL for batch metadata | |
| HF | `huggingface_hub` | Official client |
| LLM | `google-genai` SDK | Gemini API |
| Validation | `pydantic` v2 | Enforce JSON output schema |
| Storage | **SQLite** (`data/atlas.db`) + Parquet snapshots in `data/processed/` | Zero setup; 10k rows is small |
| Embeddings | Local `sentence-transformers` model (e.g. a small BGE / MiniLM model) — free; switch to an API model only if quality is poor | No cost |
| Vector search | NumPy cosine similarity or FAISS (10k vectors — no vector DB needed for MVP) | Simple |
| Analysis | pandas, matplotlib/plotly, scikit-learn (metrics, Cohen's kappa), optional HDBSCAN | |
| Web MVP | **Streamlit** (deploy on Streamlit Community Cloud free tier) | Fastest path to a usable site |
| Scheduling (later) | GitHub Actions cron | Daily sync in Stage B |
| Tests | `pytest` | |

---

## 5. Taxonomy v3 (10 sectors / 50 fields) — copy into `config/taxonomy.yaml`

Rules: every project gets **one primary sector + one primary field**, and **0–3 secondary fields**.
Use `OTHER` only when nothing fits. Sectors S09 and S10 are newly added at the advisor's request;
the exact meaning of S10 ("startup pipeline") still needs advisor confirmation (Section 12).

```yaml
version: 3
sectors:
  - id: S01
    name: Healthcare & Life Sciences
    fields:
      - {id: S01.1, name: Clinical Decision & Diagnostics}
      - {id: S01.2, name: Medical Imaging}
      - {id: S01.3, name: Drug Discovery & Biotech}
      - {id: S01.4, name: Mental Health & Wellness}
      - {id: S01.5, name: Healthcare Admin & EHR Automation}
  - id: S02
    name: Agriculture, Energy & Climate
    fields:
      - {id: S02.1, name: Precision Agriculture & Crop Vision}
      - {id: S02.2, name: Climate & Environmental Modeling}
      - {id: S02.3, name: Energy Grid & CleanTech}
      - {id: S02.4, name: Food Supply Chain}
  - id: S03
    name: Enterprise & Operations
    fields:
      - {id: S03.1, name: Customer Support & CRM}
      - {id: S03.2, name: Sales & Marketing Automation}
      - {id: S03.3, name: HR & Recruiting}
      - {id: S03.4, name: Supply Chain & Logistics}
      - {id: S03.5, name: Internal Knowledge Base (Enterprise RAG)}
      - {id: S03.6, name: E-Commerce & Retail}
  - id: S04
    name: Automation, Robotics & Hardware
    fields:
      - {id: S04.1, name: Embodied AI & Robotics Control}
      - {id: S04.2, name: Industrial Manufacturing & QA}
      - {id: S04.3, name: IoT & Edge AI}
      - {id: S04.4, name: Drones & Aerial Robotics}
      - {id: S04.5, name: Browser & OS Desktop Automation}
  - id: S05
    name: Finance, Legal & Governance
    fields:
      - {id: S05.1, name: Financial Analysis & Quant}
      - {id: S05.2, name: Accounting & Tax Automation}
      - {id: S05.3, name: Legal Tech & Contract Review}
      - {id: S05.4, name: Agentic Governance, Safety & Compliance}
      - {id: S05.5, name: Cybersecurity & Red-Teaming}
  - id: S06
    name: Software, Data & DevTools
    fields:
      - {id: S06.1, name: Coding Agents & IDE Skills}
      - {id: S06.2, name: Data Engineering & Analytics}
      - {id: S06.3, name: DevOps & Cloud Automation}
      - {id: S06.4, name: Testing & QA Automation}
      - {id: S06.5, name: UI/UX & Frontend Generation}
  - id: S07
    name: Science, Research & Education
    fields:
      - {id: S07.1, name: Scientific Literature & Research Agents}
      - {id: S07.2, name: Mathematics & Physics Modeling}
      - {id: S07.3, name: Materials & Chemistry}
      - {id: S07.4, name: Personalized Tutoring & EdTech}
      - {id: S07.5, name: Academic Writing & Translation}
  - id: S08
    name: Media, Creative & Everyday Life
    fields:
      - {id: S08.1, name: Video & Audio Generation}
      - {id: S08.2, name: Graphic Design & 3D Modeling}
      - {id: S08.3, name: Gaming & Interactive NPCs}
      - {id: S08.4, name: Personal Productivity & Life Assistants}
      - {id: S08.5, name: Travel & Real Estate}
  - id: S09
    name: Smart City & Intelligent Transportation
    fields:
      - {id: S09.1, name: Autonomous Driving & Intelligent Vehicles}
      - {id: S09.2, name: Traffic Management & Signal Control}
      - {id: S09.3, name: Public Transit & Mobility Services}
      - {id: S09.4, name: Urban Planning & Digital Twins}
      - {id: S09.5, name: Smart Infrastructure & Public Safety}
  - id: S10
    name: Entrepreneurship & Startup Pipeline
    fields:
      - {id: S10.1, name: Idea Validation & Market Research}
      - {id: S10.2, name: Business Planning & Pitch Decks}
      - {id: S10.3, name: No-Code MVP & Product Building}
      - {id: S10.4, name: Fundraising & Investor Relations}
      - {id: S10.5, name: Go-to-Market & Early Growth}
other: {id: OTHER, name: Other / Unclear}
```

### Asset types (one per project)
| `asset_type` | Meaning | Examples |
|---|---|---|
| `skill` | Agent Skills (SKILL.md), tool/API connectors | a SKILL.md pack |
| `mcp` | Model Context Protocol servers | an MCP server for a CRM |
| `agent` | Single/multi-agent frameworks and ready agents | an agent framework |
| `workflow` | Automation workflow templates (n8n, Dify, LangGraph templates) | an invoice workflow |
| `app` | End-to-end AI applications / copilots | a clinical notes assistant |
| `governance` | Guardrails, sandboxing, permission auditing, red-teaming, eval benchmarks | a guardrail library |
| `model` | Fine-tuned domain models and context assets (prompt / rule libraries) | a finance LLM |
| `resource` | **Excluded from the directory:** awesome-lists, tutorials, courses, paper-only code | an awesome-list |

---

## 6. Data model

### Table `projects` (one row per unique project)
| Field | Type | Notes |
|---|---|---|
| `id` | text PK | Canonical key: `gh:owner/repo` (lowercase); `hf:owner/name`; `mcp:<registry name>` when no repo |
| `name`, `url`, `description` | text | From source |
| `sources` | json list | e.g. `["github","mcp_registry"]` after de-dup merge |
| `stars`, `forks` | int | GitHub; `null` if not applicable |
| `created_at`, `pushed_at` | date | GitHub |
| `license_spdx` | text | e.g. `MIT`, `Apache-2.0`, `null` |
| `language`, `topics` | text / json | |
| `is_fork`, `is_archived`, `has_readme` | bool | Filters |
| `readme_excerpt` | text | Cleaned, truncated (badges/HTML stripped). **Internal only, never shown publicly** |
| `collected_at` | datetime | |

### Table `labels` (one row per project × model × prompt version)
| Field | Type | Notes |
|---|---|---|
| `project_id`, `model`, `prompt_version` | text | Composite key |
| `asset_type` | enum | Section 5 |
| `sector_primary`, `field_primary` | text | Taxonomy IDs |
| `fields_secondary` | json list | 0–3 IDs |
| `business_summary` | text | Plain English, ≤ 60 words, no jargon: what it does + which business task it helps |
| `developer_summary` | text | ≤ 60 words: stack, how it runs |
| `use_cases` | json list | 2–3 short items |
| `non_tech_usability` | int 1–5 | 5 = usable without coding |
| `deploy_difficulty` | int 1–5 | 1 = one-click / hosted, 5 = needs GPUs/infra expertise |
| `inputs`, `outputs` | json list | Controlled vocabulary tags (defined in M3), e.g. `pdf`, `invoice`, `spreadsheet`, `email`, `image`, `text`, `database`, `api` |
| `confidence` | float 0–1 | Model's self-reported confidence |
| `cost_usd`, `labeled_at` | float / datetime | For budget tracking |

### Other tables
- `gold_labels` (project_id, annotator, asset_type, sector_primary, field_primary, fields_secondary, notes)
- `embeddings` (project_id, model, vector blob) — or a `.npy` file + id index
- `related` (project_id, related_id, kind = `alternative` | `complement`, score)

---

## 7. Collection & inclusion rules

### Sources (in priority order)
1. **GitHub** — Search API, sliced by star ranges and date ranges so each query returns < 1,000
   results (the Search API caps results per query). Seeds:
   - Topics: `llm`, `ai-agent`, `ai-agents`, `agentic-ai`, `mcp`, `mcp-server`, `model-context-protocol`,
     `agent-skills`, `claude-skills`, `rag`, `langchain`, `langgraph`, `crewai`, `autogen`, `n8n`, `dify`,
     `generative-ai`, `llmops`, `guardrails`, `ai-safety` (extend in `config/sources.yaml`).
   - Sector keyword queries for niche domains (e.g. agriculture/crop, clinical/medical, traffic/autonomous
     driving, smart city, startup/pitch deck, governance/compliance) so small sectors are not missed.
   - Skill files: code search for `filename:SKILL.md` (code search has tighter rate limits).
   - Curated lists as seeds: parse repo links from lists such as `anthropics/skills`,
     `heilcheng/awesome-agent-skills`, `github/awesome-copilot`. Lists themselves get `asset_type=resource`.
   - Use GraphQL to fetch metadata in batches; fetch READMEs via REST.
2. **Official MCP Registry** — REST API at `registry.modelcontextprotocol.io` (cursor pagination; check the
   current API version in its docs). Merge with GitHub by repository URL.
3. **Hugging Face** — `huggingface_hub` for domain models and Spaces (sort by likes/downloads).
4. **Later (optional):** other MCP directories (Glama, PulseMCP, Smithery), workflow template libraries
   (n8n, Dify). Check API availability and terms first; ask the human before scraping anything.

### Inclusion defaults (all configurable in `config/sources.yaml`; tune after seeing data)
- Include if: AI-related AND not a fork AND not archived AND has a README of ≥ 200 characters.
- Freshness: `created_at >= 2025-01-01` **or** `pushed_at` within the last 12 months.
- Stars: `>= 100` by default; `>= 20` for results of niche-sector keyword queries
  (S02, S05.4, S09, S10). These numbers are starting guesses — report sector counts and revisit.
- De-duplicate by canonical `id`; merge `sources`.

---

## 8. LLM labeling pipeline

- **Input per project:** name, description, topics, language, stars, license, cleaned README excerpt
  (cap ~3,000 tokens).
- **Prompt:** versioned files in `src/atlas/enrich/prompts/label_vN.md`; includes the taxonomy (IDs + names)
  and asset-type definitions; asks for JSON matching the `labels` schema; low temperature.
- **Validation:** parse with pydantic; on invalid output retry ≤ 2 times; then mark `failed` and log.
- **Caching:** save every response to `data/cache/llm/<model>/<prompt_version>/<project_id>.json`;
  never re-call for a cached key.
- **Budget guard:** before any batch run, print an estimate (projects × avg tokens × price) and stop if
  above `max_usd_per_run` in `config/models.yaml`; track actual `cost_usd` per call.
- **Cost estimate (rough, to be replaced by measured numbers in M3):** ~4,500 input + ~500 output
  tokens per project → about $0.02 per project at Neon's reported price, i.e. ~$200 per 10,000 projects
  **before** thinking tokens. Measure the real number on the gold set.
- **Model choice:** run the gold set with Gemini 4 Neon **and** a cheaper model (e.g. Gemini 4 Hydrogen);
  pick the cheapest one that meets the quality bar. This comparison is also a result for the paper.
- **Cross-check:** a second model re-labels (a) a random 10% sample and (b) all items with
  `confidence < 0.6`; disagreements go to `data/review/queue.csv` for human review.

### Related projects
- **Alternatives:** cosine similarity on embeddings of `business_summary + description + field name`;
  top-5 neighbors, preferring the same primary field; keep pairs above a tuned threshold.
- **Complements:** project A's `outputs` overlap project B's `inputs` (and they are in related fields);
  rank by overlap + embedding similarity. Spot-check 30 pairs by hand.

---

## 9. Milestones (the implementation plan)

Suggested calendar assumes part-time work starting Mon 2026-11-23; shift weeks around finals and holidays.
Each milestone ends with a short update to the advisor (Section 10).

### M0 — Setup (Week 1, ~1–2 days)
Tasks
- Create GitHub repo `ai-atlas` with the structure in Section 11; add this file as `PROJECT_SPEC.md`.
- `.env.example` with `GITHUB_TOKEN`, `GEMINI_API_KEY`; `.gitignore` covers `.env`, `data/raw`, `data/cache`.
- `config/taxonomy.yaml` (Section 5), `config/sources.yaml`, `config/models.yaml` (model IDs, prices, cap).
- SQLite schema (Section 6) + `src/atlas/db.py`; pydantic models in `src/atlas/schema.py`.
- `docs/decisions.md`, `docs/progress_log.md`, `docs/annotation_guideline.md` (skeleton).
Done when
- [ ] `pytest` passes (schema + taxonomy loader tests).
- [ ] `python -m atlas.db init` creates an empty database.
- [ ] Taxonomy loader reports 10 sectors / 50 fields.

### M1 — Collection (Week 1–2)
Tasks
- GitHub collector (topic + keyword + sliced queries, GraphQL metadata, README fetch, backoff, caching).
- MCP Registry collector; Hugging Face collector.
- Cleaning: README cleanup, filters (Section 7), de-dup/merge.
- Report script: counts by source, by keyword group, stars histogram.
Done when
- [ ] `python -m atlas.collect.run` is resumable and re-running it costs no new API calls for cached items.
- [ ] `data/processed/candidates.parquet` exists; report in `docs/progress_log.md` with real counts.
- [ ] 20 random rows checked by hand for wrong merges or junk.

### M2 — Gold set (Week 2)
Tasks
- Stratified sample of ~250 candidates (by keyword group and rough asset type so small sectors appear).
- Finish `docs/annotation_guideline.md` (definitions, tie-break rules, examples per sector).
- Simple labeling tool (Streamlit page or CSV) → `gold_labels` table.
- Human labels all items (annotator 1); annotator 2 labels an overlap subset (≥ 50) if available.
Done when
- [ ] All sampled items labeled by annotator 1.
- [ ] Cohen's kappa computed on the overlap subset (or noted as pending if no annotator 2 yet).

### M3 — Labeling pipeline + evaluation (Week 2–3)
Tasks
- `llm_client.py` (google-genai, retries, cost tracking, cache), prompt `label_v1.md`, classifier.
- Define the controlled vocabulary for `inputs` / `outputs`.
- Run on the gold set with Gemini 4 Neon and the cheaper model; compute metrics; iterate prompt (≤ 3 versions).
- Measure real cost per project → write the resource request for the advisor.
Metrics: asset-type accuracy; primary-sector accuracy + macro-F1; primary-field accuracy + macro-F1;
micro P/R/F1 over all fields (primary + secondary); confusion matrix; error analysis notes.
Proposed quality bar (confirm with advisor): primary-sector macro-F1 ≥ 0.80 and asset-type accuracy ≥ 0.85.
Done when
- [ ] `docs/eval_report.md` with metrics per model and prompt version, cost per project, chosen model.
- [ ] Human approves the model choice and budget before M4.

### M4 — Full enrichment (Week 3–4)
Tasks
- Batch-label all candidates with the chosen model; cross-check (Section 8); human reviews the queue.
- Embeddings for all projects; alternatives + complements into `related`.
Done when
- [ ] Every included project has a valid label row (failures < 2% and listed).
- [ ] `related` table filled; 30 random pairs spot-checked and noted.
- [ ] Snapshot `data/processed/atlas_v1.parquet`.

### M5 — Landscape analysis (Week 4)
Tasks
- Notebook/script: projects by sector, field, asset type; growth by creation month; license mix;
  under-served fields; non-tech usability by sector.
Done when
- [ ] `reports/landscape/` with charts (PNG) and `docs/landscape_findings.md` (5–10 findings with numbers).

### M6 — Web MVP (Week 5–6)
Tasks
- Streamlit app: search box (semantic search over embeddings + keyword fallback), sector/field browsing,
  filters (sector, field, asset type, deploy difficulty, activity), project card with
  **Business view / Developer view** toggle, related projects, "AI-generated description" label and a
  "report an error" link.
- Deploy to Streamlit Community Cloud (ask the human before making it public).
Done when
- [ ] A non-technical test user can find a tool for "sort supplier invoices into Excel" in < 1 minute.
- [ ] App loads in < 5 s with the full dataset.

### M7 — Paper draft (Week 6–8, with advisor)
Outline: Introduction · Related work · Taxonomy design · Data collection · LLM labeling pipeline ·
Benchmark & evaluation · Landscape analysis · Platform · Limitations & ethics · Conclusion.
Done when
- [ ] Full draft in `paper/` sent to the advisor; venue decided by the advisor.

### M8 — Stage B: daily sync (after MVP)
- GitHub Actions cron: collect new/updated projects, label only new ones, update embeddings and related
  pairs incrementally, publish a new snapshot.

### Schedule at a glance
| Week (from 2026-11-23) | Milestones | Key output |
|---|---|---|
| 1 | M0, start M1 | Repo, configs, DB, first collector |
| 2 | M1 finish, M2, start M3 | Candidate pool, gold set labeled |
| 3 | M3 finish, start M4 | Eval report, chosen model, budget request |
| 4 | M4 finish, M5 | Labeled dataset v1, landscape charts |
| 5–6 | M6 | Public Streamlit MVP |
| 6–8 | M7 | Paper draft |
| After | M8 | Daily sync |

---

## 10. Advisor updates

Send at the end of each milestone (at least weekly) in the Teams chat:

```
AI-Atlas update — [date]
Done: [2–3 bullets]
Numbers: [N] collected · [N] labeled · gold-set macro-F1 [value] · spend so far $[value]
Next: [2–3 bullets]
Need from you: [decision / resource / feedback, or "nothing this time"]
```

---

## 11. Repository layout

```
ai-atlas/
├── PROJECT_SPEC.md          # this file
├── CLAUDE.md                # one line: @PROJECT_SPEC.md (Claude Code loads it automatically)
├── README.md
├── requirements.txt
├── .env.example             # GITHUB_TOKEN=, GEMINI_API_KEY=
├── config/
│   ├── taxonomy.yaml
│   ├── sources.yaml         # topics, keyword groups, thresholds, slices
│   └── models.yaml          # model IDs, prices, thinking level, max_usd_per_run
├── src/atlas/
│   ├── db.py  schema.py
│   ├── collect/   github.py  mcp_registry.py  huggingface.py  run.py
│   ├── clean/     readme.py  filters.py  dedup.py
│   ├── enrich/    llm_client.py  classify.py  prompts/label_v1.md
│   ├── embed/     embed.py  related.py
│   ├── evaluate/  sample_gold.py  metrics.py
│   └── analyze/   landscape.py
├── app/streamlit_app.py
├── data/       raw/  cache/  processed/  review/   (raw + cache gitignored)
├── docs/       decisions.md  progress_log.md  annotation_guideline.md  eval_report.md
├── reports/
├── paper/
└── tests/
```

---

## 12. Open questions (do not assume answers — ask the human)

- [ ] S10 "Entrepreneur / startup pipeline": a category of AI tools for founders (current assumption), or a platform feature?
- [ ] Annotator 2 for the gold set: Prof. Singh or another student?
- [ ] Budget cap and how to request/spend advisor funds.
- [ ] Exact Gemini model IDs and current prices (check Google AI Studio).
- [ ] Whether to include non-English repositories (currently: include, summaries in English).
- [ ] Authorship order and course credit for the paper.

---

## 13. How to start a session

**Claude Code — first session prompt:**
```
Read PROJECT_SPEC.md completely. We are starting Milestone M0.
Propose the file list you will create, then build it step by step, running tests as you go.
Stop when every "Done when" box of M0 is checked, update docs/progress_log.md, and summarize.
```

**Claude Code — later sessions:**
```
Read PROJECT_SPEC.md and docs/progress_log.md. Continue the current milestone.
Follow the rules in Section 2. Stop and ask me at any checkpoint listed there.
```

**Gemini 4 Neon (review use):**
```
Here is PROJECT_SPEC.md and [the prompt / guideline / draft]. Review it against the spec:
list problems, ambiguities and concrete improvements. Do not rewrite the whole thing.
```
