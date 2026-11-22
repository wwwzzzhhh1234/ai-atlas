"""Pydantic v2 models mirroring the SQLite tables (spec Section 6).

`LabelOutput` is what the LLM must return; it is validated against the taxonomy.
`Label` adds the bookkeeping columns stored in the `labels` table.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from atlas.taxonomy import OTHER_ID, load_taxonomy

MAX_SUMMARY_WORDS = 60
_PROJECT_ID_RE = re.compile(r"^(gh|hf|mcp):\S+$")
_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]*$")

Score1to5 = Annotated[int, Field(ge=1, le=5)]


class AssetType(str, Enum):
    skill = "skill"
    mcp = "mcp"
    agent = "agent"
    workflow = "workflow"
    app = "app"
    governance = "governance"
    model = "model"
    resource = "resource"   # excluded from the public directory


class Source(str, Enum):
    github = "github"
    mcp_registry = "mcp_registry"
    huggingface = "huggingface"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_project_id(value: str) -> str:
    if not _PROJECT_ID_RE.match(value):
        raise ValueError(f"project id must look like gh:owner/repo, hf:owner/name or mcp:name — got {value!r}")
    if value.startswith("gh:") and value != value.lower():
        raise ValueError("gh: ids must be lowercase")
    return value


# --------------------------------------------------------------------------- projects
class Project(_Strict):
    id: str
    name: str
    url: str | None = None
    description: str | None = None
    sources: list[Source] = Field(min_length=1)
    stars: int | None = Field(default=None, ge=0)
    forks: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)        # Hugging Face
    downloads: int | None = Field(default=None, ge=0)    # Hugging Face
    created_at: date | None = None
    pushed_at: date | None = None
    license_spdx: str | None = None
    language: str | None = None
    topics: list[str] = Field(default_factory=list)
    is_fork: bool | None = None
    is_archived: bool | None = None
    has_readme: bool | None = None
    readme_excerpt: str | None = None   # internal only — never shown publicly
    readme_chars: int | None = Field(default=None, ge=0)
    collect_groups: list[str] = Field(default_factory=list)
    included: bool = False
    exclude_reason: str | None = None
    collected_at: datetime

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        return validate_project_id(v)

    @field_validator("sources")
    @classmethod
    def _unique_sources(cls, v: list[Source]) -> list[Source]:
        return list(dict.fromkeys(v))


# --------------------------------------------------------------------------- shared label checks
def _check_taxonomy(sector: str, field: str, secondary: list[str]) -> None:
    tax = load_taxonomy()
    if sector not in tax.sector_ids:
        raise ValueError(f"unknown sector_primary {sector!r}")
    if field not in tax.field_ids:
        raise ValueError(f"unknown field_primary {field!r}")
    if tax.sector_of(field) != sector:
        raise ValueError(f"field_primary {field} is not in sector {sector}")
    for f in secondary:
        if f not in tax.field_ids or f == OTHER_ID:
            raise ValueError(f"invalid secondary field {f!r}")
    if field in secondary:
        raise ValueError("field_primary must not repeat in fields_secondary")
    if len(set(secondary)) != len(secondary):
        raise ValueError("fields_secondary contains duplicates")


class _Classification(_Strict):
    asset_type: AssetType
    sector_primary: str
    field_primary: str
    fields_secondary: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def _taxonomy_consistent(self):
        _check_taxonomy(self.sector_primary, self.field_primary, self.fields_secondary)
        return self


# --------------------------------------------------------------------------- labels
class LabelOutput(_Classification):
    """The JSON object the labeling LLM must return."""

    business_summary: str
    developer_summary: str
    use_cases: list[str] = Field(min_length=2, max_length=3)
    non_tech_usability: Score1to5
    deploy_difficulty: Score1to5
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("business_summary", "developer_summary")
    @classmethod
    def _word_limit(cls, v: str) -> str:
        if not v:
            raise ValueError("summary must not be empty")
        n = len(v.split())
        if n > MAX_SUMMARY_WORDS:
            raise ValueError(f"summary has {n} words; limit is {MAX_SUMMARY_WORDS}")
        return v

    @field_validator("inputs", "outputs")
    @classmethod
    def _tags(cls, v: list[str]) -> list[str]:
        # Controlled vocabulary is defined in M3; for now enforce tag shape only.
        out = [t.strip().lower() for t in v]
        bad = [t for t in out if not _TAG_RE.match(t)]
        if bad:
            raise ValueError(f"tags must be lowercase slugs: {bad}")
        return list(dict.fromkeys(out))


class Label(LabelOutput):
    """A row of the `labels` table."""

    project_id: str
    model: str
    prompt_version: str
    status: Literal["ok"] = "ok"
    cost_usd: float | None = Field(default=None, ge=0)
    labeled_at: datetime

    @field_validator("project_id")
    @classmethod
    def _check_project_id(cls, v: str) -> str:
        return validate_project_id(v)


# --------------------------------------------------------------------------- gold / related
class GoldLabel(_Classification):
    project_id: str
    annotator: str = Field(min_length=1)
    notes: str | None = None

    @field_validator("project_id")
    @classmethod
    def _check_project_id(cls, v: str) -> str:
        return validate_project_id(v)


class Related(_Strict):
    project_id: str
    related_id: str
    kind: Literal["alternative", "complement"]
    score: float

    @model_validator(mode="after")
    def _not_self(self):
        validate_project_id(self.project_id)
        validate_project_id(self.related_id)
        if self.project_id == self.related_id:
            raise ValueError("a project cannot be related to itself")
        return self
