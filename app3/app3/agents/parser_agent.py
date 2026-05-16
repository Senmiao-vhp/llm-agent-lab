"""解析门面：仅用大模型结构化产出 CompositeQuery；失败由调用方处理为致命错误。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app3.contracts.query import CompositeQuery

_YEAR_TOKEN = re.compile(r"^\d{4}$")


class RegionExtractionResult(BaseModel):
    """地区提取结果模型"""
    regions: list[str]
    reasoning: str = ""


def _build_region_extraction_prompt(user_text: str, failed_region: str) -> str:
    return f"""你是地理空间分析的行政区划专家。

用户原始问句："{user_text}"

之前提取的地区 "{failed_region}" 无法匹配到有效的行政区划。

请重新从用户问句中提取地区名称，要求：
1. 中国地名必须写**规范全称**，包括：
   - 省份/直辖市/自治区全称（如"四川省"而非"四川"）
   - 地级市全称（如"成都市"而非"成都"）
   - 市辖区/县/县级市全称（如"郫都区"、"双流区"、"简阳市"）
2. 如果是直辖市，格式为"北京市"、"上海市"、"天津市"、"重庆市"
3. 如果是县/区，需要带上所属市/省
4. 如果问句中没有明确地区，输出空列表

示例规范：
- "郫县" → "四川省成都市郫都区"
- "成都" → "四川省成都市"
- "雄安" → "河北省雄安新区"
- "容城" → "河北省保定市容城县"

请直接输出 JSON 格式：{{"regions": ["规范地区名称"], "reasoning": "提取理由"}}"""


class TimeExtractionResult(BaseModel):
    """时间抽取结构化结果（与首轮 CompositeQuery 解耦，便于校验与重试）。"""

    time_list: list[str] = Field(description="四位公历年份字符串列表，如 [\"2020\",\"2021\"]")
    expected_total_year_count: int = Field(
        ge=0,
        description="你认为应从本问句中展开出的年份总条数（与 time_list 长度一致；无时间则为 0）",
    )
    reasoning: str = Field(default="", description="如何理解时间范围、与问句对应关系的简要说明")


def _validate_time_extraction_result(r: TimeExtractionResult, *, current_year: int) -> tuple[bool, str]:
    if r.expected_total_year_count < 0:
        return False, "expected_total_year_count 不能为负"
    if len(r.time_list) != r.expected_total_year_count:
        return (
            False,
            f"time_list 长度 {len(r.time_list)} 与 expected_total_year_count={r.expected_total_year_count} 不一致",
        )
    for i, t in enumerate(r.time_list):
        s = str(t).strip()
        if not _YEAR_TOKEN.fullmatch(s):
            return False, f"time_list[{i}]={t!r} 不是四位数字年份"
        y = int(s, 10)
        if not (2000 <= y <= current_year):
            return False, f"time_list[{i}] 中年份 {y} 超出允许范围 [2000, {current_year}]"
    return True, ""


def time_range_hint_is_valid(hint: list[str]) -> bool:
    """首轮 ``time_range`` 若已是合法四位年份且条数与声明一致，则可跳过二次 LLM。"""
    cleaned = [str(x).strip() for x in hint if str(x).strip()]
    probe = TimeExtractionResult(
        time_list=cleaned,
        expected_total_year_count=len(cleaned),
        reasoning="",
    )
    return _validate_time_extraction_result(probe, current_year=datetime.now().year)[0]


def _build_time_extraction_system(
    current_year: int,
    user_text: str,
    rough_time_hint: list[str],
    intent: str,
    regions: list[str],
    correction_hint: str,
) -> str:
    hint = ", ".join(str(x) for x in rough_time_hint) if rough_time_hint else "（首轮解析未给出年份，请仅从问句推断）"
    reg = ", ".join(str(x) for x in regions) if regions else "（无）"
    fix = f"\n\n【上次校验未通过，请修正】\n{correction_hint}" if correction_hint.strip() else ""
    return f"""你是时间语义抽取模块：根据用户问句与首轮解析提示，输出结构化 JSON（字段见模式）。

### 要求

1. **time_list**：仅含四位公历年份字符串（如 "2023"），与问句中可确定的时间范围一致；无明确时间则 **time_list 为空列表**。
2. **expected_total_year_count**：必须等于 **len(time_list)**。无时间则为 0。
3. **reasoning**：简述如何从问句得到上述年份（中文一两句即可）。
4. 年份须在 **[2020, {current_year}]**；「近五年」「去年」等须展开为具体年份；去重后写入列表，**条数与 expected_total_year_count 一致**。

### 上下文

- 用户问句：{user_text!r}
- 首轮解析意图：{intent!r}
- 首轮解析地区：{reg!r}
- 首轮解析时间提示（仅供参考，可纠错）：{hint}
{fix}

