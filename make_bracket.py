# -*- coding: utf-8 -*-
"""球類賽制表：依 config.active_format 產出對戰表並繪圖"""
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

from rules import DB_PATH, load_config
from scheduling import (round_robin_schedule, single_elim_bracket,
                         group_stage_bracket, double_elim_bracket)

BASE = Path(__file__).parent
OUT_DIR = BASE / "output"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei"]
plt.rcParams["axes.unicode_minus"] = False


def get_ball_events_and_teams():
    """回傳 [(event_id, code, name, teams)]。teams = 該項目報名的班級列表"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT event_id, code, name FROM events WHERE category='ball' ORDER BY name")
    events = cur.fetchall()
    result = []
    for eid, code, name in events:
        cur.execute("""SELECT DISTINCT s.grade, s.class_no FROM registrations r
                       JOIN students s ON r.student_id=s.student_id
                       WHERE r.event_id=? ORDER BY s.grade, s.class_no""", (eid,))
        teams = [f"{g}年{c}班" for g, c in cur.fetchall()]
        result.append((eid, code, name, teams))
    conn.close()
    return result


def save_matches(event_id, matches_flat, round_labels=None):
    """把賽程寫入 ball_matches（先清除該項目舊資料）"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM ball_matches WHERE event_id=?", (event_id,))
    for i, (rnd, a, b) in enumerate(matches_flat):
        cur.execute("""INSERT INTO ball_matches(event_id, round, team_a, team_b) VALUES(?,?,?,?)""",
                    (event_id, rnd, str(a), str(b)))
    conn.commit()
    conn.close()


def draw_round_robin(ax, teams, schedule, title):
    ax.axis("off")
    ax.set_title(title, fontsize=13, pad=10)
    n = len(teams)
    if n == 0:
        ax.text(0.5, 0.5, "(未報名)", ha="center", va="center", fontsize=12)
        return
    # 對戰矩陣
    table_data = []
    for i in range(n):
        row = [teams[i]]
        for j in range(n):
            row.append("—" if i == j else "")
        table_data.append(row)
    col_labels = [""] + teams
    tbl = ax.table(cellText=table_data, colLabels=col_labels,
                   loc="upper center", cellLoc="center",
                   bbox=[0.05, 0.55, 0.9, 0.38])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    for (rr, cc), cell in tbl.get_celld().items():
        if rr == 0 or cc == 0:
            cell.set_facecolor("#DDEBF7")
            cell.set_text_props(fontweight="bold")

    # 賽程列表
    y = 0.48
    ax.text(0.05, y, "賽程", fontsize=11, fontweight="bold", transform=ax.transAxes)
    y -= 0.03
    for r_idx, matches in enumerate(schedule, 1):
        ax.text(0.05, y, f"第 {r_idx} 輪", fontsize=10, fontweight="bold",
                transform=ax.transAxes, color="#4472C4")
        y -= 0.028
        for a, b in matches:
            ax.text(0.10, y, f"{a}  vs  {b}", fontsize=10, transform=ax.transAxes)
            y -= 0.025
        y -= 0.01
        if y < 0.05:
            break


def draw_bracket(ax, rounds, title):
    """繪製單淘汰對戰樹"""
    ax.axis("off")
    ax.set_title(title, fontsize=13, pad=10)
    if not rounds or not rounds[0]:
        ax.text(0.5, 0.5, "(隊數不足)", ha="center", va="center", fontsize=12)
        return

    n_rounds = len(rounds)
    r1_size = len(rounds[0]) * 2
    y_step = 1.0 / (r1_size + 1)
    ax.set_xlim(0, n_rounds + 1)
    ax.set_ylim(0, 1)

    positions = []
    y_positions = [(i + 1) * y_step for i in range(r1_size)]
    for match_idx, (a, b) in enumerate(rounds[0]):
        y_a = y_positions[match_idx * 2]
        y_b = y_positions[match_idx * 2 + 1]
        _draw_slot(ax, 0.2, y_a, str(a) if a else "(輪空)")
        _draw_slot(ax, 0.2, y_b, str(b) if b else "(輪空)")
        ax.plot([0.9, 1.05, 1.05, 0.9], [y_a, y_a, y_b, y_b], "-", color="#666", lw=1)
        positions.append((y_a + y_b) / 2)

    for r_idx in range(1, n_rounds):
        new_positions = []
        for m_idx in range(len(rounds[r_idx])):
            y_top = positions[m_idx * 2]
            y_bot = positions[m_idx * 2 + 1] if m_idx * 2 + 1 < len(positions) else y_top
            y_mid = (y_top + y_bot) / 2
            _draw_slot(ax, r_idx + 0.2, y_top, "勝者")
            _draw_slot(ax, r_idx + 0.2, y_bot, "勝者")
            ax.plot([r_idx + 0.9, r_idx + 1.05, r_idx + 1.05, r_idx + 0.9],
                    [y_top, y_top, y_bot, y_bot], "-", color="#666", lw=1)
            new_positions.append(y_mid)
        positions = new_positions

    round_names = _bracket_round_names(n_rounds)
    for i, name in enumerate(round_names):
        ax.text(i + 0.5, 0.98, name, ha="center", fontsize=11,
                fontweight="bold", color="#4472C4")


