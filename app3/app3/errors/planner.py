"""规划阶段专用异常 — 由 ``classify_exception`` 映射为 ``ErrorEnvelope``。"""

from __future__ import annotations


class PlannerError(Exception):
    """规划子系统错误基类。"""


class PlannerInputError(PlannerError):
    """解析结果无法组成合法规划输入（如空 ``queries``、CompositeQuery 校验失败）。"""


class PlannerPlanningError(PlannerError):
    """内置规划插件无法生成任务 DAG（如缺必填区划）。"""
