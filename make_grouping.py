# -*- coding: utf-8 -*-
"""田徑分組表 + 分道表：寫入 heats/heat_assignments，並產出 PDF 與 Excel"""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from rules import DB_PATH, load_config
from scheduling import split_into_heats, assign_lanes

BASE = Path(__file__).parent
OUT_DIR = BASE / "output"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Noto Sans CJK TC", "Noto Sans CJK JP", "WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def fetch_track_field_events():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""SELECT event_id, code, name, category FROM events
                   WHERE category IN ('track','field','relay')
                   ORDER BY category, name""")
    return conn, cur, cur.fetchall()


def build_all_heats():
    """為所有田徑項目產生分組並寫入資料庫"""
    cfg = load_config()
    lanes = cfg["grouping"]["track_lanes_per_group"]
    field_size = cfg["grouping"]["field_group_size"]

    conn, cur, events = fetch_track_field_events()
    cur.execute("DELETE FROM heat_assignments")
    cur.execute("DELETE FROM heats")

    summary = []
    for eid, code, ename, cat in events:
        if cat == "relay":
            cur.execute("""SELECT DISTINCT s.grade, s.class_no FROM registrations r
                           JOIN students s ON r.student_id=s.student_id
                           WHERE r.event_id=? ORDER BY s.grade, s.class_no""", (eid,))
            teams = cur.fetchall()
            participants = [{"student_id": None,
                             "team_code": f"{g}{c:02d}",
                             "name": f"{g}年{c}班",
                             "class_no": c, "grade": g} for g, c in teams]
        else:
            cur.execute("""SELECT s.student_id, s.bib_number, s.name, s.grade, s.class_no
                           FROM registrations r JOIN students s ON r.student_id=s.student_id
                           WHERE r.event_id=? ORDER BY s.grade, s.class_no, s.seat_no""",
                        (eid,))
            participants = [{"student_id": sid, "team_code": None,
                             "bib": bib, "name": name,
                             "class_no": c, "grade": g}
                            for sid, bib, name, g, c in cur.fetchall()]

        if not participants:
            summary.append((code, ename, 0, 0))
            continue

        group_size = lanes if cat != "field" else field_size
        heats = split_into_heats(participants, group_size)

        n_saved = 0
        for hi, members in enumerate(heats, 1):
            cur.execute("INSERT INTO heats(event_id, heat_no, round) VALUES(?,?,?)",
                        (eid, hi, "預賽"))
            heat_id = cur.lastrowid
            if cat == "field":
                for order_no, m in enumerate(members, 1):
                    cur.execute("""INSERT INTO heat_assignments(heat_id, lane, student_id, team_code)
                                   VALUES(?,?,?,?)""",
                                (heat_id, order_no, m.get("student_id"), m.get("team_code")))
                    n_saved += 1
            else:
                for lane, m in assign_lanes(members, lanes):
                    cur.execute("""INSERT INTO heat_assignments(heat_id, lane, student_id, team_code)
                                   VALUES(?,?,?,?)""",
                                (heat_id, lane, m.get("student_id"), m.get("team_code")))
                    n_saved += 1

        summary.append((code, ename, len(heats), n_saved))

    conn.commit()
    conn.close()
    print("[OK] 分組完成：")
    for code, name, n_heats, n_ppl in summary:
        print(f"  {code:10s} {name:20s} {n_heats} 組 / {n_ppl} 人")
    return summary


def export_excel():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""SELECT e.code, e.name, e.category, h.heat_no, h.round,
                          ha.lane, s.bib_number, s.name, s.grade, s.class_no, ha.team_code
                   FROM heats h
                   JOIN events e ON h.event_id = e.event_id
                   JOIN heat_assignments ha ON ha.heat_id = h.heat_id
                   LEFT JOIN students s ON ha.student_id = s.student_id
                   ORDER BY e.category, e.name, h.heat_no, ha.lane""")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("(無分組資料)")
        return None
    df = pd.DataFrame(rows, columns=["項目代碼", "項目", "類別", "組別", "回合",
                                       "水道/順序", "號碼", "姓名", "年", "班", "隊伍"])
    path = OUT_DIR / f"分組分道表_{datetime.now():%Y%m%d_%H%M}.xlsx"
    df.to_excel(path, index=False)
    print(f"[OK] Excel 已輸出：{path}")
    return path


