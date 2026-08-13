# -*- coding: utf-8 -*-
"""Web 介面：學生線上自主報名、公開查詢頁"""
import sqlite3
from functools import wraps
from pathlib import Path

import csv
import io
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, Response)
from werkzeug.security import check_password_hash, generate_password_hash

from rules import DB_PATH, load_config, can_register, register, unregister

BASE = Path(__file__).parent
app = Flask(__name__,
            template_folder=str(BASE / "web" / "templates"),
            static_folder=str(BASE / "web" / "static"))
app.secret_key = "sportmeet-dev-key-change-in-prod"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def login_required(role=None):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if "user_id" not in session:
                return redirect(url_for("login", next=request.path))
            if role and session.get("role") != role:
                flash("權限不足", "error")
                return redirect(url_for("home"))
            return f(*a, **kw)
        return wrapper
    return deco


def _full_title(meet):
    """組合完整名稱：校名+學制+賽事名 (回退到 name 欄位)"""
    school = meet.get("school_name", "").strip()
    level = meet.get("school_level", "").strip()
    ev = meet.get("event_type") or meet.get("name") or "運動會"
    return f"{school}{level}{ev}"


@app.context_processor
def inject_globals():
    cfg = load_config()
    meet = dict(cfg["meet_info"])
    meet["full_title"] = _full_title(meet)
    return {
        "meet": meet,
        "current_rule": cfg["track_field_rules"]["active_option"],
        "rule_detail": cfg["track_field_rules"]["options"][cfg["track_field_rules"]["active_option"]],
        "user": session.get("username"),
        "role": session.get("role"),
    }


@app.route("/")
def home():
    conn = db()
    stats = {
        "students": conn.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "regs": conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0],
    }
    conn.close()
    return render_template("home.html", stats=stats)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        conn = db()
        row = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        conn.close()
        if row and check_password_hash(row["password_hash"], p):
            session["user_id"] = row["user_id"]
            session["username"] = row["username"]
            session["role"] = row["role"]
            session["student_id"] = row["student_id"]
            flash(f"歡迎 {u}", "success")
            return redirect(request.args.get("next") or url_for("home"))
        flash("帳號或密碼錯誤", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/change_password", methods=["GET", "POST"])
@login_required()
def change_password():
    if request.method == "POST":
        old = request.form.get("old", "")
        new = request.form.get("new", "")
        new2 = request.form.get("new2", "")
        if new != new2 or len(new) < 4:
            flash("新密碼不一致或太短（至少 4 字）", "error")
            return redirect(url_for("change_password"))
        conn = db()
        row = conn.execute("SELECT password_hash FROM users WHERE user_id=?",
                           (session["user_id"],)).fetchone()
        if not check_password_hash(row["password_hash"], old):
            conn.close()
            flash("舊密碼錯誤", "error")
            return redirect(url_for("change_password"))
        conn.execute("UPDATE users SET password_hash=? WHERE user_id=?",
                     (generate_password_hash(new), session["user_id"]))
        conn.commit()
        conn.close()
        flash("密碼已更新", "success")
        return redirect(url_for("home"))
    return render_template("change_password.html")


@app.route("/me")
@login_required(role="student")
def me():
    sid = session["student_id"]
    conn = db()
    stu = conn.execute("SELECT * FROM students WHERE student_id=?", (sid,)).fetchone()
    regs = conn.execute("""SELECT e.event_id, e.code, e.name, e.category
                           FROM registrations r JOIN events e ON r.event_id=e.event_id
                           WHERE r.student_id=? ORDER BY e.category""", (sid,)).fetchall()
    all_events = conn.execute("""SELECT event_id, code, name, category, gender, grade_limit
                                  FROM events WHERE category != 'ball' ORDER BY category, name""").fetchall()
    conn.close()
    # 過濾學生能報的
    eligible = []
    for e in all_events:
        if e["gender"] != "MIX" and e["gender"] != stu["gender"]:
            continue
        gl = str(e["grade_limit"] or "").strip()
        if gl and gl.lower() != "nan":
            allowed = [int(x) for x in gl.split(",") if x.strip().isdigit()]
            if allowed and stu["grade"] not in allowed:
                continue
        eligible.append(e)
    return render_template("me.html", stu=stu, regs=regs, events=eligible)


@app.route("/register_event", methods=["POST"])
@login_required(role="student")
def do_register():
    sid = session["student_id"]
    eid = int(request.form["event_id"])
    ok, msg = register(sid, eid)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("me"))


