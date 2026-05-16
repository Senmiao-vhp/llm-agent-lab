"""结构化意图解析 — 仅 LLM；无模型或解析失败则 fatal"""

from __future__ import annotations

import logging
from typing import Any

from app3.agents import (
    extract_regions_with_fallback,
    extract_time_range_with_retries,
    parse_composite_query,
    time_range_hint_is_valid,
)
from app3.errors.classify import classify_exception
from app3.errors.state import envelope_to_agent_patch
from app3.errors.taxonomy import FatalSubtype
from app3.gis.district_normalize import (
    is_district_canonical,
    normalize_regions,
    regions_are_all_district_canonical,
)
from app3.graph.context import GraphContext
from app3.nodes.base import NodePatch
from app3.state.agent_state import AgentState, ErrorClass

logger = logging.getLogger(__name__)


def _validate_region(region: str) -> bool:
    """
    快速验证地区是否可解析（仅检查格式和基本有效性，不调用外部 API）。
    返回 True 表示可能有效，False 表示明显无效。
    """
    if not region:
        return False
    region = region.strip()
    if len(region) < 2:
        return False
    if any(c in region for c in [",", "，", ";", "；", "(", ")"]):
        return False
    return True


def parse_node(state: AgentState, *, ctx: GraphContext) -> NodePatch:
    user_text = (state.get("user_input") or "").strip()

    if ctx.llm is None:
        return {
            "phase": "parse",
            "fatal_error": "OPENAI_API_KEY is not set (or LLM factory failed); structured parse requires a chat model.",
            "fatal_subtype": FatalSubtype.CONFIG.value,
            "error_class": ErrorClass.FATAL,
        }

    try:
        cq = parse_composite_query(user_text, ctx.llm)
    except Exception as exc:  # noqa: BLE001 — 统一分类
        env = classify_exception(exc, source="parse_node")
        patch = envelope_to_agent_patch(env)
        patch["phase"] = "parse"
        return patch

    data: dict[str, Any] = cq.model_dump()
    data["_parser_source"] = "llm"

    queries = data.get("queries", [])
    for q in queries:
        regions = q.get("regions", [])
        if regions:
            needs_fallback = False
            failed_region = ""

            for region in regions:
                if not _validate_region(region):
                    needs_fallback = True
                    failed_region = region
                    break

            if needs_fallback:
                try:
                    fallback_result = extract_regions_with_fallback(
                        user_text, failed_region, ctx.llm
                    )
                    if fallback_result.regions:
                        q["regions"] = fallback_result.regions
                        data["_region_fallback"] = {
                            "original": failed_region,
                            "corrected": fallback_result.regions,
                            "reasoning": fallback_result.reasoning,
                        }
                        logger.info(
                            "地区回退成功：'%s' → %s",
                            failed_region,
                            fallback_result.regions,
                        )
                    else:
                        data["_region_fallback"] = {
                            "original": failed_region,
                            "corrected": [],
                            "reasoning": "LLM 无法提取有效地区",
                        }
                except Exception as e:
                    logger.warning("地区回退失败: %s", e)
                    data["_region_fallback"] = {
                        "original": failed_region,
                        "error": str(e),
                    }

        dpath = ctx.settings.district_csv_path
        if dpath and (q.get("regions") or []):
            raw_regs = [str(x) for x in (q.get("regions") or []) if str(x).strip()]
            if raw_regs:
                norm_regs = normalize_regions(raw_regs, csv_path=dpath)
                if norm_regs != raw_regs:
                    q["_regions_district_normalize"] = {"from": raw_regs, "to": norm_regs}
                q["regions"] = norm_regs

                if not regions_are_all_district_canonical(norm_regs, csv_path=dpath):
                    hint = next(
                        (r for r in norm_regs if not is_district_canonical(r, csv_path=dpath)),
                        norm_regs[0],
                    )
                    try:
                        fb = extract_regions_with_fallback(user_text, hint, ctx.llm)
                        if fb.regions:
                            raw2 = [str(x) for x in fb.regions if str(x).strip()]
                            norm2 = normalize_regions(raw2, csv_path=dpath)
                            q["regions"] = norm2
                            data["_region_fallback_district"] = {
                                "after_normalize": norm_regs,
                                "llm_regions": list(fb.regions),
                                "final_normalized": norm2,
                                "reasoning": fb.reasoning,
                            }
                            if norm2 != norm_regs:
                                q["_regions_district_normalize"] = {
                                    "from": norm_regs,
                                    "to": norm2,
                                    "after_llm_retry": True,
                                }
                            elif norm2 != raw2:
                                q["_regions_district_normalize"] = {
                                    "from": raw2,
                                    "to": norm2,
                                    "after_llm_retry": True,
                                }
                            logger.info(
                                "district 未命中标准名，LLM 重提地区后归一: %s → %s",
                                norm_regs,
                                norm2,
                            )
                        else:
                            data["_region_fallback_district"] = {
                                "after_normalize": norm_regs,
                                "llm_regions": [],
                                "reasoning": fb.reasoning or "LLM 未返回地区",
                            }
                    except Exception as e:
                        logger.warning("district 未命中后地区回退失败: %s", e)
                        data["_region_fallback_district"] = {
                            "after_normalize": norm_regs,
                            "error": str(e),
                        }

        rough_time = [str(x) for x in (q.get("time_range") or [])]
        try:
            if time_range_hint_is_valid(rough_time):
                q["_time_refinement"] = {
                    "ok": True,
                    "skipped_llm": True,
                    "reasoning": "首轮 CompositeQuery 时间字段已满足格式与条数一致性",
                    "expected_total_year_count": len(rough_time),
                    "attempts": 0,
                }
            else:
                new_times, meta = extract_time_range_with_retries(
                    user_text,
                    rough_time_hint=rough_time,
                    intent=str(q.get("intent") or ""),
                    regions=[str(x) for x in (q.get("regions") or [])],
                    llm=ctx.llm,
                )
                q["time_range"] = new_times
                q["_time_refinement"] = meta
        except Exception as e:
            logger.warning("时间精炼失败: %s", e)
            q["_time_refinement"] = {"ok": False, "error": str(e)}

    return {
        "phase": "parse",
        "parse_result": data,
        "error_class": ErrorClass.NONE,
        "fatal_error": None,
        "fatal_subtype": None,
        "recoverable_subtype": None,
        "last_error_message": None,
        "last_tool_error": None,
    }
