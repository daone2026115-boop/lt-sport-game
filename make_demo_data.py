# -*- coding: utf-8 -*-
"""產生國中運動會示範資料：7/8/9 年級，每年級獨立競賽（項目按年級分開）"""
import random
from pathlib import Path
import pandas as pd

random.seed(42)
BASE = Path(__file__).parent
TEMPLATE_DIR = BASE / "templates"

surnames = "王陳林張李黃吳劉蔡楊許鄭謝洪郭邱曾廖賴徐周葉蘇莊呂江"
given_m = ["俊傑", "彥廷", "宗翰", "冠宇", "承恩", "柏翰", "家豪", "志豪", "威廷", "書豪"]
given_f = ["怡君", "雅婷", "淑芬", "佳蓉", "冠妤", "宜臻", "郁婷", "詩涵", "欣宜", "品妍"]


def gen_students():
    """3 個年級 × 3 個班級 × 20 位學生 = 180 人"""
    rows = []
    for grade in [7, 8, 9]:
        for cls in range(1, 4):
            for seat in range(1, 21):
                gender = "M" if seat <= 10 else "F"
                surname = random.choice(surnames)
                given = random.choice(given_m if gender == "M" else given_f)
                sid = f"{grade}{cls:02d}{seat:02d}"
                rows.append({"student_id": sid, "name": surname + given,
                             "grade": grade, "class_no": cls,
                             "seat_no": seat, "gender": gender})
    df = pd.DataFrame(rows)
    path = TEMPLATE_DIR / "students_demo.xlsx"
    df.to_excel(path, index=False)
    print(f"[OK] 示範學生: {path}  ({len(df)} 人)")


def gen_events():
    """各年級獨立項目：以 G7/G8/G9 前綴區分，grade_limit 只填該年級"""
    # 各年級的個人項目 (code_suffix, name, category, record_M, record_F, unit)
    grade_events = {
        7: [
            ("100M",  "100公尺",   "track", 14.0, 15.0, "秒"),
            ("200M",  "200公尺",   "track", 29.0, 32.0, "秒"),
            ("LJ",    "跳遠",       "field", 4.50, 3.80, "公尺"),
            ("SP",    "壘球擲遠",   "field", 45.0, 30.0, "公尺"),
        ],
        8: [
            ("100M",  "100公尺",   "track", 13.5, 14.5, "秒"),
            ("200M",  "200公尺",   "track", 28.0, 31.0, "秒"),
            ("400M",  "400公尺",   "track", 64.0, 72.0, "秒"),
            ("LJ",    "跳遠",       "field", 5.00, 4.20, "公尺"),
            ("HJ",    "跳高",       "field", 1.45, 1.25, "公尺"),
            ("SHOT",  "鉛球",       "field", 9.00, 7.00, "公尺"),
        ],
        9: [
            ("100M",  "100公尺",   "track", 12.8, 14.0, "秒"),
            ("200M",  "200公尺",   "track", 26.5, 30.0, "秒"),
            ("400M",  "400公尺",   "track", 60.0, 70.0, "秒"),
            ("800M",  "800公尺",   "track", 140.0, 155.0, "秒"),
            ("1500M", "1500公尺",  "track", 290.0, 330.0, "秒"),
            ("LJ",    "跳遠",       "field", 5.30, 4.50, "公尺"),
            ("HJ",    "跳高",       "field", 1.55, 1.35, "公尺"),
            ("SHOT",  "鉛球",       "field", 10.00, 7.80, "公尺"),
        ],
    }
    # 接力
    grade_relays = {
        7: [("4X100",       "4x100接力",       55.0, 60.0)],
        8: [("4X100",       "4x100接力",       52.0, 58.0)],
        9: [("4X100",       "4x100接力",       50.0, 56.0),
            ("4X400",       "4x400接力(1600m)", 300.0, 340.0)],
    }
    # 大隊接力、球類（籃排羽桌）、帶式橄欖球、拔河
    team_events = [
        ("CLASSRELAY", "大隊接力",     "relay", "MIX", 240.0, "秒"),
        ("BBALL_M",    "男子籃球",     "ball",  "M",   None, "場"),
        ("BBALL_F",    "女子籃球",     "ball",  "F",   None, "場"),
        ("VBALL_M",    "男子排球",     "ball",  "M",   None, "場"),
        ("VBALL_F",    "女子排球",     "ball",  "F",   None, "場"),
        ("BADM_M",     "男子羽球",     "ball",  "M",   None, "場"),
        ("BADM_F",     "女子羽球",     "ball",  "F",   None, "場"),
        ("TT_M",       "男子桌球",     "ball",  "M",   None, "場"),
        ("TT_F",       "女子桌球",     "ball",  "F",   None, "場"),
        ("RUGBY",      "帶式橄欖球",   "ball",  "MIX", None, "場"),
        ("TUGOFWAR",   "拔河",         "ball",  "MIX", None, "場"),
    ]

    rows = []
    for grade in [7, 8, 9]:
        for suf, cname, cat, rec_m, rec_f, unit in grade_events[grade]:
            for gender, rec in [("M", rec_m), ("F", rec_f)]:
                zh = "男" if gender == "M" else "女"
                rows.append((f"G{grade}{gender}{suf}",
                             f"{grade}年級{zh}子{cname}", cat, gender,
                             str(grade), rec, unit))
        for suf, cname, rec_m, rec_f in grade_relays[grade]:
            for gender, rec in [("M", rec_m), ("F", rec_f)]:
                zh = "男" if gender == "M" else "女"
                rows.append((f"G{grade}{gender}{suf}",
                             f"{grade}年級{zh}子{cname}", "relay", gender,
                             str(grade), rec, "秒"))
        for suf, cname, cat, gender, rec, unit in team_events:
            rows.append((f"G{grade}{suf}",
                         f"{grade}年級{cname}", cat, gender,
                         str(grade), rec, unit))

    df = pd.DataFrame(rows, columns=["code", "name", "category", "gender",
                                       "grade_limit", "record_value", "unit"])
    df["record_holder"] = ""
    df["record_year"] = 2024
    df = df[["code", "name", "category", "gender", "grade_limit",
             "record_value", "record_holder", "record_year", "unit"]]
    path = TEMPLATE_DIR / "events_demo.xlsx"
    df.to_excel(path, index=False)
    print(f"[OK] 示範項目: {path}  ({len(df)} 項)")


