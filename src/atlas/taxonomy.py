"""Taxonomy loader and lookups (config/taxonomy.yaml).

CLI:  python -m atlas.taxonomy      -> prints sector / field counts
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from atlas.config import load_yaml
from atlas.paths import CONFIG_DIR

OTHER_ID = "OTHER"
_SECTOR_RE = re.compile(r"^S\d{2}$")
_FIELD_RE = re.compile(r"^(S\d{2})\.\d+$")


@dataclass(frozen=True)
class Field:
    id: str
    name: str
    sector_id: str


@dataclass(frozen=True)
class Sector:
    id: str
    name: str
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class Taxonomy:
    version: int
    sectors: tuple[Sector, ...]
    other_name: str

    @property
    def fields(self) -> tuple[Field, ...]:
        return tuple(f for s in self.sectors for f in s.fields)

    @property
    def sector_ids(self) -> set[str]:
        return {s.id for s in self.sectors} | {OTHER_ID}

    @property
    def field_ids(self) -> set[str]:
        return {f.id for f in self.fields} | {OTHER_ID}

    def sector_of(self, field_id: str) -> str:
        """Return the sector ID that owns `field_id` (OTHER -> OTHER)."""
        if field_id == OTHER_ID:
            return OTHER_ID
        for f in self.fields:
            if f.id == field_id:
                return f.sector_id
        raise KeyError(f"Unknown field id: {field_id}")

    def name_of(self, node_id: str) -> str:
        if node_id == OTHER_ID:
            return self.other_name
        for s in self.sectors:
            if s.id == node_id:
                return s.name
            for f in s.fields:
                if f.id == node_id:
                    return f.name
        raise KeyError(f"Unknown taxonomy id: {node_id}")

    def summary(self) -> str:
        return f"Taxonomy v{self.version}: {len(self.sectors)} sectors / {len(self.fields)} fields"


def _parse_sector(raw: dict) -> Sector:
    sid = raw["id"]
    if not _SECTOR_RE.match(sid):
        raise ValueError(f"Bad sector id: {sid}")
    fields = []
    for rf in raw["fields"]:
        m = _FIELD_RE.match(rf["id"])
        if not m or m.group(1) != sid:
            raise ValueError(f"Field {rf['id']} does not belong to sector {sid}")
        fields.append(Field(id=rf["id"], name=rf["name"], sector_id=sid))
    return Sector(id=sid, name=raw["name"], fields=tuple(fields))


def parse_taxonomy(data: dict) -> Taxonomy:
    sectors = tuple(_parse_sector(s) for s in data["sectors"])
    ids = [s.id for s in sectors] + [f.id for s in sectors for f in s.fields]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"Duplicate taxonomy ids: {sorted(dupes)}")
    other = data.get("other") or {}
    if other.get("id", OTHER_ID) != OTHER_ID:
        raise ValueError("The 'other' node must have id OTHER")
    return Taxonomy(version=int(data["version"]), sectors=sectors,
                    other_name=other.get("name", "Other / Unclear"))


@lru_cache(maxsize=None)
def load_taxonomy(path: Path | None = None) -> Taxonomy:
    return parse_taxonomy(load_yaml(path or CONFIG_DIR / "taxonomy.yaml"))


if __name__ == "__main__":
    print(load_taxonomy().summary())
