"""中国行政区离线归一（基于 eduosi/district 的 district.csv，Apache-2.0）。

在解析完成后将 ``regions`` 中的口语/缺省地级市写法拼成与 CSV 一致的
``name+extra+suffix`` 链（省/自治区全称不缩写）。
"""

from __future__ import annotations

import csv
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _row_label(r: dict[str, Any]) -> str:
    return str(r.get("name") or "") + str(r.get("extra") or "") + str(r.get("suffix") or "")


def _load_rows(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            try:
                rid = int(str(r["id"]).strip())
            except (KeyError, ValueError):
                continue
            rows[rid] = r
    return rows


class DistrictNormalizer:
    """按 ``parent_id`` 链拼接 ``name+extra+suffix``，并用尾缀 + 前缀相容做消歧。"""

    def __init__(self, csv_path: str | Path) -> None:
        self._path = Path(csv_path)
        self._rows = _load_rows(self._path)
        self._canon: dict[int, str] = {}
        for rid in self._rows:
            self._canon[rid] = self._raw_canonical(rid)
        self._canon_set = frozenset(self._canon.values())

    def is_canonical(self, region: str) -> bool:
        """是否为库内某节点的完整标准名（已 strip、去空格）。"""
        u = (region or "").strip().replace(" ", "")
        return bool(u) and u in self._canon_set

    def _raw_canonical(self, node_id: int) -> str:
        parts: list[str] = []
        nid: int | None = node_id
        while nid is not None and nid in self._rows:
            r = self._rows[nid]
            parts.append(_row_label(r))
            pid_raw = (self._rows[nid].get("parent_id") or "").strip()
            try:
                pid = int(pid_raw) if pid_raw else 0
            except ValueError:
                pid = 0
            nid = pid if pid else None
        return "".join(reversed(parts))

    def normalize(self, region: str) -> str:
        u = (region or "").strip().replace(" ", "")
        if not u:
            return region
        if u.endswith("市区") and len(u) > 3:
            v = self.normalize(u[:-1])
            if v != u[:-1]:
                return v
        if u in self._canon_set:
            return u

        best: list[tuple[int, str, str]] = []
        max_tail = 0
        for nid, r in self._rows.items():
            tail = _row_label(r)
            if len(tail) < 2 or not u.endswith(tail):
                continue
            if len(tail) > max_tail:
                max_tail = len(tail)
                best = [(nid, tail, self._canon[nid])]
            elif len(tail) == max_tail:
                best.append((nid, tail, self._canon[nid]))

        if not best:
            return region

        up = u[:-max_tail] if max_tail else u

        def _compatible(bp: str) -> bool:
            if not up:
                return True
            if not bp:
                return True
            if bp.startswith(up) or up.startswith(bp):
                return True
            if bp.endswith(up) or up.endswith(bp):
                return True
            if up in bp or bp in up:
                return True
            return False

        filtered = [(nid, tail, can) for nid, tail, can in best if _compatible(can[: -len(tail)] if tail else can)]
        pool = filtered if filtered else best

        if len(pool) == 1:
            return pool[0][2]

        def _score(item: tuple[int, str, str]) -> tuple[int, int]:
            can = item[2]
            common = 0
            for a, b in zip(u, can, strict=False):
                if a != b:
                    break
                common += 1
            return (common, len(can))

        pool.sort(key=_score, reverse=True)
        top = _score(pool[0])
        tied = [p for p in pool if _score(p) == top]
        if len(tied) == 1:
            return tied[0][2]
        logger.debug(
            "行政区归一存在多候选，保持原文: %r candidates=%s",
            region,
            [t[2] for t in tied[:5]],
        )
        return region


@lru_cache(maxsize=8)
def _normalizer_for_path(csv_path: str) -> DistrictNormalizer | None:
    p = Path(csv_path)
    if not p.is_file():
        return None
    try:
        return DistrictNormalizer(p)
    except OSError as e:
        logger.warning("无法加载 district.csv %s: %s", csv_path, e)
        return None


def normalize_region(region: str, *, csv_path: str | None) -> str:
    if not csv_path:
        return region
    n = _normalizer_for_path(csv_path)
    if n is None:
        return region
    return n.normalize(region)


def normalize_regions(regions: list[str], *, csv_path: str | None) -> list[str]:
    if not regions or not csv_path:
        return regions
    n = _normalizer_for_path(csv_path)
    if n is None:
        return regions
    return [n.normalize(r) for r in regions]


def is_district_canonical(region: str, *, csv_path: str | None) -> bool:
    if not csv_path:
        return True
    n = _normalizer_for_path(csv_path)
    if n is None:
        return True
    return n.is_canonical(region)


def regions_are_all_district_canonical(regions: list[str], *, csv_path: str | None) -> bool:
    if not regions or not csv_path:
        return True
    n = _normalizer_for_path(csv_path)
    if n is None:
        return True
    return all(n.is_canonical(r) for r in regions)
