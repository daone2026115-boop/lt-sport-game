# -*- coding: utf-8 -*-
"""產生 Excel 匯入範本：學生名冊、賽事項目"""
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
TEMPLATE_DIR = BASE / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)


def make_student_template():
    df = pd.DataFrame({
        "student_id": ["1010101", "1010102", "1010103"],
        "name": ["王小明", "陳小華", "林小美"],
        "grade": [1, 1, 1],
        "class_no": [1, 1, 1],
        "seat_no": [1, 2, 3],
        "gender": ["M", "M", "F"],
    })
    path = TEMPLATE_DIR / "students_template.xlsx"
    df.to_excel(path, index=False)
    print(f"[OK] 學生名冊範本: {path}")


def make_event_template():
    df = pd.DataFrame({
        "code":     ["M100M", "F100M", "M200M", "MLJ", "FLJ", "M4X100", "BOYBBALL"],
        "name":     ["男子100公尺", "女子100公尺", "男子200公尺", "男子跳遠", "女子跳遠", "男子4x100接力", "男子籃球"],
        "category": ["track", "track", "track", "field", "field", "relay", "ball"],
        "gender":   ["M", "F", "M", "M", "F", "M", "M"],
        "grade_limit": ["", "", "", "", "", "", ""],
        "record_value":  [12.5, 13.8, 25.4, 5.20, 4.50, 52.3, None],
        "record_holder": ["", "", "", "", "", "", ""],
        "record_year":   [2024, 2024, 2024, 2024, 2024, 2024, None],
        "unit":     ["秒", "秒", "秒", "公尺", "公尺", "秒", "場"],
    })
    path = TEMPLATE_DIR / "events_template.xlsx"
    df.to_excel(path, index=False)
    print(f"[OK] 賽事項目範本: {path}")


def make_registration_template():
    df = pd.DataFrame({
        "student_id": ["1010101", "1010101", "1010101", "1010102", "1010103"],
        "student_name": ["王小明", "王小明", "王小明", "陳小華", "林小美"],
        "event_code": ["M100M", "MLJ", "M4X100", "M100M", "F100M"],
        "event_name": ["男子100公尺", "男子跳遠", "男子4x100接力", "男子100公尺", "女子100公尺"],
    })
    path = TEMPLATE_DIR / "registrations_template.xlsx"
    df.to_excel(path, index=False)
    print(f"[OK] 報名匯入範本: {path}")
    print("     必要欄位: student_id, event_code (name 欄位僅供對照參考)")


if __name__ == "__main__":
    make_student_template()
    make_event_template()
    make_registration_template()