def _draw_slot(ax, x, y, text):
    box = FancyBboxPatch((x, y - 0.025), 0.7, 0.05,
                          boxstyle="round,pad=0.005",
                          fc="white", ec="#666", lw=0.8)
    ax.add_patch(box)
    ax.text(x + 0.35, y, text, ha="center", va="center", fontsize=9)


def _bracket_round_names(n):
    names_map = {1: ["決賽"], 2: ["準決賽", "決賽"],
                  3: ["八強", "準決賽", "決賽"],
                  4: ["十六強", "八強", "準決賽", "決賽"]}
    return names_map.get(n, [f"第{i+1}輪" for i in range(n - 1)] + ["決賽"])


def draw_double_elim(pdf, code, name, de_result, meet):
    """雙淘汰：勝部一頁、敗部一頁、冠軍賽一頁"""
    header = f"{meet['year']} {meet['name']}\n{code} {name}  雙淘汰賽"

    def _bracket_page(title, rounds, color):
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.axis("off")
        ax.set_title(f"{header}\n【{title}】", fontsize=13, pad=8)
        if not rounds:
            ax.text(0.5, 0.5, "(隊數不足)", ha="center", va="center",
                    fontsize=12)
            pdf.savefig(fig); plt.close(fig); return

        n_rounds = len(rounds)
        col_w = 0.9 / n_rounds
        max_matches = max(len(r) for r in rounds)
        row_h = 0.85 / (max_matches + 1)
        for r_idx, matches in enumerate(rounds):
            x = 0.05 + r_idx * col_w
            ax.text(x + col_w / 2, 0.95, f"第 {r_idx + 1} 輪",
                    ha="center", fontsize=12, fontweight="bold", color=color)
            for m_idx, (a, b) in enumerate(matches):
                y = 0.88 - (m_idx + 1) * row_h
                _draw_match_box(ax, x + 0.01, y, col_w - 0.02, str(a), str(b), color)
        pdf.savefig(fig); plt.close(fig)

    _bracket_page("勝部 Winner's Bracket", de_result["winners"], "#27ae60")
    _bracket_page("敗部 Loser's Bracket", de_result["losers"], "#e74c3c")

    # 冠軍賽
    fig, ax = plt.subplots(figsize=(11.69, 5))
    ax.axis("off")
    ax.set_title(f"{header}\n【冠軍賽 Grand Final】", fontsize=14, pad=10)
    gf = de_result["grand_final"]
    if gf and gf[0]:
        a, b = gf[0][0]
        _draw_match_box(ax, 0.30, 0.4, 0.4, str(a), str(b), "#4472C4", big=True)
    else:
        ax.text(0.5, 0.5, "(尚無冠軍賽)", ha="center", fontsize=12)
    pdf.savefig(fig); plt.close(fig)


def _draw_match_box(ax, x, y, w, a, b, color, big=False):
    fs = 12 if big else 10
    ax.add_patch(FancyBboxPatch((x, y - 0.06), w, 0.06,
                                 boxstyle="round,pad=0.005",
                                 fc="white", ec=color, lw=1.5))
    ax.add_patch(FancyBboxPatch((x, y), w, 0.06,
                                 boxstyle="round,pad=0.005",
                                 fc="white", ec=color, lw=1.5))
    ax.text(x + 0.01, y + 0.03, a, ha="left", va="center", fontsize=fs)
    ax.text(x + 0.01, y - 0.03, b, ha="left", va="center", fontsize=fs)


