# -*- coding: utf-8 -*-
"""檢錄組點名單（橫式 A4，一欄一跑道）：
   徑賽/接力：欄=跑道，列=班級/號碼/姓名/到場/成績/名次
   田賽：列=選手，欄=預賽1/2/3 決賽1/2/3"""
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from rules import DB_PATH, load_config

BASE = Path(__file__).parent
OUT_DIR = BASE / "output"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei"]
plt.rcParams["axes.unicode_minus"] = False


def clean_name(ename, grade_str, gender_zh):
    """從項目名稱去掉冗餘的「N年級 男/女子」前綴，避免與標題重覆"""
    result = ename
    if grade_str:
        result = re.sub(rf'^{re.escape(grade_str)}\s*', '', result)
    if gender_zh:
        result = re.sub(rf'^{re.escape(gender_zh)}\s*', '', result)
    return result.strip() or ename


def fetch_all_heats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""SELECT e.event_id, e.code, e.name, e.category, e.gender,
                          e.grade_limit, e.unit, e.record_value, e.record_holder,
                          h.heat_id, h.heat_no, h.round
                   FROM heats h JOIN events e ON h.event_id=e.event_id
                   ORDER BY e.category, e.name, h.heat_no""")
    heats = cur.fetchall()
    result = []
    for (eid, code, ename, cat, gender, grade_limit, unit,
         rec_val, rec_holder, hid, hno, rnd) in heats:
        cur.execute("""SELECT ha.lane, s.student_id, s.bib_number, s.name,
                              s.grade, s.class_no, ha.team_code
                       FROM heat_assignments ha
                       LEFT JOIN students s ON ha.student_id=s.student_id
                       WHERE ha.heat_id=? ORDER BY ha.lane""", (hid,))
        members = cur.fetchall()
        result.append({
            "code": code, "ename": ename, "cat": cat,
            "gender": gender, "grade_limit": grade_limit,
            "unit": unit, "rec_val": rec_val, "rec_holder": rec_holder,
            "hno": hno, "rnd": rnd, "members": members,
        })
    conn.close()
    return result


def render_header(ax, fig, info, meet, n_registered, n_lanes):
    grade_str = f"{info['grade_limit']} 年級" if info['grade_limit'] else ""
    gender_zh = {"M": "男子", "F": "女子", "MIX": "混合"}.get(info['gender'], "")
    short_name = clean_name(info['ename'], grade_str, gender_zh)
    cat_zh = {"track": "徑賽", "field": "田賽", "relay": "接力"}.get(info['cat'], info['cat'])

    # 小字：大會名（頁首上方）
    ax.text(0.5, 1.06, f"{meet['year']}  {meet['name']}  ·  檢錄點名單",
            transform=ax.transAxes, ha="center", fontsize=10, color="#888")

    # 主標題：組別 + 短項目名（左），年級 + 性別（右）
    ax.text(0.02, 1.005, f"第 {info['hno']} 組  {short_name}",
            transform=ax.transAxes, ha="left", fontsize=20,
            fontweight="bold", color="#4472C4")
    ax.text(0.98, 1.005, f"{grade_str}  {gender_zh}".strip(),
            transform=ax.transAxes, ha="right", fontsize=18,
            fontweight="bold", color="#e74c3c")

    # 資訊列
    rec_str = ""
    if info['rec_val'] is not None:
        rec_str = f"大會紀錄 {info['rec_val']} {info['unit'] or ''}"
        if info['rec_holder']:
            rec_str += f" ({info['rec_holder']})"
    parts = [f"{info['code']}", cat_zh,
             f"應到 {n_registered} 人 / 共 {n_lanes} 跑道",
             info['rnd']]
    if rec_str:
        parts.append(rec_str)
    ax.text(0.02, 0.95, "  ·  ".join(parts),
            transform=ax.transAxes, fontsize=10, color="#555")
    ax.text(0.68, 0.95, "預定 ____ : ____", transform=ax.transAxes, fontsize=10)
    ax.text(0.86, 0.95, "實際 ____ : ____", transform=ax.transAxes, fontsize=10)


def draw_track_relay(pdf, info, meet, n_lanes):
    """徑賽 / 接力：欄=跑道，列=屬性 + 成績登記"""
    members = info['members']
    n_registered = len([m for m in members if m[2] or m[6]])

    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.axis("off")
    render_header(ax, fig, info, meet, n_registered, n_lanes)

    # 建立 lane -> member map
    lane_map = {m[0]: m for m in members}

    # 表頭欄位
    col_labels = [""] + [f"第 {i} 跑道" for i in range(1, n_lanes + 1)]
    left_w = 0.09
    lane_w = (0.98 - left_w) / n_lanes
    col_widths = [left_w] + [lane_w] * n_lanes

    # 建資料列
    row_defs = ["班級", "號碼布", "姓名", "到場", "成績", "名次"]
    table_data = []
    for label in row_defs:
        row = [label]
        for lane in range(1, n_lanes + 1):
            m = lane_map.get(lane)
            if not m:
                row.append("")
                continue
            lane_n, sid, bib, name, g, c, team = m
            if name is None and team:
                val = {
                    "班級": f"{team[0]}年{int(team[1:]):d}班" if team else "",
                    "號碼布": team or "",
                    "姓名": "(全班)",
                }.get(label, "")
            else:
                val = {
                    "班級": f"{g} 年 {c} 班" if g else "",
                    "號碼布": bib or "-",
                    "姓名": name or "-",
                }.get(label, "")
            row.append(val)
        table_data.append(row)

    # 主表
    bbox = [0.01, 0.16, sum(col_widths), 0.72]
    tbl = ax.table(cellText=table_data, colLabels=col_labels,
                   colWidths=col_widths, cellLoc="center",
                   bbox=bbox)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)

    # 各列高度（成績、名次列較高）
    row_heights = {"班級": 0.07, "號碼布": 0.11, "姓名": 0.10,
                   "到場": 0.10, "成績": 0.13, "名次": 0.10}
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#555")
        if r == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", fontweight="bold", fontsize=12)
            cell.set_height(0.07)
        else:
            label = row_defs[r - 1]
            cell.set_height(row_heights.get(label, 0.09))
            if c == 0:
                cell.set_facecolor("#EAF0F8")
                cell.set_text_props(fontweight="bold", fontsize=11)
            elif label == "號碼布":
                cell.set_text_props(fontweight="bold", fontsize=18)
            elif label == "姓名":
                cell.set_text_props(fontsize=13)
            elif label == "成績":
                cell.set_facecolor("#FFF7E6")
            elif label == "名次":
                cell.set_facecolor("#FDECEA")
                cell.set_text_props(fontweight="bold", fontsize=14)

    # 頁尾簽名列
    ax.text(0.02, 0.05, "檢錄組長：______________", transform=ax.transAxes, fontsize=10)
    ax.text(0.28, 0.05, "終點裁判：______________", transform=ax.transAxes, fontsize=10)
    ax.text(0.54, 0.05, "計時裁判：______________", transform=ax.transAxes, fontsize=10)
    ax.text(0.78, 0.05, "裁判長：______________", transform=ax.transAxes, fontsize=10)
    ax.text(0.02, 0.02, "備註：",
            transform=ax.transAxes, fontsize=10)
    ax.plot([0.06, 0.98], [0.015, 0.015], "-", color="#999",
            transform=ax.transAxes, lw=0.5)

    fig.text(0.99, 0.005, f"{datetime.now():%Y-%m-%d %H:%M}",
             fontsize=7, color="#999", ha="right")
    pdf.savefig(fig); plt.close(fig)


def draw_field(pdf, info, meet):
    """田賽：列=選手，欄=預賽1/2/3 決賽1/2/3 + 到場 + 最終成績 + 名次"""
    members = info['members']
    n_registered = len([m for m in members if m[2] or m[6]])

    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.axis("off")
    render_header(ax, fig, info, meet, n_registered, 0)

    col_labels = ["順序", "號碼布", "班級", "姓名",
                   "預1", "預2", "預3", "決1", "決2", "決3",
                   "最佳成績", "到場", "名次"]
    col_widths = [0.04, 0.07, 0.07, 0.10,
                   0.06, 0.06, 0.06, 0.07, 0.07, 0.07,
                   0.10, 0.05, 0.06]

    n_rows = max(len(members), 8)
    table_data = []
    for i in range(n_rows):
        if i < len(members):
            lane, sid, bib, name, g, c, team = members[i]
            cls = f"{g} 年 {c} 班" if g else ""
            table_data.append([str(lane), bib or "-", cls, name or "-",
                                "", "", "", "", "", "", "", "", ""])
        else:
            table_data.append([""] * len(col_labels))

    tbl = ax.table(cellText=table_data, colLabels=col_labels,
                   colWidths=col_widths, cellLoc="center",
                   bbox=[0.02, 0.12, sum(col_widths), 0.78])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_height(0.07)
        cell.set_edgecolor("#666")
        if r == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", fontweight="bold", fontsize=11)
            if c in (4, 5, 6):
                cell.set_facecolor("#5B9BD5")
            elif c in (7, 8, 9):
                cell.set_facecolor("#E67E22")
            elif c == 10:
                cell.set_facecolor("#c0392b")
            elif c == 12:
                cell.set_facecolor("#8e44ad")
        else:
            if c == 1:
                cell.set_text_props(fontweight="bold", fontsize=13)
            elif c == 10:
                cell.set_facecolor("#FFF7E6")
            elif c == 11:
                cell.set_facecolor("#F8F9FA")
            elif c == 12:
                cell.set_facecolor("#FDECEA")

    ax.text(0.02, 0.05, "檢錄組長：______________", transform=ax.transAxes, fontsize=10)
    ax.text(0.28, 0.05, "測距裁判：______________", transform=ax.transAxes, fontsize=10)
    ax.text(0.54, 0.05, "記錄裁判：______________", transform=ax.transAxes, fontsize=10)
    ax.text(0.78, 0.05, "裁判長：______________", transform=ax.transAxes, fontsize=10)
    fig.text(0.99, 0.005, f"{datetime.now():%Y-%m-%d %H:%M}",
             fontsize=7, color="#999", ha="right")
    pdf.savefig(fig); plt.close(fig)


def make_pdf():
    cfg = load_config()
    heats = fetch_all_heats()
    if not heats:
        print("[X] 沒有分組資料，請先執行 python make_grouping.py")
        return
    n_lanes = cfg["grouping"]["track_lanes_per_group"]
    out_path = OUT_DIR / f"檢錄點名單_{datetime.now():%Y%m%d_%H%M}.pdf"
    with PdfPages(out_path) as pdf:
        for info in heats:
            if info['cat'] == 'field':
                draw_field(pdf, info, cfg["meet_info"])
            else:
                draw_track_relay(pdf, info, cfg["meet_info"], n_lanes)
    print(f"[OK] 檢錄點名單已產出：{out_path}  (共 {len(heats)} 組)")


if __name__ == "__main__":
    make_pdf()