def draw_event_page(pdf, event_info, heats_data, meet_name, meet_year):
    code, ename, cat = event_info
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")
    cat_zh = {"track": "徑賽", "field": "田賽", "relay": "接力"}[cat]
    fig.suptitle(f"{meet_year} {meet_name}", fontsize=14, y=0.97)
    ax.set_title(f"【{cat_zh}】{code}  {ename}  分組{'分道' if cat != 'field' else '順序'}表",
                 fontsize=13, pad=10)

    if not heats_data:
        ax.text(0.5, 0.5, "(無報名)", ha="center", va="center", fontsize=14)
        pdf.savefig(fig)
        plt.close(fig)
        return

    y0 = 0.90
    for heat_no, rows in heats_data:
        header = "水道" if cat != "field" else "順序"
        col_labels = [header, "號碼", "姓名", "班級"]
        table_data = []
        for lane, bib, name, grade, cls, team in rows:
            if name is None and team:
                table_data.append([str(lane), team, f"{team[0]}年{int(team[1:]):d}班", ""])
            else:
                table_data.append([str(lane), bib or "-", name or "-",
                                    f"{grade}-{cls}" if grade else ""])
        height = 0.045 + 0.03 * len(table_data)
        top = y0
        ax.text(0.05, top, f"第 {heat_no} 組", fontsize=11, fontweight="bold",
                transform=ax.transAxes)
        tbl = ax.table(cellText=table_data, colLabels=col_labels,
                       colWidths=[0.12, 0.20, 0.28, 0.14],
                       bbox=[0.05, top - height, 0.74, height - 0.01])
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        for (rr, cc), cell in tbl.get_celld().items():
            if rr == 0:
                cell.set_facecolor("#4472C4")
                cell.set_text_props(color="white", fontweight="bold")
        y0 = top - height - 0.03
        if y0 < 0.15:
            pdf.savefig(fig)
            plt.close(fig)
            fig, ax = plt.subplots(figsize=(8.27, 11.69))
            ax.axis("off")
            ax.set_title(f"{code} {ename} (續)", fontsize=12)
            y0 = 0.90

    pdf.savefig(fig)
    plt.close(fig)


def export_pdf():
    cfg = load_config()
    meet = cfg["meet_info"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""SELECT event_id, code, name, category FROM events
                   WHERE category IN ('track','field','relay') ORDER BY category, name""")
    events = cur.fetchall()

    out_path = OUT_DIR / f"分組分道表_{datetime.now():%Y%m%d_%H%M}.pdf"
    with PdfPages(out_path) as pdf:
        for eid, code, ename, cat in events:
            cur.execute("SELECT heat_id, heat_no FROM heats WHERE event_id=? ORDER BY heat_no", (eid,))
            heats = cur.fetchall()
            heats_data = []
            for hid, hno in heats:
                cur.execute("""SELECT ha.lane, s.bib_number, s.name, s.grade, s.class_no, ha.team_code
                               FROM heat_assignments ha
                               LEFT JOIN students s ON ha.student_id=s.student_id
                               WHERE ha.heat_id=? ORDER BY ha.lane""", (hid,))
                heats_data.append((hno, cur.fetchall()))
            draw_event_page(pdf, (code, ename, cat), heats_data, meet["name"], meet["year"])
    conn.close()
    print(f"[OK] PDF 已輸出：{out_path}")


if __name__ == "__main__":
    build_all_heats()
    export_excel()
    export_pdf()
