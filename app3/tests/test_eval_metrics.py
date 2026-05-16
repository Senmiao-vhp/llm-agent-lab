"""eval 金标对齐与 parse-only / full 成功判据。"""

from __future__ import annotations

import unittest

from app3.eval.metrics import aggregate, evaluate_case_result


class TestEvalMetrics(unittest.TestCase):
    def test_parse_only_success(self) -> None:
        case = {
            "sample_id": "t1",
            "query": "x",
            "gold": {"primary_intent": "current_status_estimate", "regions": ["北京市"], "time_range": ["2020"], "target_object": "耕地"},
        }
        final = {
            "parse_result": {
                "queries": [{"intent": "current_status_estimate", "regions": ["北京市"], "time_range": ["2020"], "target_object": "耕地"}]
            },
            "phase": "parse",
            "fatal_error": None,
            "error_class": "none",
        }
        ev = evaluate_case_result(case, final, eval_mode="parse", include_parse_result=True)
        self.assertTrue(ev["task_success"])
        self.assertTrue(ev["checks"].get("intent_match"))
        self.assertIn("parse_result", ev)
        self.assertEqual(ev["parse_result"]["queries"][0]["intent"], "current_status_estimate")

    def test_parse_only_fail_empty_queries(self) -> None:
        case = {"sample_id": "t2", "query": "x", "gold": {"primary_intent": "other"}}
        final = {"parse_result": {"queries": []}, "phase": "parse", "fatal_error": None, "error_class": "none"}
        ev = evaluate_case_result(case, final, eval_mode="parse")
        self.assertFalse(ev["task_success"])
        self.assertNotIn("parse_result", ev)

    def test_full_requires_explain_and_pipeline(self) -> None:
        case = {
            "sample_id": "t3",
            "query": "x",
            "gold": {"primary_intent": "current_status_estimate", "regions": ["北京市"], "time_range": ["2020"], "target_object": "耕地"},
        }
        final_parse_only_state = {
            "parse_result": {
                "queries": [{"intent": "current_status_estimate", "regions": ["北京市"], "time_range": ["2020"], "target_object": "耕地"}]
            },
            "plan_result": {"skip_gis": False},
            "gis_context": {"pipeline": {"success": True}},
            "phase": "parse",
            "fatal_error": None,
            "error_class": "none",
        }
        ev = evaluate_case_result(case, final_parse_only_state, eval_mode="full")
        self.assertFalse(ev["task_success"])

        final_ok = {**final_parse_only_state, "phase": "explain"}
        ev2 = evaluate_case_result(case, final_ok, eval_mode="full")
        self.assertTrue(ev2["task_success"])
        self.assertIsInstance(ev2.get("gis_pipeline"), dict)
        self.assertTrue(ev2["gis_pipeline"].get("success"))

    def test_aggregate(self) -> None:
        rows = [
            {"task_success": True, "checks": {"intent_match": True, "regions_match": True, "time_range_match": True, "target_object_match": True}, "duration_ms": 100.0},
            {"task_success": False, "checks": {"intent_match": False}, "duration_ms": 200.0},
        ]
        o = aggregate(rows)
        self.assertEqual(o["case_count"], 2)
        self.assertEqual(o["success_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
