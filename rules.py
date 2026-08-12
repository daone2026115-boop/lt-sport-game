# -*- coding: utf-8 -*-
"""報名規則引擎：依 config.json 檢核學生報名是否合法"""
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"
DB_PATH = BASE / "data" / "sportmeet.db"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_active_track_rules():
    cfg = load_config()
    rules = cfg["track_field_rules"]
    return rules["options"][rules["active_option"]]


def count_current_registrations(cur, student_id):
    cur.execute("""
        SELECT e.category, COUNT(*) FROM registrations r
        JOIN events e ON r.event_id = e.event_id
        WHERE r.student_id = ?
        GROUP BY e.category
    """, (student_id,))
    counts = {"track": 0, "field": 0, "relay": 0, "ball": 0}
    for cat, n in cur.fetchall():
        counts[cat] = n
    individual = counts["track"] + counts["field"]
    return individual, counts["field"], counts["track"], counts["relay"]


def can_register(student_id, event_id):
    rules = get_active_track_rules()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT category, gender, grade_limit, name FROM events WHERE event_id=?", (event_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "找不到此項目"
    category, ev_gender, grade_limit, ev_name = row

    cur.execute("SELECT gender, grade FROM students WHERE student_id=?", (student_id,))
    srow = cur.fetchone()
    if not srow:
        conn.close()
        return False, "找不到此學生"
    st_gender, st_grade = srow

    if ev_gender != "MIX" and ev_gender != st_gender:
        conn.close()
        return False, f"性別不符（項目限{ev_gender}）"

    if grade_limit and str(grade_limit).lower() not in ("", "nan", "none"):
        try:
            allowed = [int(x) for x in str(grade_limit).split(",") if x.strip().isdigit()]
        except ValueError:
            allowed = []
        if allowed and st_grade not in allowed:
            conn.close()
            return False, f"年級不符（項目限{grade_limit}年級）"

    cur.execute("SELECT 1 FROM registrations WHERE student_id=? AND event_id=?", (student_id, event_id))
    if cur.fetchone():
        conn.close()
        return False, "已報名此項目"

    ind, field_n, track_n, relay_n = count_current_registrations(cur, student_id)
    conn.close()

    if category == "field":
        if rules.get("category_exclusive") and track_n > 0:
            return False, "此規則限只能報「田賽」或「徑賽」其中一類"
        if field_n + 1 > rules["field_max"]:
            return False, f"田賽已達上限 {rules['field_max']} 項"
        if ind + 1 > rules["individual_max"]:
            return False, f"個人項目已達上限 {rules['individual_max']} 項"
    elif category == "track":
        if rules.get("category_exclusive") and field_n > 0:
            return False, "此規則限只能報「田賽」或「徑賽」其中一類"
        if track_n + 1 > rules["track_max"]:
            return False, f"徑賽已達上限 {rules['track_max']} 項"
        if ind + 1 > rules["individual_max"]:
            return False, f"個人項目已達上限 {rules['individual_max']} 項"
    elif category == "relay":
        if relay_n + 1 > rules["relay_max"]:
            return False, f"接力已達上限 {rules['relay_max']} 項"

    return True, "OK"


def register(student_id, event_id, team_code=None):
    ok, msg = can_register(student_id, event_id)
    if not ok:
        return False, msg
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO registrations(student_id, event_id, team_code) VALUES(?,?,?)",
                (student_id, event_id, team_code))
    conn.commit()
    conn.close()
    return True, "報名成功"


def unregister(student_id, event_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM registrations WHERE student_id=? AND event_id=?", (student_id, event_id))
    n = cur.rowcount
    conn.commit()
    conn.close()
    return n > 0
