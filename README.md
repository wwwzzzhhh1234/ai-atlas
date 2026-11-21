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

## Layout
- `config/` — taxonomy, data sources, models/prices/budget (edit these, not the code)
- `src/atlas/` — pipeline code (`collect`, `clean`, `enrich`, `embed`, `evaluate`, `analyze`)
- `app/` — Streamlit web app (M6)
- `data/` — database and snapshots (`raw/` and `cache/` are not committed)
- `docs/` — decisions, progress log, annotation guideline, eval report
