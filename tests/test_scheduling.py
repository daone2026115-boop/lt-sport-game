# -*- coding: utf-8 -*-
"""分組 / 賽程演算法測試"""
import pytest


def test_center_out_lanes_8():
    from scheduling import center_out_lanes
    assert center_out_lanes(8) == [4, 5, 3, 6, 2, 7, 1, 8]


def test_center_out_lanes_7():
    from scheduling import center_out_lanes
    assert center_out_lanes(7) == [4, 3, 5, 2, 6, 1, 7]


def test_center_out_lanes_6():
    from scheduling import center_out_lanes
    assert center_out_lanes(6) == [3, 4, 2, 5, 1, 6]


def test_center_out_lanes_5():
    from scheduling import center_out_lanes
    assert center_out_lanes(5) == [3, 2, 4, 1, 5]


def test_center_out_lanes_length():
    """任意水道數都應排滿"""
    from scheduling import center_out_lanes
    for n in range(1, 12):
        lanes = center_out_lanes(n)
        assert len(lanes) == n
        assert sorted(lanes) == list(range(1, n + 1))


def test_snake_distribute():
    from scheduling import snake_distribute
    heats = snake_distribute(list(range(9)), 3)
    assert len(heats) == 3
    # 每組應該平均分配
    total = sum(len(h) for h in heats)
    assert total == 9


def test_round_robin_even():
    from scheduling import round_robin_schedule
    rounds = round_robin_schedule(["A", "B", "C", "D"])
    # 4 隊 → 3 輪、每輪 2 場
    assert len(rounds) == 3
    for r in rounds:
        assert len(r) == 2
    # 每兩隊應對戰 1 次
    all_pairs = set()
    for r in rounds:
        for a, b in r:
            all_pairs.add(frozenset([a, b]))
    assert len(all_pairs) == 6  # C(4,2) = 6


def test_round_robin_odd():
    from scheduling import round_robin_schedule
    rounds = round_robin_schedule(["A", "B", "C"])
    # 3 隊 → 3 輪，每輪最多 1 場 (含輪空)
    assert len(rounds) == 3
    pairs = set()
    for r in rounds:
        for a, b in r:
            pairs.add(frozenset([a, b]))
    assert len(pairs) == 3  # C(3,2)


def test_single_elim_power_of_2():
    from scheduling import single_elim_bracket
    rounds = single_elim_bracket(["A", "B", "C", "D"])
    # 4 隊 → 2 輪 (準決賽 + 決賽)
    assert len(rounds) == 2
    assert len(rounds[0]) == 2  # R1: 2 場
    assert len(rounds[1]) == 1  # 決賽: 1 場


def test_single_elim_non_power():
    from scheduling import single_elim_bracket
    rounds = single_elim_bracket(["A", "B", "C"])
    # 3 隊 → 補到 4，R1 有 1 場輪空
    assert len(rounds) == 2
    assert len(rounds[0]) == 2
    # 應有一場含 None (輪空)
    bye = any(a is None or b is None for a, b in rounds[0])
    assert bye


def test_double_elim_4_teams():
    from scheduling import double_elim_bracket
    d = double_elim_bracket(["A", "B", "C", "D"])
    assert len(d["winners"]) >= 1
    assert len(d["losers"]) >= 1
    assert len(d["grand_final"]) == 1
    assert len(d["grand_final"][0]) == 1  # 冠軍賽 1 場


def test_group_stage():
    from scheduling import group_stage_bracket
    r = group_stage_bracket(["A", "B", "C", "D"], n_groups=2, advance_per_group=2)
    assert len(r["groups"]) == 2
    assert all(len(g) == 2 for g in r["groups"])
    # 複賽對戰有 4 隊晉級
    assert len(r["playoff"]) >= 1


def test_split_into_heats():
    from scheduling import split_into_heats
    participants = [{"class_no": (i % 3) + 1} for i in range(20)]
    heats = split_into_heats(participants, lanes_per_group=7)
    # 20 人 / 7 道 → 3 組
    assert len(heats) == 3
    total = sum(len(h) for h in heats)
    assert total == 20