@app.route("/unregister_event", methods=["POST"])
@login_required(role="student")
def do_unregister():
    sid = session["student_id"]
    eid = int(request.form["event_id"])
    if unregister(sid, eid):
        flash("已退報", "success")
    else:
        flash("找不到報名紀錄", "error")
    return redirect(url_for("me"))


@app.route("/events")
def events():
    conn = db()
    rows = conn.execute("""SELECT e.event_id, e.code, e.name, e.category, e.gender,
                                  e.grade_limit, e.record_value, e.unit,
                                  COUNT(r.reg_id) as n_reg
                           FROM events e LEFT JOIN registrations r ON e.event_id=r.event_id
                           GROUP BY e.event_id ORDER BY e.category, e.name""").fetchall()
    conn.close()
    return render_template("events.html", events=rows)


@app.route("/event/<int:eid>")
def event_detail(eid):
    conn = db()
    ev = conn.execute("SELECT * FROM events WHERE event_id=?", (eid,)).fetchone()
    if not ev:
        conn.close()
        return "找不到項目", 404
    regs = conn.execute("""SELECT s.student_id, s.bib_number, s.name, s.grade, s.class_no
                           FROM registrations r JOIN students s ON r.student_id=s.student_id
                           WHERE r.event_id=? ORDER BY s.grade, s.class_no, s.seat_no""",
                        (eid,)).fetchall()
    heats = conn.execute("""SELECT h.heat_id, h.heat_no, h.round FROM heats h
                            WHERE h.event_id=? ORDER BY h.heat_no""", (eid,)).fetchall()
    heat_data = []
    for h in heats:
        members = conn.execute("""SELECT ha.lane, s.bib_number, s.name, s.grade, s.class_no, ha.team_code
                                   FROM heat_assignments ha
                                   LEFT JOIN students s ON ha.student_id=s.student_id
                                   WHERE ha.heat_id=? ORDER BY ha.lane""", (h["heat_id"],)).fetchall()
        heat_data.append((h, members))
    results = conn.execute("""SELECT res.rank, res.performance, res.broke_record, res.points,
                                     s.bib_number, s.name, s.grade, s.class_no
                              FROM results res LEFT JOIN students s ON res.student_id=s.student_id
                              WHERE res.event_id=? ORDER BY res.rank""", (eid,)).fetchall()
    matches = conn.execute("""SELECT * FROM ball_matches WHERE event_id=? ORDER BY match_id""",
                           (eid,)).fetchall()
    conn.close()
    return render_template("event_detail.html", ev=ev, regs=regs, heats=heat_data,
                           results=results, matches=matches)


@app.route("/standings")
def standings():
    conn = db()
    rows = conn.execute("""SELECT s.grade, s.class_no,
                                  SUM(res.points) as total_pts,
                                  COUNT(res.result_id) as n_wins,
                                  SUM(res.broke_record) as n_records
                           FROM results res JOIN students s ON res.student_id=s.student_id
                           WHERE res.rank <= 8 AND res.rank > 0
                           GROUP BY s.grade, s.class_no
                           ORDER BY total_pts DESC""").fetchall()
    conn.close()
    return render_template("standings.html", rows=rows)


