# -*- coding: utf-8 -*-
"""批次建立學生帳號 + 管理員帳號"""
import sqlite3
import sys
from werkzeug.security import generate_password_hash

from rules import DB_PATH


def create_student_accounts(default_pwd_source="student_id"):
    """為每位學生建立帳號。username=student_id, 初始密碼=學號"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT student_id, name FROM students")
    students = cur.fetchall()
    n_new = n_skip = 0
    for sid, name in students:
        pwd = sid if default_pwd_source == "student_id" else "123456"
        pw_hash = generate_password_hash(pwd)
        try:
            cur.execute("""INSERT INTO users(student_id, username, password_hash, role)
                           VALUES(?,?,?,'student')""", (sid, sid, pw_hash))
            n_new += 1
        except sqlite3.IntegrityError:
            n_skip += 1
    conn.commit()
    conn.close()
    print(f"[OK] 學生帳號：新增 {n_new}、已存在略過 {n_skip}")
    print(f"     初始密碼 = 學號本身，請提醒學生首次登入後修改")


def create_admin(username="admin", password="admin123"):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    pw_hash = generate_password_hash(password)
    try:
        cur.execute("""INSERT INTO users(username, password_hash, role) VALUES(?,?,'admin')""",
                    (username, pw_hash))
        print(f"[OK] 管理員 {username} 已建立，密碼 = {password}（請立即修改）")
    except sqlite3.IntegrityError:
        print(f"[!] 管理員 {username} 已存在")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "admin":
        pwd = sys.argv[2] if len(sys.argv) > 2 else "admin123"
        create_admin(password=pwd)
    else:
        create_student_accounts()
        create_admin()
