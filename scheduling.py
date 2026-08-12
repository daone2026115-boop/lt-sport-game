# -*- coding: utf-8 -*-
"""分組與賽程演算法：蛇形分組、跑道中央外擴、循環賽、單淘汰、分組預賽+複賽"""
import math
import random


def snake_distribute(items, n_heats):
    """依蛇形分配到 n_heats 個組。回傳 list[list]，每組一份"""
    heats = [[] for _ in range(n_heats)]
    forward = True
    idx = 0
    order = list(range(n_heats))
    for item in items:
        heats[order[idx]].append(item)
        idx += 1
        if idx == n_heats:
            idx = 0
            forward = not forward
            order = order[::-1] if not forward else list(range(n_heats))
    return heats


def center_out_lanes(n_lanes):
    """回傳中央→外的道次順序。
    7 道 → [4, 3, 5, 2, 6, 1, 7]
    8 道 → [4, 5, 3, 6, 2, 7, 1, 8]"""
    if n_lanes <= 0:
        return []
    if n_lanes % 2 == 1:
        center = (n_lanes + 1) // 2
        lanes = [center]
        for offset in range(1, n_lanes):
            l, r = center - offset, center + offset
            if l >= 1:
                lanes.append(l)
            if r <= n_lanes:
                lanes.append(r)
            if len(lanes) >= n_lanes:
                break
    else:
        center = n_lanes // 2
        lanes = [center, center + 1]
        for offset in range(1, n_lanes):
            l, r = center - offset, center + 1 + offset
            if l >= 1:
                lanes.append(l)
            if r <= n_lanes:
                lanes.append(r)
            if len(lanes) >= n_lanes:
                break
    return lanes[:n_lanes]


def split_into_heats(participants, lanes_per_group, class_key=lambda p: p.get("class_no")):
    """把參賽者切成多組，同班盡量分散到不同組"""
    n = len(participants)
    if n == 0:
        return []
    n_heats = max(1, math.ceil(n / lanes_per_group))
    # 依班級分組後蛇形散佈
    from collections import defaultdict
    by_class = defaultdict(list)
    for p in participants:
        by_class[class_key(p)].append(p)
    ordered = []
    for cls in sorted(by_class.keys()):
        ordered.extend(by_class[cls])
    heats = snake_distribute(ordered, n_heats)
    return heats


def assign_lanes(heat_members, n_lanes):
    """在一組內指派水道。回傳 list[(lane, member)]"""
    lane_order = center_out_lanes(n_lanes)
    result = []
    for i, m in enumerate(heat_members):
        if i >= len(lane_order):
            break
        result.append((lane_order[i], m))
    result.sort(key=lambda x: x[0])
    return result


def round_robin_schedule(teams):
    """循環賽賽程（圓輪法）。回傳 list[list[(a,b)]]，第 i 個是第 i+1 輪"""
    teams = list(teams)
    if len(teams) < 2:
        return []
    if len(teams) % 2 == 1:
        teams.append(None)  # bye
    n = len(teams)
    rounds = []
    fixed = teams[0]
    rotating = teams[1:]
    for r in range(n - 1):
        pairs = []
        left = [fixed] + rotating[: n // 2 - 1]
        right = rotating[n // 2 - 1:][::-1]
        for a, b in zip(left, right):
            if a is not None and b is not None:
                pairs.append((a, b))
        rounds.append(pairs)
        rotating = [rotating[-1]] + rotating[:-1]
    return rounds


def single_elim_bracket(teams, seed_order=True):
    """單淘汰賽對戰表。回傳 list[list[(a,b)]]，第一組是第一輪"""
    teams = list(teams)
    if len(teams) < 2:
        return []
    size = 1
    while size < len(teams):
        size *= 2
    padded = teams + [None] * (size - len(teams))
    if seed_order:
        # 標準對稱種子：1 vs N, 2 vs N-1
        pairs_r1 = [(padded[i], padded[size - 1 - i]) for i in range(size // 2)]
    else:
        pairs_r1 = [(padded[i], padded[i + 1]) for i in range(0, size, 2)]
    rounds = [pairs_r1]
    remaining = size // 2
    while remaining > 1:
        rounds.append([("待定", "待定") for _ in range(remaining // 2)])
        remaining //= 2
    return rounds


def double_elim_bracket(teams):
    """雙淘汰賽：勝部 (WB) + 敗部 (LB) + 冠軍賽 (GF)
    回傳 dict{winners, losers, grand_final}，每個是 list[list[(a,b)]]"""
    teams = list(teams)
    if len(teams) < 2:
        return {"winners": [], "losers": [], "grand_final": []}

    size = 1
    while size < len(teams):
        size *= 2
    padded = teams + [None] * (size - len(teams))

    # ── 勝部：類似單淘汰 ─────────────────
    wb_rounds = []
    current = padded[:]
    while len(current) > 1:
        matches = [(current[i], current[i + 1]) for i in range(0, len(current), 2)]
        wb_rounds.append(matches)
        current = [f"勝R{len(wb_rounds)}-{i + 1}勝" for i in range(len(matches))]

    # ── 敗部：勝部各輪敗者交替進入 ────────
    lb_rounds = []
    n_wb = len(wb_rounds)
    if n_wb >= 1:
        # LB R1：勝部第 1 輪敗者兩兩對戰
        wb1_losers = [f"勝R1-{i + 1}敗" for i in range(len(wb_rounds[0]))]
        if len(wb1_losers) >= 2:
            lb_r1 = [(wb1_losers[2 * i], wb1_losers[2 * i + 1])
                     for i in range(len(wb1_losers) // 2)]
            lb_rounds.append(lb_r1)
            current_lb = [f"敗R1-{i + 1}勝" for i in range(len(lb_r1))]
        else:
            current_lb = wb1_losers

        for wb_idx in range(1, n_wb):
            wb_losers = [f"勝R{wb_idx + 1}-{i + 1}敗" for i in range(len(wb_rounds[wb_idx]))]
            # 敗部進來的 vs 勝部本輪敗者
            paired = list(zip(current_lb, wb_losers))
            if paired:
                lb_rounds.append(paired)
                r_num = len(lb_rounds)
                current_lb = [f"敗R{r_num}-{i + 1}勝" for i in range(len(paired))]
                # 敗部再自我合併一輪
                if len(current_lb) > 1:
                    merged = [(current_lb[2 * i], current_lb[2 * i + 1])
                              for i in range(len(current_lb) // 2)]
                    lb_rounds.append(merged)
                    r_num = len(lb_rounds)
                    current_lb = [f"敗R{r_num}-{i + 1}勝" for i in range(len(merged))]

    # ── 冠軍賽 ─────────────────────────
    gf_a = "勝部冠軍"
    gf_b = current_lb[0] if current_lb else "敗部冠軍"
    grand_final = [[(gf_a, gf_b)]]

    return {"winners": wb_rounds, "losers": lb_rounds,
            "grand_final": grand_final}


def group_stage_bracket(teams, n_groups=2, advance_per_group=2):
    """分組預賽 + 複賽淘汰。回傳 dict{groups, playoff}"""
    teams = list(teams)
    groups = [[] for _ in range(n_groups)]
    for i, t in enumerate(teams):
        groups[i % n_groups].append(t)
    group_schedules = [round_robin_schedule(g) for g in groups]
    n_playoff = n_groups * advance_per_group
    placeholders = [f"{chr(65+i)}組第{k+1}" for i in range(n_groups) for k in range(advance_per_group)]
    playoff = single_elim_bracket(placeholders, seed_order=True)
    return {
        "groups": groups,
        "group_schedules": group_schedules,
        "playoff": playoff,
    }
