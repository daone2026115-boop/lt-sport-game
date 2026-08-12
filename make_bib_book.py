# -*- coding: utf-8 -*-
"""參賽號碼簿產出：per-class 一頁，列出號碼、姓名、報名項目"""
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


def fetch_class_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT grade, class_no FROM students ORDER BY grade, class_no")
    classes = cur.fetchall()

    data = {}
    for g, c in classes:
        cur.execute("""
            SELECT s.student_id, s.bib_number, s.name, s.gender, s.seat_no
            FROM students s
            WHERE s.grade=? AND s.class_no=?
            ORDER BY s.seat_no
        """, (g, c))
        students = cur.fetchall()
        rows = []
        for sid, bib, name, gender, seat in students:
            cur.execute("""
                SELECT e.name, e.category FROM registrations r
                JOIN events e ON r.event_id=e.event_id
                WHERE r.student_id=? ORDER BY e.category
            """, (sid,))
            events = cur.fetchall()
            events_str = " / ".join([f"{n}" for n, _ in events]) if events else "(未報名)"
            rows.append((bib or "-", name, gender, events_str))
        data[(g, c)] = rows
    conn.close()
    return data


def render_class_page(pdf, grade, class_no, rows, meet_name, meet_year):
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    ax.axis("off")

    title = f"{meet_year} {meet_name}  參賽號碼簿"
    subtitle = f"{grade} 年 {class_no} 班 (共 {len(rows)} 人)"
    fig.suptitle(title, fontsize=16, fontweight="bold", y=0.96)
    ax.set_title(subtitle, fontsize=13, pad=14)

    if not rows:
        ax.text(0.5, 0.5, "(無學生資料)", ha="center", va="center", fontsize=14)
    else:
        col_labels = ["號碼", "姓名", "性別", "報名項目"]
        table = ax.table(cellText=rows, colLabels=col_labels,
                         loc="upper center", cellLoc="center",
                         colWidths=[0.12, 0.16, 0.08, 0.6])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.6)
        for (r, c), cell in table.get_celld().items():
            if r == 0:
                cell.set_facecolor("#4472C4")
                cell.set_text_props(color="white", fontweight="bold")
            elif c == 3:
                cell.set_text_props(ha="left")
                cell.PAD = 0.02

    footer = f"產出時間：{datetime.now():%Y-%m-%d %H:%M}"
    fig.text(0.95, 0.02, footer, ha="right", fontsize=8, color="#888")
    pdf.savefig(fig)
    plt.close(fig)


def make_pdf():
    cfg = load_config()
    meet = cfg["meet_info"]
    data = fetch_class_data()
    if not data:
        print("沒有學生資料，請先匯入。")
        return

    out_path = OUT_DIR / f"參賽號碼簿_{datetime.now():%Y%m%d_%H%M}.pdf"
    with PdfPages(out_path) as pdf:
        for (g, c), rows in data.items():
            render_class_page(pdf, g, c, rows, meet["name"], meet["year"])
    print(f"[OK] 號碼簿已產出：{out_path}")
    print(f"     共 {len(data)} 個班級、{sum(len(v) for v in data.values())} 位學生")


if __name__ == "__main__":
    make_pdf()
