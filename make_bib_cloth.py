# -*- coding: utf-8 -*-
"""號碼布 PDF：一張 A4 印 3 位選手（橫向堆疊），含號碼、班級、姓名、個人賽項目"""
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

from rules import DB_PATH, load_config

BASE = Path(__file__).parent
OUT_DIR = BASE / "output"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Noto Sans CJK TC", "Noto Sans CJK JP", "WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def fetch_students_with_events():
    """回傳 [(student_id, bib, name, grade, class_no, events_str)]"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""SELECT student_id, bib_number, name, grade, class_no
                   FROM students WHERE bib_number IS NOT NULL
                   ORDER BY grade, class_no, seat_no""")
    students = cur.fetchall()
    result = []
    for sid, bib, name, g, c in students:
        cur.execute("""SELECT e.name, e.category FROM registrations r
                       JOIN events e ON r.event_id=e.event_id
                       WHERE r.student_id=? AND e.category IN ('track','field','relay')
                       ORDER BY e.category, e.name""", (sid,))
        events = cur.fetchall()
        ev_str = "、".join([n for n, _ in events]) if events else "(未報名)"
        result.append((sid, bib, name, g, c, ev_str))
    conn.close()
    return result


def draw_bib_strip(ax, bib, name, class_str, events_str, meet_year, meet_name):
    """單張號碼布 (橫向長條，佔 A4 一頁的 1/3)
    版面：頂部大會名；中央=大號碼；左下=班級+姓名；右下=個人賽項目"""
    ax.set_xlim(0, 20); ax.set_ylim(0, 7)
    ax.set_aspect("auto"); ax.axis("off")

    # 剪裁虛線外框
    ax.add_patch(Rectangle((0.1, 0.1), 19.8, 6.8, fill=False,
                            edgecolor="#999", linestyle="--", linewidth=1))
    # 實線內框
    ax.add_patch(Rectangle((0.4, 0.4), 19.2, 6.2, fill=False,
                            edgecolor="black", linewidth=2))

    # 頂部大會名
    ax.text(10, 6.35, f"{meet_year} {meet_name}", ha="center", va="center",
            fontsize=10, color="#666")

    # 中央大號碼（再放大）
    ax.text(10, 3.9, str(bib), ha="center", va="center",
            fontsize=140, fontweight="bold", color="black")

    # 下方分隔線
    ax.plot([0.6, 19.4], [1.8, 1.8], color="#ddd", linewidth=0.8)

    # 左下：班級 + 姓名（往中央靠近，從 x=1 → x=4）
    ax.text(4.0, 1.3, class_str, ha="left", va="center",
            fontsize=14, fontweight="bold", color="#4472C4")
    ax.text(4.0, 0.65, name, ha="left", va="center",
            fontsize=18, fontweight="bold")

    # 右下：個人賽項目（往中央靠近，從 x=19 → x=16）
    ax.text(16.0, 1.3, "個人賽項目", ha="right", va="center",
            fontsize=10, color="#888")
    ev_short = events_str if len(events_str) <= 28 else events_str[:26] + "…"
    ax.text(16.0, 0.65, ev_short, ha="right", va="center",
            fontsize=13)


def make_pdf():
    students = fetch_students_with_events()
    if not students:
        print("[X] 沒有學生號碼可產出，請先執行 python import_data.py bib")
        return
    cfg = load_config()
    meet_year = cfg["meet_info"]["year"]
    meet_name = cfg["meet_info"]["name"]

    out_path = OUT_DIR / f"號碼布_{datetime.now():%Y%m%d_%H%M}.pdf"
    per_page = 3
    with PdfPages(out_path) as pdf:
        for i in range(0, len(students), per_page):
            batch = students[i:i + per_page]
            fig, axes = plt.subplots(per_page, 1, figsize=(8.27, 11.69))
            for ax in axes:
                ax.axis("off")
            for j, (sid, bib, name, g, c, ev_str) in enumerate(batch):
                draw_bib_strip(axes[j], bib, name, f"{g} 年 {c} 班", ev_str,
                               meet_year, meet_name)
            plt.subplots_adjust(left=0.02, right=0.98, top=0.98,
                                 bottom=0.02, hspace=0.08)
            pdf.savefig(fig)
            plt.close(fig)

    n_pages = (len(students) + per_page - 1) // per_page
    print(f"[OK] 號碼布已產出：{out_path}")
    print(f"     共 {len(students)} 張 / 每頁 3 張 / {n_pages} 頁")


if __name__ == "__main__":
    make_pdf()