@app.route("/scoreboard")
def scoreboard():
    """公開即時公告板 (30 秒自動重新整理)"""
    conn = db()
    latest = conn.execute("""
        SELECT e.name AS event, s.name AS name, s.grade || '-' || s.class_no AS cls,
               r.rank, r.performance, r.broke_record, e.unit
        FROM results r JOIN events e ON r.event_id = e.event_id
        LEFT JOIN students s ON r.student_id = s.student_id
        WHERE r.rank IS NOT NULL AND r.rank > 0
        ORDER BY r.result_id DESC LIMIT 20
    """).fetchall()
    standings = conn.execute("""
        SELECT s.grade AS grade, s.class_no AS class_no,
               COALESCE(SUM(r.points), 0) AS total_pts,
               COUNT(r.result_id) AS n_wins,
               COALESCE(SUM(r.broke_record), 0) AS n_records
        FROM students s LEFT JOIN results r ON r.student_id=s.student_id
        AND r.rank BETWEEN 1 AND 8
        GROUP BY s.grade, s.class_no
        HAVING total_pts > 0 OR n_wins > 0
        ORDER BY total_pts DESC LIMIT 10
    """).fetchall()
    records = conn.execute("""
        SELECT e.name AS event, s.name AS name, s.grade || '-' || s.class_no AS cls,
               r.performance, e.unit
        FROM results r JOIN events e ON r.event_id=e.event_id
        LEFT JOIN students s ON r.student_id=s.student_id
        WHERE r.broke_record=1 ORDER BY r.result_id DESC LIMIT 10
    """).fetchall()
    conn.close()
    return render_template("scoreboard.html",
                           latest=latest, standings=standings, records=records)


@app.route("/export/<kind>.csv")
def export_csv(kind):
    """公開 CSV 匯出：standings / results / registrations"""
    conn = db()
    if kind == "standings":
        rows = conn.execute("""
            SELECT s.grade AS 年級, s.class_no AS 班級,
                   COALESCE(SUM(r.points), 0) AS 總積分,
                   COUNT(r.result_id) AS 入圍次數,
                   COALESCE(SUM(r.broke_record), 0) AS 破紀錄次數
            FROM students s LEFT JOIN results r ON r.student_id=s.student_id
            AND r.rank BETWEEN 1 AND 8
            GROUP BY s.grade, s.class_no ORDER BY 總積分 DESC""").fetchall()
    elif kind == "results":
        rows = conn.execute("""
            SELECT e.code AS 代碼, e.name AS 項目,
                   r.rank AS 名次, s.grade AS 年, s.class_no AS 班,
                   s.name AS 姓名, s.bib_number AS 號碼布,
                   r.performance AS 成績, e.unit AS 單位,
                   r.broke_record AS 破紀錄, r.points AS 積分
            FROM results r JOIN events e ON r.event_id=e.event_id
            LEFT JOIN students s ON r.student_id=s.student_id
            ORDER BY e.category, e.name, r.rank""").fetchall()
    elif kind == "registrations":
        rows = conn.execute("""
            SELECT e.code AS 項目代碼, e.name AS 項目,
                   s.student_id AS 學號, s.name AS 姓名,
                   s.grade AS 年, s.class_no AS 班, s.bib_number AS 號碼布
            FROM registrations reg JOIN events e ON reg.event_id=e.event_id
            JOIN students s ON reg.student_id=s.student_id
            ORDER BY e.category, e.name, s.grade, s.class_no, s.seat_no""").fetchall()
    else:
        conn.close()
        return "unknown kind", 404
    conn.close()
    if not rows:
        return "no data", 204
    buf = io.StringIO()
    buf.write("﻿")  # BOM for Excel UTF-8
    w = csv.writer(buf)
    w.writerow(rows[0].keys())
    for r in rows:
        w.writerow(list(r))
    return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={kind}.csv"})


