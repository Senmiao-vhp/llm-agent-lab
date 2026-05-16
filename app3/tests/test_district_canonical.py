"""district 标准名判定（与 parse 中 LLM 回退条件一致）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app3.gis.district_normalize import (
    is_district_canonical,
    normalize_regions,
    regions_are_all_district_canonical,
)


def _csv() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "refs" / "district" / "district.csv"


@unittest.skipUnless(_csv().is_file(), "需要 data/refs/district/district.csv")
class TestDistrictCanonical(unittest.TestCase):
    def test_canonical_hangzhou(self) -> None:
        p = str(_csv())
        self.assertTrue(is_district_canonical("浙江省杭州市", csv_path=p))

    def test_non_canonical_colloquial(self) -> None:
        p = str(_csv())
        self.assertFalse(is_district_canonical("西安市关中地区", csv_path=p))

    def test_normalize_then_all_canonical(self) -> None:
        p = str(_csv())
        n = normalize_regions(["杭州市"], csv_path=p)
        self.assertEqual(n, ["浙江省杭州市"])
        self.assertTrue(regions_are_all_district_canonical(n, csv_path=p))


if __name__ == "__main__":
    unittest.main()
