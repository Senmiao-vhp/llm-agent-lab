"""与 app2 对齐的意图枚举 — 供 LLM 结构化输出与契约共用。"""

from __future__ import annotations

from enum import StrEnum


class IntentId(StrEnum):
    CURRENT_STATUS_ESTIMATE = "current_status_estimate"
    CHANGE_DETECTION = "change_detection"
    TREND_EVOLUTION = "trend_evolution"
    COMPLIANCE_CHECK = "compliance_check"
    MULTI_REGION_COMPARE = "multi_region_compare"
    TRANSFER_ANALYSIS = "transfer_analysis"
    OTHER = "other"


INTENT_IDS: tuple[str, ...] = tuple(i.value for i in IntentId)


def intent_from_str(value: str, default: IntentId = IntentId.OTHER) -> IntentId:
    try:
        return IntentId(str(value))
    except ValueError:
        return default