@app.route("/admin/config", methods=["GET", "POST"])
@login_required(role="admin")
def admin_config():
    import json as _json
    cfg_path = BASE / "config.json"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = _json.load(f)

    if request.method == "POST":
        try:
            cfg["meet_info"]["school_name"] = request.form.get("school_name", "").strip()
            cfg["meet_info"]["school_level"] = request.form.get("school_level", "").strip()
            cfg["meet_info"]["event_type"] = request.form.get("event_type", "").strip()
            cfg["meet_info"]["year"] = int(request.form["meet_year"])
            cfg["meet_info"]["date"] = request.form["meet_date"].strip()
            # 保留 name 欄位向後相容
            cfg["meet_info"]["name"] = f"{cfg['meet_info']['school_level']}{cfg['meet_info']['event_type']}"

            pts = [int(x.strip()) for x in request.form["individual_points"].split(",")
                   if x.strip()]
            cfg["scoring_rules"]["individual_points"] = pts
            cfg["scoring_rules"]["relay_points_multiplier"] = int(request.form["relay_mul"])
            cfg["scoring_rules"]["record_break_bonus"] = int(request.form["record_bonus"])
            cfg["scoring_rules"]["team_ranking_top_n"] = int(request.form["top_n"])

            cfg["ball_game_rules"]["active_format"] = request.form["ball_format"]
            cfg["grouping"]["track_lanes_per_group"] = int(request.form["lanes"])
            cfg["grouping"]["field_group_size"] = int(request.form["field_size"])

            with open(cfg_path, "w", encoding="utf-8") as f:
                _json.dump(cfg, f, ensure_ascii=False, indent=2)
            flash("設定已儲存並立即生效", "success")
        except (ValueError, KeyError) as e:
            flash(f"欄位錯誤：{e}", "error")
        return redirect(url_for("admin_config"))

    return render_template("admin_config.html", cfg=cfg)


@app.route("/api/rule_status")
def api_rule_status():
    cfg = load_config()
    return jsonify(cfg["track_field_rules"])


@app.route("/admin/batch", methods=["GET", "POST"])
@login_required(role="admin")
def admin_batch():
    conn = db()
    if request.method == "POST":
        results = []
        for key, val in request.form.items():
            if not key.startswith("ev_") or not val:
                continue
            # ev_<student_id>_<slot>
            try:
                _, sid, _ = key.split("_", 2)
                eid = int(val)
            except (ValueError, IndexError):
                continue
            ok, msg = register(sid, eid)
            if not ok and msg != "已報名此項目":
                results.append((sid, msg))
        conn.close()
        if results:
            for sid, msg in results[:15]:
                flash(f"{sid}: {msg}", "error")
            if len(results) > 15:
                flash(f"...另外還有 {len(results) - 15} 筆失敗", "error")
        else:
            flash("批次登錄完成", "success")
        return redirect(url_for("admin_batch",
                                grade=request.form.get("grade"),
                                class_no=request.form.get("class_no")))

    classes = conn.execute("SELECT DISTINCT grade, class_no FROM students "
                           "ORDER BY grade, class_no").fetchall()
    grade = request.args.get("grade", type=int)
    cls = request.args.get("class_no", type=int)
    students = []
    events_by_gender = {"M": {"individual": [], "relay": []},
                        "F": {"individual": [], "relay": []}}
    cfg = load_config()
    rule = cfg["track_field_rules"]["options"][cfg["track_field_rules"]["active_option"]]
    n_ind_slots = max(1, min(rule["individual_max"], 6))
    n_relay_slots = 3 if rule["relay_max"] >= 999 else max(1, min(rule["relay_max"], 4))
    if grade and cls:
        students_raw = conn.execute("""SELECT * FROM students WHERE grade=? AND class_no=?
                                        ORDER BY seat_no""", (grade, cls)).fetchall()
        for s in students_raw:
            regs = conn.execute("""SELECT e.event_id, e.code, e.name, e.category
                                    FROM registrations r JOIN events e ON r.event_id=e.event_id
                                    WHERE r.student_id=? ORDER BY e.category""",
                                 (s["student_id"],)).fetchall()
            students.append((s, regs))
        for g in ("M", "F"):
            evs = conn.execute("""SELECT event_id, code, name, category, gender, grade_limit
                                   FROM events WHERE category IN ('track','field','relay')
                                   AND (gender=? OR gender='MIX') ORDER BY category, name""",
                                (g,)).fetchall()
            for e in evs:
                gl = str(e["grade_limit"] or "").strip()
                if gl and gl.lower() != "nan":
                    allowed = [int(x) for x in gl.split(",") if x.strip().isdigit()]
                    if allowed and grade not in allowed:
                        continue
                slot = "relay" if e["category"] == "relay" else "individual"
                events_by_gender[g][slot].append(e)
    conn.close()
    return render_template("admin_batch.html", classes=classes,
                           grade=grade, class_no=cls,
                           students=students, events=events_by_gender,
                           n_ind_slots=n_ind_slots, n_relay_slots=n_relay_slots,
                           active_rule=cfg["track_field_rules"]["active_option"],
                           rule=rule)


