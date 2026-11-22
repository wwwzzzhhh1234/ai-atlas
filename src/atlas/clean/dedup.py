"""De-duplicate records by canonical id and merge their sources / provenance groups."""

from __future__ import annotations

from collections.abc import Iterable

_SET_FIELDS = ("sources", "groups")


def _has_metadata(rec: dict) -> bool:
    return rec.get("stars") is not None or rec.get("likes") is not None or rec.get("name") is not None


def merge(records: Iterable[dict]) -> dict[str, dict]:
    """Merge records sharing an id. Non-null scalar fields from metadata-bearing records win."""
    by_id: dict[str, list[dict]] = {}
    for r in records:
        by_id.setdefault(r["id"], []).append(r)
    merged = {}
    for rid, recs in by_id.items():
        recs = sorted(recs, key=lambda r: not _has_metadata(r))   # metadata-bearing first (stable)
        out = {k: (set(v) if k in _SET_FIELDS else v) for k, v in recs[0].items()}
        for r in recs[1:]:
            for k, v in r.items():
                if k in _SET_FIELDS:
                    out[k] |= set(v)
                elif out.get(k) in (None, [], "") and v not in (None, [], ""):
                    out[k] = v
        merged[rid] = out
    return merged
