"""app3 对外契约（意图、结构化查询）。"""

from app3.contracts.intents import INTENT_IDS, IntentId, intent_from_str
from app3.contracts.query import CompositeQuery, QueryIntent

__all__ = [
    "INTENT_IDS",
    "IntentId",
    "intent_from_str",
    "CompositeQuery",
    "QueryIntent",
]
