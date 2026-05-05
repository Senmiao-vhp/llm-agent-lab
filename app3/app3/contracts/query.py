"""结构化查询模型 — 字段语义对齐 app2 `parser_models`。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from app3.contracts.intents import IntentId, intent_from_str

IntentName = str


class QueryIntent(BaseModel):
    intent: IntentName = Field(description="Task intent name")
    regions: List[str] = Field(
        default_factory=list,
        description="行政区/地点名称，便于地理检索。",
    )
    time_range: List[str] = Field(default_factory=list)
    target_object: str = Field(default="耕地")
    specific_metrics: List[str] = Field(default_factory=list)
    coordinates: Optional[List[List[float]]] = None

    @field_validator("intent", mode="before")
    @classmethod
    def _norm_intent(cls, v: Any) -> str:
        raw = str(v or "").strip()
        if not raw:
            return IntentId.OTHER.value
        known = intent_from_str(raw)
        if known.value == raw:
            return known.value
        raw_l = raw.lower()
        if re.fullmatch(r"[a-z][a-z0-9_]{1,63}", raw_l):
            return raw_l
        return IntentId.OTHER.value

    @field_validator("time_range", mode="before")
    @classmethod
    def _norm_time_range(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v

    @field_validator("time_range")
    @classmethod
    def _extract_years(cls, v: List[str]) -> List[str]:
        years: List[int] = []
        cur = datetime.now().year
        saw_since_phrase = False
        for item in v:
            text = str(item)
            if re.search(r"20\d{2}\s*年?\s*(?:以来|至今|到现在)", text):
                saw_since_phrase = True
            for m in re.findall(r"\d{4}", text):
                y = int(m)
                if 2000 <= y <= cur:
                    years.append(y)
        if saw_since_phrase and years:
            years.append(cur)
        years = sorted(set(years))
        return [str(y) for y in years]


class CompositeQuery(BaseModel):
    queries: List[QueryIntent]
    original_query: str = ""
