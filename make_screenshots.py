# -*- coding: utf-8 -*-
"""自動截圖 Web 頁面 + 從 PDF 產出預覽 PNG，供 README 使用"""
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent
SHOT_DIR = BASE / "screenshots"
SHOT_DIR.mkdir(exist_ok=True)

URL = "http://127.0.0.1:5000"


def take_web_shots():
    from playwright.sync_api import sync_playwright

    pages = [
        ("home", "/", None, None),
        ("events", "/events", None, None),
        ("scoreboard", "/scoreboard", None, None),
        ("standings", "/standings", None, None),
        ("login", "/login", None, None),
        ("student_me", "/me", "student", None),
        ("admin_dashboard", "/admin", "admin", None),
        ("admin_students", "/admin/students", "admin", None),
        ("admin_batch", "/admin/batch?grade=9&class_no=1", "admin", None),
        ("admin_rules", "/admin/rules", "admin", None),
        ("admin_config", "/admin/config", "admin", None),
        ("admin_upload", "/admin/upload", "admin", None),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 螢幕大小類似筆電
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        page = ctx.new_page()

        # 登入 admin
        page.goto(f"{URL}/login")
        page.fill("input[name=username]", "admin")
        page.fill("input[name=password]", "admin123")
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")

        for name, path, role, extra in pages:
            if role == "student":
                page.goto(f"{URL}/logout")
                page.goto(f"{URL}/login")
                page.fill("input[name=username]", "70101")
                page.fill("input[name=password]", "70101")
                page.click("button[type=submit]")
                page.wait_for_load_state("networkidle")
            elif role == "admin":
                # 若目前是 student，重新登入 admin
                if page.url.endswith("/me"):
                    page.goto(f"{URL}/logout")
                    page.goto(f"{URL}/login")
                    page.fill("input[name=username]", "admin")
                    page.fill("input[name=password]", "admin123")
                    page.click("button[type=submit]")
                    page.wait_for_load_state("networkidle")

            page.goto(f"{URL}{path}")
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            out = SHOT_DIR / f"{name}.png"
            page.screenshot(path=str(out), full_page=True)
            print(f"[OK] {name}: {out}")

        browser.close()


def render_pdf_previews():
    """把 PDF 第一頁轉 PNG (用 matplotlib 直接重繪)"""
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Noto Sans CJK TC", "Noto Sans CJK JP", "WenQuanYi Micro Hei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    # 用 make_bib_cloth 產第一位學生的號碼布
    from make_bib_cloth import fetch_students_with_events, draw_bib_strip
    from rules import load_config
    cfg = load_config()
    students = fetch_students_with_events()[:3]
    if students:
        fig, axes = plt.subplots(3, 1, figsize=(8.27, 11.69))
        for ax in axes: ax.axis("off")
        for j, (sid, bib, name, g, c, ev) in enumerate(students):
            draw_bib_strip(axes[j], bib, name, f"{g} 年 {c} 班", ev,
                            cfg["meet_info"]["year"], cfg["meet_info"]["name"])
        plt.subplots_adjust(left=0.02, right=0.98, top=0.98,
                             bottom=0.02, hspace=0.08)
        out = SHOT_DIR / "bib_cloth_sample.png"
        fig.savefig(out, dpi=100, bbox_inches="tight")
        plt.close(fig)
        print(f"[OK] {out}")

    # 用 make_checkin 產第一組
    from make_checkin import fetch_all_heats, draw_track_relay, draw_field
    heats = fetch_all_heats()
    track_heat = next((h for h in heats if h['cat'] == 'track'), None)
    if track_heat:
        from matplotlib.backends.backend_pdf import PdfPages
        from tempfile import NamedTemporaryFile
        tmp = NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        with PdfPages(tmp.name) as pdf:
            draw_track_relay(pdf, track_heat, cfg["meet_info"], 7)
        # 用 pdftoppm 或者直接重畫
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.axis("off")
        from make_checkin import draw_track_relay as _
        # 重新畫到 fig 而不是 pdf
        # 簡化：直接告訴 user 看 PDF
    print("[提示] 檢錄單 PDF 可另存 PNG 由 output/檢錄點名單_*.pdf 截取")


if __name__ == "__main__":
    print("=== Web 截圖 ===")
    take_web_shots()
    print("\n=== PDF 預覽 ===")
    render_pdf_previews()
    print("\n[完成] 全部截圖存在 screenshots/")
