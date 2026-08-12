# -*- coding: utf-8 -*-
"""命令列報名工具（第一階段驗證用）"""
import sqlite3
import sys
from rules import register, unregister, DB_PATH


def list_events():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT event_id, code, name, category, gender FROM events ORDER BY category, event_id")
    print(f"{'ID':4s} {'代碼':10s} {'項目':20s} {'類別':6s} 性別")
    print("-" * 60)
    for r in cur.fetchall():
        print(f"{r[0]:<4d} {r[1]:10s} {r[2]:20s} {r[3]:6s} {r[4]}")
    conn.close()


def list_student_regs(student_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name, bib_number FROM students WHERE student_id=?", (student_id,))
    s = cur.fetchone()
    if not s:
        print(f"找不到學生 {student_id}")
        conn.close()
        return
    print(f"學生: {s[0]}  號碼: {s[1]}")
    cur.execute("""
        SELECT e.code, e.name, e.category FROM registrations r
        JOIN events e ON r.event_id = e.event_id
        WHERE r.student_id=? ORDER BY e.category
    """, (student_id,))
    for r in cur.fetchall():
        print(f"  [{r[2]:6s}] {r[0]:10s} {r[1]}")
    conn.close()


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python register_cli.py events                          # 列出所有項目")
        print("  python register_cli.py list <student_id>               # 查看某生報名")
        print("  python register_cli.py add <student_id> <event_id>     # 報名")
        print("  python register_cli.py del <student_id> <event_id>     # 退報")
        return
    cmd = sys.argv[1]
    if cmd == "events":
        list_events()
    elif cmd == "list":
        list_student_regs(sys.argv[2])
    elif cmd == "add":
        ok, msg = register(sys.argv[2], int(sys.argv[3]))
        print(("[OK] " if ok else "[X] ") + msg)
    elif cmd == "del":
        ok = unregister(sys.argv[2], int(sys.argv[3]))
        print("[OK] 已退報" if ok else "[X] 找不到報名紀錄")
    else:
        print(f"未知指令: {cmd}")


if __name__ == "__main__":
    main()