当前公历年年份参考：{current_year}。"""


def extract_time_range_with_retries(
    user_text: str,
    *,
    rough_time_hint: list[str],
    intent: str,
    regions: list[str],
    llm: BaseChatModel,
    max_attempts: int = 3,
) -> tuple[list[str], dict[str, Any]]:
    """
    对时间列表做结构化抽取 + 后处理校验；不通过则带反馈重试 LLM。
    若用尽次数仍不通过，保留首轮 ``rough_time_hint`` 并返回 meta.ok=False。
    """
    current_year = datetime.now().year
    structured = llm.with_structured_output(TimeExtractionResult)
    correction = ""
    last: TimeExtractionResult | None = None
    attempts = 0
    for _ in range(max_attempts):
        attempts += 1
        sys = _build_time_extraction_system(
            current_year,
            user_text,
            rough_time_hint,
            intent,
            regions,
            correction,
        )
        out = structured.invoke(
            [
                SystemMessage(content=sys),
                HumanMessage(content="请输出时间结构化结果（JSON 模式）。"),
            ]
        )
        if not isinstance(out, TimeExtractionResult):
            correction = "上一次未返回合法 TimeExtractionResult，请严格按模式输出。"
            continue
        last = out
        ok, err = _validate_time_extraction_result(out, current_year=current_year)
        if ok:
            return list(out.time_list), {
                "ok": True,
                "reasoning": out.reasoning,
                "expected_total_year_count": out.expected_total_year_count,
                "attempts": attempts,
            }
        correction = err

    # 用尽重试：保留首轮提示
    safe = [str(x).strip() for x in rough_time_hint if str(x).strip()]
    return safe, {
        "ok": False,
        "reasoning": (last.reasoning if last else "") or "重试耗尽，保留首轮时间解析",
        "attempts": attempts,
        "kept_original": True,
        "last_error": correction,
    }


def extract_regions_with_fallback(
    user_text: str,
    failed_region: str,
    llm: BaseChatModel,
) -> RegionExtractionResult:
    """
    地区提取回退函数：当原始提取的地区无法匹配时，调用 LLM 重新提取。
    """
    structured = llm.with_structured_output(RegionExtractionResult)
    messages = [
        SystemMessage(content=_build_region_extraction_prompt(user_text, failed_region)),
        HumanMessage(content="请执行地区提取回退："),
    ]
    out = structured.invoke(messages)
    
    if not isinstance(out, RegionExtractionResult):
        return RegionExtractionResult(regions=[], reasoning="LLM 返回格式错误")
    
    return out


def _build_parse_system_prompt(current_year: int) -> str:
    return f"""你是地理空间/耕地分析助手的**查询解析**模块。只输出符合给定 JSON 模式的结构化结果。

### 意图分类规则（必须严格遵守）

1. **current_status_estimate**（现状估算）：询问耕地面积、保有量、现状数量
   - 关键词：面积、保有量、现状、多少、估算、量级、大概、有多大

2. **change_detection**（变化监测）：询问耕地变化、流失、占用、非农化情况
   - 关键词：变化、流失、占用、破坏、减少、图斑、非农化、监测

3. **trend_evolution**（趋势演变）：询问多年变化趋势、时间序列分析
   - 关键词：趋势、历年、多年、近[三四五六]年、时间序列、年际、演变

4. **compliance_check**（合规检查）：判断某点是否为耕地、是否合规
   - 关键词：合规、红线、还是耕地、坐标、点

5. **multi_region_compare**（多区域对比）：比较两个及以上地区的耕地情况
   - 关键词：谁多、谁少、对比、比较、和、与、vs

6. **transfer_analysis**（转移分析）：询问耕地流失后变成什么地类
   - 关键词：流失后、变成什么、转移、去向

7. **other**（其他）：无法匹配以上类型的问题

### 字段说明

- **intent**: 意图类型，从上述7类中选择最匹配的一个
- **regions**: 行政区/地点名称列表，中国地名写规范全称（如「四川省成都市郫都区」）
- **time_range**: 年份列表（如 ["2023"]），将「近五年」「去年」等展开为具体年份
- **target_object**: 目标对象，默认为「耕地」
- **specific_metrics**: 具体指标列表（如「面积」「变化率」等）
- **coordinates**: 坐标列表，格式为 [[lon, lat], ...]

### 示例

- 用户问："2023年成都市郫都区耕地保有量大概多少？"
  → intent: current_status_estimate, regions: ["成都市郫都区"], time_range: ["2023"]

- 用户问："河北容城县耕地被占用情况如何？"
  → intent: change_detection, regions: ["河北省容城县"]

- 用户问："2018到2023年杭州市耕地变化趋势？"
  → intent: trend_evolution, regions: ["杭州市"], time_range: ["2018", "2023"]

- 用户问："坐标[104.0, 30.7]还是耕地吗？"
  → intent: compliance_check, coordinates: [[104.0, 30.7]]

- 用户问："北京和河北谁的耕地更多？"
  → intent: multi_region_compare, regions: ["北京市", "河北省"]

- 用户问："长沙耕地流失后主要变成了什么？"
  → intent: transfer_analysis, regions: ["长沙市"]

**当前公历年年份参考：{current_year}**（将「近五年」「去年」等展开为具体四位年份）。

请直接输出 JSON 格式的解析结果。"""


def parse_composite_query(user_text: str, llm: BaseChatModel) -> CompositeQuery:
    """
    调用 `with_structured_output(CompositeQuery)`，附带 System Prompt 指导解析。
    失败时抛出异常，由 `parse_node` 转为 fatal（不做占位结果）。
    """
    text = (user_text or "").strip()
    current_year = datetime.now().year

    structured = llm.with_structured_output(CompositeQuery)
    messages = [
        SystemMessage(content=_build_parse_system_prompt(current_year)),
        HumanMessage(content=f"用户问句: {text}"),
    ]
    out = structured.invoke(messages)

    if not isinstance(out, CompositeQuery):
        raise TypeError(f"structured parse returned {type(out)!r}, expected CompositeQuery")
    if not (out.original_query or "").strip():
        out = out.model_copy(update={"original_query": text})
    return out
