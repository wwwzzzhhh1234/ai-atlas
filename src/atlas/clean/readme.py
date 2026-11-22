"""README cleanup: strip front matter, HTML, badges, images and link URLs; truncate.

The result is an internal excerpt for LLM labeling only — never shown publicly (spec Section 6).
"""

from __future__ import annotations

import html
import re

_FRONT_MATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_CODE_FENCE = re.compile(r"```.*?```", re.S)
_BADGE_LINK = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)")   # [![alt](img)](link)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")                      # ![alt](img)
_REF_IMAGE = re.compile(r"!\[[^\]]*\]\[[^\]]*\]")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")                      # [text](url) -> text
_REF_DEF = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.M)
_TAG = re.compile(r"<[^>]+>")
_BARE_URL = re.compile(r"https?://\S+")
_TABLE_RULE = re.compile(r"^\s*\|?[\s:|-]{3,}\|?\s*$", re.M)
_BLANKS = re.compile(r"\n\s*\n\s*\n+")
_SPACES = re.compile(r"[ \t]{2,}")
# Hugging Face Space template line (carries no information about the project)
_HF_BOILERPLATE = re.compile(r"^.*Check out the configuration reference at.*$", re.M | re.I)


def clean_readme(text: str | None, max_chars: int = 12000, keep_code: bool = False) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n")
    t = _FRONT_MATTER.sub("", t)
    t = _HTML_COMMENT.sub("", t)
    t = _HF_BOILERPLATE.sub("", t)
    if not keep_code:
        t = _CODE_FENCE.sub("[code]", t)
    for rx in (_BADGE_LINK, _IMAGE, _REF_IMAGE, _REF_DEF):
        t = rx.sub("", t)
    t = _LINK.sub(r"\1", t)
    t = _TAG.sub(" ", t)
    t = html.unescape(t)
    t = _BARE_URL.sub("", t)
    t = _TABLE_RULE.sub("", t)
    t = "\n".join(line.rstrip() for line in t.split("\n"))
    t = _SPACES.sub(" ", t)
    t = _BLANKS.sub("\n\n", t).strip()
    if len(t) > max_chars:
        cut = t.rfind(" ", 0, max_chars)
        t = t[: cut if cut > max_chars * 0.8 else max_chars].rstrip() + " …"
    return t
