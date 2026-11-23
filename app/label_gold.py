"""Gold-set labeling tool (M2).

    streamlit run app/label_gold.py

Shows one sampled project at a time; the annotator picks asset type, primary sector/field and up to
three secondary fields. Every save goes to the gold_labels table and to data/gold/gold_labels.csv.
Follow docs/annotation_guideline.md. Do not look at any LLM labels while annotating.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from atlas import db
from atlas.data import load_candidates
from atlas.evaluate import gold
from atlas.paths import DB_PATH
from atlas.schema import AssetType, GoldLabel
from atlas.taxonomy import OTHER_ID, load_taxonomy

ASSET_HELP = {
    "skill": "Agent Skill (SKILL.md) or tool/API connector for an agent",
    "mcp": "Model Context Protocol server (or MCP client/SDK)",
    "agent": "Agent framework or a ready-made autonomous agent",
    "workflow": "Automation workflow template (n8n, Dify, LangGraph template...)",
    "app": "End-to-end AI application / copilot a user runs",
    "governance": "Guardrails, sandboxing, permission auditing, red-teaming, eval benchmarks",
    "model": "Fine-tuned / domain model, or context assets (prompt / rule libraries)",
    "resource": "NOT a project: awesome-list, tutorial, course, paper-only code",
}

st.set_page_config(page_title="AI-Atlas gold labeling", layout="wide")
NOT_AI = "[NOT-AI]"
TAX = load_taxonomy()


@st.cache_data
def load_items() -> pd.DataFrame:
    sample = gold.load_sample()
    cand = load_candidates(with_readme=True)
    return sample[["order", "id", "stratum", "overlap"]].merge(cand, on="id", how="left").sort_values("order")


@st.cache_resource
def prepare_db() -> bool:
    db.init_db(DB_PATH)
    gold.ensure_projects(DB_PATH, gold.load_sample()["id"].tolist())
    gold.import_csv()          # restore labels committed to git (no-op when already present)
    return True


def sector_label(sid: str) -> str:
    return f"{sid} · {TAX.name_of(sid)}"


def field_options(sector: str) -> list[str]:
    if sector == OTHER_ID:
        return [OTHER_ID]
    return [f.id for s in TAX.sectors if s.id == sector for f in s.fields]


def show_card(row: pd.Series) -> None:
    pop = f"⭐ {int(row.stars):,}" if pd.notna(row.stars) else (f"♥ {int(row.likes):,}" if pd.notna(row.likes) else "")
    st.markdown(f"### [{row['name']}]({row.url})  \n`{row.id}` · {pop} · {row.language or ''} · "
                f"license: {row.license_spdx or 'n/a'}")
    st.write(row.description if isinstance(row.description, str) else "_(no description)_")
    topics = list(row.topics) if row.topics is not None else []
    if topics:
        st.caption("Topics: " + ", ".join(topics[:20]))
    st.caption(f"Sample stratum: {row.stratum} (sampling only — not a label hint)")
    with st.expander("README excerpt (internal, cleaned)", expanded=True):
        st.text(str(row.readme_excerpt)[:6000] if isinstance(row.readme_excerpt, str) else "(none)")


def label_form(row: pd.Series, annotator: str, existing: dict | None) -> None:
    ex = existing or {}
    sectors = [s.id for s in TAX.sectors] + [OTHER_ID]
    types = [t.value for t in AssetType]
    asset = st.radio("Asset type", types, index=types.index(ex.get("asset_type", "app")),
                     format_func=lambda t: f"{t} — {ASSET_HELP[t]}", key=f"asset_{row.id}")
    sector = st.selectbox("Primary sector", sectors, format_func=sector_label, key=f"sector_{row.id}",
                          index=sectors.index(ex["sector_primary"]) if ex.get("sector_primary") in sectors else 0)
    fields = field_options(sector)
    field = st.selectbox("Primary field", fields, format_func=sector_label, key=f"field_{row.id}_{sector}",
                         index=fields.index(ex["field_primary"]) if ex.get("field_primary") in fields else 0)
    all_fields = [f.id for f in TAX.fields if f.id != field]
    secondary = st.multiselect("Secondary fields (0–3, any sector)", all_fields, max_selections=3,
                               default=[f for f in ex.get("fields_secondary", []) if f in all_fields],
                               format_func=sector_label, key=f"sec_{row.id}_{field}")
    old_notes = ex.get("notes") or ""
    not_ai = st.checkbox("Not an AI project (no AI/ML component at all)", value=old_notes.startswith(NOT_AI),
                         key=f"notai_{row.id}")
    notes = st.text_area("Notes (doubts, tie-break rule used, gap:foundation / gap:library)",
                         value=old_notes.removeprefix(NOT_AI).strip(), key=f"notes_{row.id}")
    notes = f"{NOT_AI} {notes}".strip() if not_ai else notes
    if st.button("💾 Save & next", type="primary", key=f"save_{row.id}"):
        try:
            label = GoldLabel(project_id=row.id, annotator=annotator, asset_type=asset, sector_primary=sector,
                              field_primary=field, fields_secondary=secondary, notes=notes or None)
        except ValidationError as e:
            st.error(f"Invalid label: {e.errors()[0]['msg']}")
            return
        gold.save_label(label)
        st.session_state.pos = st.session_state.pos + 1
        st.rerun()


def main() -> None:
    prepare_db()
    items = load_items()
    st.sidebar.title("AI-Atlas · gold set")
    annotator = st.sidebar.text_input("Annotator ID", value="zw", help="Use the same ID every session").strip()
    only_overlap = st.sidebar.checkbox("Only overlap items (annotator 2)", value=False)
    if only_overlap:
        items = items[items["overlap"]]
    items = items.reset_index(drop=True)
    labels = gold.read_labels()
    mine = labels[labels["annotator"] == annotator].set_index("project_id")
    done = items["id"].isin(mine.index)
    st.sidebar.progress(done.mean() if len(items) else 0.0, text=f"{int(done.sum())} / {len(items)} labeled")
    view = (annotator, only_overlap)
    if st.session_state.get("view") != view:     # new annotator or filter -> jump to first unlabeled item
        st.session_state.view = view
        st.session_state.pop("pos", None)
    if "pos" not in st.session_state:
        st.session_state.pos = int((~done).idxmax()) if (~done).any() else 0
    st.session_state.pos = max(0, min(st.session_state.pos, len(items) - 1))
    c1, c2, c3 = st.sidebar.columns(3)
    if c1.button("◀ Prev"):
        st.session_state.pos -= 1
        st.rerun()
    if c2.button("Next ▶"):
        st.session_state.pos += 1
        st.rerun()
    if c3.button("Next unlabeled") and (~done).any():
        st.session_state.pos = int((~done).idxmax())
        st.rerun()
    st.sidebar.markdown("Guideline: `docs/annotation_guideline.md`")
    if done.all() and len(items):
        st.success("All items in this view are labeled. Thank you!")
    row = items.iloc[st.session_state.pos]
    st.caption(f"Item {st.session_state.pos + 1} / {len(items)}" + (" · ✅ already labeled" if row.id in mine.index else ""))
    left, right = st.columns([3, 2])
    with left:
        show_card(row)
    with right:
        existing = mine.loc[row.id].to_dict() if row.id in mine.index else None
        label_form(row, annotator, existing)


main()
