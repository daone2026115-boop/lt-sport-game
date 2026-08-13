# -*- coding: utf-8 -*-
"""成績分析報表：班級積分、參與統計、破紀錄清單，輸出 Excel + PDF 圖表"""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from rules import DB_PATH, load_config

BASE = Path(__file__).parent
OUT_DIR = BASE / "output"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Noto Sans CJK TC", "Noto Sans CJK JP", "WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def analyze():
    conn = sqlite3.connect(DB_PATH)

    class_pts = pd.read_sql("""
        SELECT s.grade AS 年級, s.class_no AS 班級,
               COALESCE(SUM(res.points), 0) AS 總積分,
               COUNT(res.result_id) AS 入圍次數,
               COALESCE(SUM(res.broke_record), 0) AS 破紀錄次數
        FROM students s
        LEFT JOIN results res ON res.student_id=s.student_id AND res.rank BETWEEN 1 AND 8
        GROUP BY s.grade, s.class_no
        ORDER BY 總積分 DESC
    """, conn)

    event_stats = pd.read_sql("""
        SELECT e.category AS 類別, e.code AS 代碼, e.name AS 項目,
               COUNT(r.reg_id) AS 報名數
        FROM events e LEFT JOIN registrations r ON e.event_id=r.event_id
        GROUP BY e.event_id
        ORDER BY 報名數 DESC
    """, conn)

    participation = pd.read_sql("""
        SELECT s.grade AS 年級, s.gender AS 性別,
               COUNT(DISTINCT s.student_id) AS 學生數,
               COUNT(r.reg_id) AS 報名總數,
               ROUND(1.0 * COUNT(r.reg_id) / COUNT(DISTINCT s.student_id), 2) AS 平均每人項目
        FROM students s LEFT JOIN registrations r ON r.student_id=s.student_id
        GROUP BY s.grade, s.gender
        ORDER BY s.grade, s.gender
    """, conn)

    records_broken = pd.read_sql("""
        SELECT e.code AS 代碼, e.name AS 項目, s.name AS 姓名,
               s.grade AS 年, s.class_no AS 班,
               res.performance AS 新紀錄, e.record_value AS 舊紀錄, e.unit AS 單位
        FROM results res
        JOIN events e ON res.event_id=e.event_id
        LEFT JOIN students s ON res.student_id=s.student_id
        WHERE res.broke_record=1
        ORDER BY e.category, e.name
    """, conn)

    top_performers = pd.read_sql("""
        SELECT s.name AS 姓名, s.grade AS 年, s.class_no AS 班,
               SUM(res.points) AS 個人積分,
               COUNT(res.result_id) AS 入圍次數
        FROM results res JOIN students s ON res.student_id=s.student_id
        WHERE res.rank BETWEEN 1 AND 8
        GROUP BY s.student_id
        ORDER BY 個人積分 DESC
        LIMIT 20
    """, conn)

    conn.close()
    return {
        "class_points": class_pts,
        "event_stats": event_stats,
        "participation": participation,
        "records_broken": records_broken,
        "top_performers": top_performers,
    }


def export_excel(data, path):
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        data["class_points"].to_excel(w, sheet_name="班級積分", index=False)
        data["top_performers"].to_excel(w, sheet_name="個人英雄榜", index=False)
        data["records_broken"].to_excel(w, sheet_name="破紀錄清單", index=False)
        data["event_stats"].to_excel(w, sheet_name="項目報名數", index=False)
        data["participation"].to_excel(w, sheet_name="參與統計", index=False)
    print(f"[OK] Excel 分析報表：{path}")


def export_pdf(data, path, meet):
    with PdfPages(path) as pdf:
        _page_title(pdf, meet)
        _chart_class_points(pdf, data["class_points"])
        _chart_participation(pdf, data["participation"])
        _chart_event_popularity(pdf, data["event_stats"])
        _table_page(pdf, data["records_broken"], "破紀錄清單")
        _table_page(pdf, data["top_performers"], "個人積分英雄榜 Top 20")
    print(f"[OK] PDF 分析報表：{path}")


def _page_title(pdf, meet):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.axis("off")
    ax.text(0.5, 0.65, f"{meet['year']} {meet['name']}", ha="center",
            fontsize=32, fontweight="bold")
    ax.text(0.5, 0.5, "成績分析報告", ha="center", fontsize=24, color="#4472C4")
    ax.text(0.5, 0.35, f"產出時間：{datetime.now():%Y-%m-%d %H:%M}",
            ha="center", fontsize=12, color="#888")
    pdf.savefig(fig); plt.close(fig)


def _chart_class_points(pdf, df):
    if df.empty or df["總積分"].sum() == 0:
        return
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    df = df.head(20).copy()
    df["班級"] = df["年級"].astype(str) + "-" + df["班級"].astype(str)
    ax.barh(df["班級"][::-1], df["總積分"][::-1], color="#4472C4")
    ax.set_xlabel("總積分"); ax.set_title("班級積分排行（Top 20）", fontsize=16)
    ax.grid(axis="x", alpha=.3)
    pdf.savefig(fig); plt.close(fig)


def _chart_participation(pdf, df):
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    df["組別"] = df["年級"].astype(str) + "年" + df["性別"].map({"M": "男", "F": "女"})
    ax.bar(df["組別"], df["平均每人項目"], color=["#3498db" if g == "M" else "#e91e63"
                                             for g in df["性別"]])
    ax.set_ylabel("平均每人報名項目數"); ax.set_title("各年級性別報名參與度", fontsize=16)
    ax.grid(axis="y", alpha=.3)
    for i, v in enumerate(df["平均每人項目"]):
        ax.text(i, v + 0.02, f"{v}", ha="center", fontsize=10)
    pdf.savefig(fig); plt.close(fig)


def _chart_event_popularity(pdf, df):
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    top = df.head(15)
    colors = {"track": "#3498db", "field": "#27ae60",
              "relay": "#9b59b6", "ball": "#e67e22"}
    ax.barh(top["項目"][::-1], top["報名數"][::-1],
            color=[colors.get(c, "#888") for c in top["類別"][::-1]])
    ax.set_xlabel("報名人數"); ax.set_title("項目熱門度 Top 15", fontsize=16)
    ax.grid(axis="x", alpha=.3)
    pdf.savefig(fig); plt.close(fig)


def _table_page(pdf, df, title):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.axis("off")
    ax.set_title(title, fontsize=16, pad=10)
    if df.empty:
        ax.text(0.5, 0.5, "(無資料)", ha="center", fontsize=14)
    else:
        tbl = ax.table(cellText=df.values.tolist(),
                       colLabels=df.columns.tolist(),
                       loc="upper center", cellLoc="center",
                       bbox=[0.05, 0.05, 0.9, 0.88])
        tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.4)
        for (r, c), cell in tbl.get_celld().items():
            if r == 0:
                cell.set_facecolor("#4472C4")
                cell.set_text_props(color="white", fontweight="bold")
    pdf.savefig(fig); plt.close(fig)


def main():
    cfg = load_config()
    data = analyze()
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    export_excel(data, OUT_DIR / f"成績分析_{stamp}.xlsx")
    export_pdf(data, OUT_DIR / f"成績分析_{stamp}.pdf", cfg["meet_info"])


if __name__ == "__main__":
    main()