@app.route("/admin/unregister", methods=["POST"])
@login_required(role="admin")
def admin_unregister():
    sid = request.form["student_id"]
    eid = int(request.form["event_id"])
    unregister(sid, eid)
    return redirect(url_for("admin_batch",
                            grade=request.form.get("grade"),
                            class_no=request.form.get("class_no")))


@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    conn = db()
    stats = {
        "students": conn.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "regs": conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0],
        "heats": conn.execute("SELECT COUNT(*) FROM heats").fetchone()[0],
        "results": conn.execute("SELECT COUNT(*) FROM results").fetchone()[0],
        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
    }
    unregistered = conn.execute("""
        SELECT COUNT(*) FROM students s WHERE NOT EXISTS
        (SELECT 1 FROM registrations r WHERE r.student_id=s.student_id)""").fetchone()[0]
    conn.close()
    return render_template("admin_dashboard.html", stats=stats, unregistered=unregistered)


@app.route("/admin/students", methods=["GET", "POST"])
@login_required(role="admin")
def admin_students():
    from import_data import import_students, assign_bib_numbers
    from create_accounts import create_student_accounts
    conn = db()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            sid = request.form["student_id"].strip()
            try:
                data = (sid, request.form["name"].strip(),
                        int(request.form["grade"]), int(request.form["class_no"]),
                        int(request.form.get("seat_no") or 0),
                        request.form["gender"])
                conn.execute("""INSERT INTO students(student_id, name, grade, class_no,
                                seat_no, gender) VALUES(?,?,?,?,?,?)""", data)
                conn.commit()
                flash(f"已新增 {data[1]}", "success")
            except sqlite3.IntegrityError:
                flash(f"學號 {sid} 已存在", "error")
            except (ValueError, KeyError) as e:
                flash(f"欄位錯誤：{e}", "error")

        elif action == "delete":
            sid = request.form["student_id"]
            conn.execute("DELETE FROM registrations WHERE student_id=?", (sid,))
            conn.execute("DELETE FROM users WHERE student_id=?", (sid,))
            conn.execute("DELETE FROM students WHERE student_id=?", (sid,))
            conn.commit()
            flash(f"已刪除 {sid} 及其報名與帳號", "success")

        elif action == "assign_bibs":
            conn.close()
            assign_bib_numbers()
            flash("已重新產生所有參賽號碼", "success")
            return redirect(url_for("admin_students"))

        elif action == "create_accounts":
            conn.close()
            create_student_accounts()
            flash("已為新學生建立帳號（初始密碼＝學號）", "success")
            return redirect(url_for("admin_students"))

        elif action == "upload":
            f = request.files.get("file")
            if not f or not f.filename.lower().endswith((".xlsx", ".xls")):
                flash("請選 Excel 檔 (.xlsx / .xls)", "error")
            else:
                tmp_dir = BASE / "data" / "uploads"
                tmp_dir.mkdir(exist_ok=True)
                tmp = tmp_dir / f.filename
                f.save(str(tmp))
                try:
                    conn.close()
                    import_students(str(tmp))
                    assign_bib_numbers()
                    create_student_accounts()
                    flash("已匯入學生 + 產生號碼 + 建立帳號", "success")
                except Exception as e:
                    flash(f"匯入失敗：{e}", "error")
                finally:
                    tmp.unlink(missing_ok=True)
                return redirect(url_for("admin_students"))

        conn.close()
        return redirect(url_for("admin_students",
                                grade=request.form.get("grade_filter"),
                                class_no=request.form.get("class_filter")))

    grade = request.args.get("grade", type=int)
    cls = request.args.get("class_no", type=int)
    sql = "SELECT * FROM students WHERE 1=1"; params = []
    if grade: sql += " AND grade=?"; params.append(grade)
    if cls:   sql += " AND class_no=?"; params.append(cls)
    sql += " ORDER BY grade, class_no, seat_no"
    students = conn.execute(sql, params).fetchall()
    classes = conn.execute("SELECT DISTINCT grade, class_no FROM students "
                           "ORDER BY grade, class_no").fetchall()
    conn.close()
    return render_template("admin_students.html", students=students,
                           classes=classes, grade=grade, class_no=cls)


