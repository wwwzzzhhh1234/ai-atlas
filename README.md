# AI-Atlas

Open-source discovery platform and benchmark for AI projects (agent skills, MCP servers, agents,
workflows, apps, governance tools, domain models), classified into a 10-sector / 50-field taxonomy.

Full plan: [`PROJECT_SPEC.md`](PROJECT_SPEC.md) · Status: [`docs/progress_log.md`](docs/progress_log.md)

## Setup (Windows PowerShell)

```powershell
git clone https://github.com/<you>/ai-atlas.git
cd ai-atlas
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env   # then edit .env and add your keys
```

## Check it works

```powershell
pytest
python -m atlas.taxonomy      # Taxonomy v3: 10 sectors / 50 fields
python -m atlas.db init       # creates data/atlas.db
python -m atlas.db info       # table row counts
```

## Collect candidates (M1)

```powershell
python -m atlas.collect.run                 # all sources (~1 h the first time; re-runs use the cache)
python -m atlas.collect.run --only github   # one source: github | mcp | hf
python -m atlas.collect.report              # rebuild reports/collection_report.md from the DB
python -m atlas.collect.spotcheck           # 20 random rows -> docs/m1_spotcheck.md for manual review
```

Every HTTP response is cached in `data/cache/http/` (not committed), so an interrupted run resumes
where it stopped. `GITHUB_TOKEN` in `.env` is used for the GitHub API when present.

## Gold set (M2)

```powershell
python -m atlas.evaluate.sample_gold        # (already done) stratified sample -> data/gold/gold_sample.csv
streamlit run app/label_gold.py             # labeling tool in the browser (read docs/annotation_guideline.md first)
python -m atlas.evaluate.gold status        # progress per annotator
python -m atlas.evaluate.agreement          # Cohen's kappa once a 2nd annotator labeled the overlap items
```

Labels are saved to `data/atlas.db` **and** `data/gold/gold_labels.csv`. Commit the CSV after each session
(`git add data/gold; git commit -m "gold labels"; git push`). On a new machine, the tool restores labels
from the CSV automatically (or run `python -m atlas.evaluate.gold sync`).

## Layout
- `config/` — taxonomy, data sources, models/prices/budget (edit these, not the code)
- `src/atlas/` — pipeline code (`collect`, `clean`, `enrich`, `embed`, `evaluate`, `analyze`)
- `app/` — Streamlit web app (M6)
- `data/` — database and snapshots (`raw/` and `cache/` are not committed)
- `docs/` — decisions, progress log, annotation guideline, eval report
