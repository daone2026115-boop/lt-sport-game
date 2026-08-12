# -*- coding: utf-8 -*-
"""匯入 Excel 到 SQLite：學生名冊、賽事項目、產生參賽號碼"""
import json
import sqlite3
import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).parent
DB_PATH = BASE / "data" / "sportmeet.db"
CONFIG_PATH = BASE / "config.json"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def import_students(xlsx_path):
    df = pd.read_excel(xlsx_path, dtype={"student_id": str})
    required = {"student_id", "name", "grade", "class_no", "gender"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少欄位: {missing}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n_new = n_upd = 0
    for _, r in df.iterrows():
        cur.execute("SELECT 1 FROM students WHERE student_id=?", (str(r["student_id"]),))
        exists = cur.fetchone()
        cur.execute("""
            INSERT OR REPLACE INTO students(student_id, name, grade, class_no, seat_no, gender)
            VALUES(?,?,?,?,?,?)
        """, (str(r["student_id"]), r["name"], int(r["grade"]), int(r["class_no"]),
              int(r.get("seat_no", 0) or 0), r["gender"]))
        if exists:
            n_upd += 1
        else:
            n_new += 1
    conn.commit()
    conn.close()
    print(f"[OK] 學生匯入完成：新增 {n_new}、更新 {n_upd}")


def _s(v):
    """安全轉字串：NaN/None → 空字串"""
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


def import_events(xlsx_path):
    df = pd.read_excel(xlsx_path)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n = 0
    for _, r in df.iterrows():
        cur.execute("""
            INSERT INTO events(code, name, category, gender, grade_limit,
                               record_value, record_holder, record_year, unit)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                category=excluded.category,
                gender=excluded.gender,
                grade_limit=excluded.grade_limit,
                record_value=excluded.record_value,
                record_holder=excluded.record_holder,
                record_year=excluded.record_year,
                unit=excluded.unit
        """, (r["code"], r["name"], r["category"], r["gender"],
              _s(r.get("grade_limit")),
              r["record_value"] if pd.notna(r.get("record_value")) else None,
              _s(r.get("record_holder")),
              int(r["record_year"]) if pd.notna(r.get("record_year")) else None,
              _s(r.get("unit"))))
        n += 1
    conn.commit()
    conn.close()
    print(f"[OK] 賽事匯入完成：{n} 項")


def assign_bib_numbers():
    """依 config 號碼格式產生每位學生的參賽號碼"""
    cfg = load_config()
    fmt = cfg["number_encoding"]["individual_format"]
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT student_id, grade, class_no, seat_no FROM students ORDER BY grade, class_no, seat_no")
    rows = cur.fetchall()
    by_class = {}
    for sid, g, c, seat in rows:
        by_class.setdefault((g, c), []).append((sid, seat))

    n = 0
    for (g, c), members in by_class.items():
        for seq, (sid, seat) in enumerate(members, 1):
            bib = fmt.format(grade=g, class_no=c, seq=seq)
            cur.execute("UPDATE students SET bib_number=? WHERE student_id=?", (bib, sid))
            n += 1
    conn.commit()
    conn.close()
    print(f"[OK] 已產生 {n} 個參賽號碼")


def import_registrations(xlsx_path, dry_run=False):
    """批次匯入報名。長格式：一列 = 一位選手報一項"""
    from rules import can_register, register
    df = pd.read_excel(xlsx_path, dtype={"student_id": str})
    required = {"student_id", "event_code"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少欄位: {missing}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT code, event_id FROM events")
    code_to_id = {r[0]: r[1] for r in cur.fetchall()}
    cur.execute("SELECT student_id, name FROM students")
    sid_to_name = {r[0]: r[1] for r in cur.fetchall()}
    conn.close()

    ok_n = fail_n = 0
    errors = []
    for i, r in df.iterrows():
        sid = str(r["student_id"]).strip()
        code = str(r["event_code"]).strip()
        row_no = i + 2  # +2 for 1-indexed + header row

        if sid not in sid_to_name:
            errors.append(f"第 {row_no} 列: 學號 {sid} 不存在")
            fail_n += 1
            continue
        if code not in code_to_id:
            errors.append(f"第 {row_no} 列: 項目代碼 {code} 不存在")
            fail_n += 1
            continue

        eid = code_to_id[code]
        if dry_run:
            ok, msg = can_register(sid, eid)
        else:
            ok, msg = register(sid, eid)

        if ok:
            ok_n += 1
        else:
            fail_n += 1
            errors.append(f"第 {row_no} 列: {sid_to_name[sid]}({sid}) 報 {code} → {msg}")

    mode = "試算" if dry_run else "匯入"
    print(f"[結果] 報名{mode}：成功 {ok_n}、失敗 {fail_n}")
    if errors:
        print("\n失敗清單:")
        for e in errors:
            print(f"  - {e}")
    return ok_n, fail_n, errors


def show_status():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for tbl in ["students", "events", "registrations", "teams", "results"]:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"  {tbl:15s}: {cur.fetchone()[0]}")
    conn.close()


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python import_data.py students <xlsx>")
        print("  python import_data.py events <xlsx>")
        print("  python import_data.py regs <xlsx>          # 批次匯入報名")
        print("  python import_data.py regs <xlsx> --check  # 只試算不寫入")
        print("  python import_data.py bib                  # 產生參賽號碼")
        print("  python import_data.py status               # 查看資料庫狀態")
        return
    cmd = sys.argv[1]
    if cmd == "students":
        import_students(sys.argv[2])
    elif cmd == "events":
        import_events(sys.argv[2])
    elif cmd == "regs":
        dry = "--check" in sys.argv
        import_registrations(sys.argv[2], dry_run=dry)
    elif cmd == "bib":
        assign_bib_numbers()
    elif cmd == "status":
        show_status()
    else:
        print(f"未知指令: {cmd}")


if __name__ == "__main__":
    main()
