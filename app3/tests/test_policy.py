"""Policy: backoff upper bound、cap 与路由。"""

from __future__ import annotations

import random
import unittest

from app3.config import settings_for_tests
from app3.errors.policy import compute_backoff_seconds, get_max_retries
from app3.errors.taxonomy import RecoverableSubtype
from app3.graph import edges
from app3.state.agent_state import AgentState


class TestPolicy(unittest.TestCase):
    def test_get_max_retries_known(self) -> None:
        self.assertEqual(get_max_retries(RecoverableSubtype.RATE_LIMIT.value), 8)

    def test_get_max_retries_planner(self) -> None:
        self.assertEqual(get_max_retries(RecoverableSubtype.PLANNER.value), 3)

    def test_get_max_retries_fallback(self) -> None:
        self.assertEqual(get_max_retries("nonexistent", fallback=7), 7)

    def test_backoff_monotonic_no_jitter(self) -> None:
        st = settings_for_tests()
        rng = random.Random(42)
        s0 = compute_backoff_seconds(
            RecoverableSubtype.NETWORK.value, 0, settings=st, jitter_ratio=0.0, rng=rng
        )
        rng = random.Random(42)
        s1 = compute_backoff_seconds(
            RecoverableSubtype.NETWORK.value, 1, settings=st, jitter_ratio=0.0, rng=rng
        )
        self.assertLess(s0, s1)

    def test_backoff_respects_cap(self) -> None:
        st = settings_for_tests()
        rng = random.Random(0)
        s = compute_backoff_seconds(
            RecoverableSubtype.RATE_LIMIT.value, 20, settings=st, jitter_ratio=0.0, rng=rng
        )
        self.assertLessEqual(s, 130.0)


class TestEdgesHandleError(unittest.TestCase):
    def test_fatal_routes_end(self) -> None:
        s: AgentState = {"fatal_error": "x", "pending_sleep_seconds": 5.0}
        self.assertEqual(edges.route_after_handle_error(s), "end")

    def test_sleep_routes_delay(self) -> None:
        s: AgentState = {"pending_sleep_seconds": 1.0}
        self.assertEqual(edges.route_after_handle_error(s), "delay")

    def test_zero_sleep_routes_plan(self) -> None:
        s: AgentState = {"pending_sleep_seconds": 0.0}
        self.assertEqual(edges.route_after_handle_error(s), "plan")


if __name__ == "__main__":
    unittest.main()