def draw_group_stage(pdf, code, name, gb_result, meet):
    """分組預賽 + 複賽：分組小循環 + 淘汰樹"""
    groups = gb_result["groups"]
    schedules = gb_result["group_schedules"]
    for i, (grp, sched) in enumerate(zip(groups, schedules)):
        fig, ax = plt.subplots(figsize=(8.27, 5.8))
        title = f"{meet['year']} {meet['name']}\n{code} {name}  {chr(65+i)}組  預賽循環表"
        draw_round_robin(ax, grp, sched, title)
        pdf.savefig(fig)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    draw_bracket(ax, gb_result["playoff"],
                  f"{meet['year']} {meet['name']}  {code} {name}  複賽（淘汰賽）")
    pdf.savefig(fig)
    plt.close(fig)


def make_brackets():
    cfg = load_config()
    fmt = cfg["ball_game_rules"]["active_format"]
    meet = cfg["meet_info"]
    ev_data = get_ball_events_and_teams()
    if not ev_data:
        print("沒有球類項目或報名資料。")
        return

    out_path = OUT_DIR / f"球類賽制表_{fmt}_{datetime.now():%Y%m%d_%H%M}.pdf"
    with PdfPages(out_path) as pdf:
        for eid, code, ename, teams in ev_data:
            if not teams:
                fig, ax = plt.subplots(figsize=(8.27, 5))
                ax.axis("off")
                ax.set_title(f"{code} {ename}", fontsize=13)
                ax.text(0.5, 0.5, "(尚無班級報名)", ha="center", fontsize=12)
                pdf.savefig(fig); plt.close(fig)
                continue

            if fmt == "循環賽":
                sched = round_robin_schedule(teams)
                fig, ax = plt.subplots(figsize=(8.27, 11.69))
                draw_round_robin(ax, teams, sched,
                                  f"{meet['year']} {meet['name']}\n{code} {ename}  循環賽")
                pdf.savefig(fig); plt.close(fig)
                flat = [(f"第{i+1}輪", a, b) for i, ms in enumerate(sched) for a, b in ms]
                save_matches(eid, flat)

            elif fmt == "單淘汰":
                rounds = single_elim_bracket(teams)
                fig, ax = plt.subplots(figsize=(11.69, 8.27))
                draw_bracket(ax, rounds,
                              f"{meet['year']} {meet['name']}  {code} {ename}  單淘汰賽")
                pdf.savefig(fig); plt.close(fig)
                names = _bracket_round_names(len(rounds))
                flat = [(names[i], a, b) for i, ms in enumerate(rounds) for a, b in ms]
                save_matches(eid, flat)

            elif fmt == "雙淘汰":
                de = double_elim_bracket(teams)
                draw_double_elim(pdf, code, ename, de, meet)
                flat = []
                for i, ms in enumerate(de["winners"]):
                    for a, b in ms:
                        flat.append((f"勝部第{i+1}輪", a, b))
                for i, ms in enumerate(de["losers"]):
                    for a, b in ms:
                        flat.append((f"敗部第{i+1}輪", a, b))
                for ms in de["grand_final"]:
                    for a, b in ms:
                        flat.append(("冠軍賽", a, b))
                save_matches(eid, flat)

            elif fmt == "分組預賽加複賽":
                gb = group_stage_bracket(teams, n_groups=2, advance_per_group=2)
                draw_group_stage(pdf, code, ename, gb, meet)
                flat = []
                for g_idx, sched in enumerate(gb["group_schedules"]):
                    for r_idx, ms in enumerate(sched):
                        for a, b in ms:
                            flat.append((f"{chr(65+g_idx)}組第{r_idx+1}輪", a, b))
                names = _bracket_round_names(len(gb["playoff"]))
                for i, ms in enumerate(gb["playoff"]):
                    for a, b in ms:
                        flat.append((f"複賽{names[i]}", a, b))
                save_matches(eid, flat)
            else:
                print(f"[X] 未知賽制：{fmt}")

    print(f"[OK] 賽制表已產出（{fmt}）：{out_path}")


if __name__ == "__main__":
    make_brackets()