def gen_registrations():
    """每位學生依 grade / gender 隨機報 1-3 項合法項目"""
    stu = pd.read_excel(TEMPLATE_DIR / "students_demo.xlsx", dtype={"student_id": str})
    evt = pd.read_excel(TEMPLATE_DIR / "events_demo.xlsx")

    rows = []
    for _, s in stu.iterrows():
        g = s["grade"]
        gender = s["gender"]
        avail = evt[(evt["grade_limit"].astype(str) == str(g))
                    & ((evt["gender"] == gender) | (evt["gender"] == "MIX"))]
        picks = []
        track = avail[avail["category"] == "track"]
        field = avail[avail["category"] == "field"]
        relay = avail[avail["category"] == "relay"]
        ball  = avail[avail["category"] == "ball"]
        if len(track) > 0 and random.random() < 0.55:
            picks.append(track.sample(1).iloc[0])
        if len(field) > 0 and random.random() < 0.35:
            picks.append(field.sample(1).iloc[0])
        if len(relay) > 0 and random.random() < 0.4:
            picks.append(relay.sample(1).iloc[0])
        if len(ball) > 0 and random.random() < 0.4:
            picks.append(ball.sample(1).iloc[0])
        for e in picks:
            rows.append({"student_id": s["student_id"], "student_name": s["name"],
                         "event_code": e["code"], "event_name": e["name"]})

    df = pd.DataFrame(rows)
    path = TEMPLATE_DIR / "registrations_demo.xlsx"
    df.to_excel(path, index=False)
    print(f"[OK] 示範報名: {path}  ({len(df)} 筆)")


if __name__ == "__main__":
    gen_students()
    gen_events()
    gen_registrations()
    print("\n下一步：")
    print("  python import_data.py students templates/students_demo.xlsx")
    print("  python import_data.py events templates/events_demo.xlsx")
    print("  python import_data.py bib")
    print("  python import_data.py regs templates/registrations_demo.xlsx")