@app.route("/admin/rules", methods=["GET", "POST"])
@login_required(role="admin")
def admin_rules():
    import json as _json
    cfg_path = BASE / "config.json"
    with open(cfg_path, encoding="utf-8") as f:
        cfg = _json.load(f)

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_option":
            name = request.form["name"].strip()
            try:
                opt = {
                    "individual_max": int(request.form["individual_max"]),
                    "field_max": int(request.form["field_max"]),
                    "track_max": int(request.form["track_max"]),
                    "relay_max": int(request.form["relay_max"]),
                }
                if request.form.get("category_exclusive"):
                    opt["category_exclusive"] = True
            except (ValueError, KeyError):
                flash("欄位需為整數", "error")
                return redirect(url_for("admin_rules"))
            cfg["track_field_rules"]["options"][name] = opt
            flash(f"規則「{name}」已儲存", "success")

        elif action == "delete_option":
            name = request.form["name"]
            if name == cfg["track_field_rules"]["active_option"]:
                flash("不能刪除目前使用中的規則", "error")
            elif len(cfg["track_field_rules"]["options"]) <= 1:
                flash("至少需要保留一組規則", "error")
            else:
                cfg["track_field_rules"]["options"].pop(name, None)
                flash(f"已刪除「{name}」", "success")

        elif action == "activate":
            name = request.form["name"]
            if name in cfg["track_field_rules"]["options"]:
                cfg["track_field_rules"]["active_option"] = name
                flash(f"目前規則已切換為「{name}」", "success")

        with open(cfg_path, "w", encoding="utf-8") as f:
            _json.dump(cfg, f, ensure_ascii=False, indent=2)
        return redirect(url_for("admin_rules"))

    return render_template("admin_rules.html",
                           options=cfg["track_field_rules"]["options"],
                           active=cfg["track_field_rules"]["active_option"])


@app.route("/admin/upload", methods=["GET", "POST"])
@login_required(role="admin")
def admin_upload():
    from import_data import import_registrations
    if request.method == "POST":
        f = request.files.get("file")
        if not f or not f.filename.lower().endswith((".xlsx", ".xls")):
            flash("請選擇 Excel 檔 (.xlsx / .xls)", "error")
            return redirect(url_for("admin_upload"))
        dry_run = request.form.get("dry_run") == "1"
        tmp_dir = BASE / "data" / "uploads"
        tmp_dir.mkdir(exist_ok=True)
        tmp = tmp_dir / f.filename
        f.save(str(tmp))
        try:
            ok_n, fail_n, errors = import_registrations(str(tmp), dry_run=dry_run)
        except Exception as e:
            flash(f"匯入失敗：{e}", "error")
            return redirect(url_for("admin_upload"))
        finally:
            tmp.unlink(missing_ok=True)
        return render_template("admin_upload_result.html",
                               ok_n=ok_n, fail_n=fail_n, errors=errors,
                               dry_run=dry_run, filename=f.filename)
    return render_template("admin_upload.html")


if __name__ == "__main__":
    import os
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") != "0"
    print(f"啟動網頁伺服器：http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}")
    print("學生登入：username = 學號，密碼 = 學號（首次登入請改密碼）")
    print("管理員登入：admin / admin123")
    app.run(host=host, port=port, debug=debug)
