"""Dependency-free unit tests for safe randomized system click targets."""

from __future__ import annotations

import random
import sys

sys.path.insert(0, "/app")

from system import System, choose_click_point


def test_click_points_stay_in_safe_interior() -> None:
    rng = random.Random(17)
    for _ in range(500):
        x, y = choose_click_point(100, 50, 80, 40, rng=rng)
        assert 76 <= x <= 124
        assert 38 <= y <= 62


def test_excluded_points_do_not_repeat() -> None:
    rng = random.Random(23)
    seen = set()
    for _ in range(500):
        point = choose_click_point(
            100,
            50,
            80,
            40,
            excluded=seen,
            rng=rng,
        )
        assert point not in seen
        seen.add(point)


def test_system_remembers_positions_per_box() -> None:
    system = System()
    first = system.random_click_point(100, 50, 80, 40)
    other = system.random_click_point(200, 50, 80, 40)
    assert 176 <= other[0] <= 224
    second = system.random_click_point(100, 50, 80, 40)
    assert second != first


def test_invalid_dimensions_are_rejected() -> None:
    for width, height in ((0, 10), (10, 0), (-1, 10), (10, -1)):
        try:
            choose_click_point(100, 50, width, height)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid dimensions should raise ValueError")


def main() -> None:
    test_click_points_stay_in_safe_interior()
    test_excluded_points_do_not_repeat()
    test_system_remembers_positions_per_box()
    test_invalid_dimensions_are_rejected()
    print("OK: system click target unit tests")


if __name__ == "__main__":
    main()
