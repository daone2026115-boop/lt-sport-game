# -*- coding: utf-8 -*-
"""桌面 GUI：學生報名、成績登錄、報名總覽"""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from rules import can_register, register, unregister, DB_PATH, load_config
from import_data import import_registrations


class SportMeetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        cfg = load_config()
        meet = cfg["meet_info"]
        self.title(f"{meet['year']} {meet['name']} 報名系統")
        self.geometry("1100x650")
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("vista")
        except tk.TclError:
            pass

        self._build_header()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=4)
        self.tab_reg = RegistrationTab(nb)
        self.tab_score = ScoreEntryTab(nb)
        self.tab_view = OverviewTab(nb)
        nb.add(self.tab_reg, text="  學生報名  ")
        nb.add(self.tab_score, text="  成績登錄  ")
        nb.add(self.tab_view, text="  報名總覽  ")
        nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _build_header(self):
        cfg = load_config()
        rules = cfg["track_field_rules"]
        active = rules["active_option"]
        opt = rules["options"][active]
        header = ttk.Frame(self, padding=6)
        header.pack(fill="x")
        ttk.Label(header, text=f"目前規則：{active}",
                  font=("Microsoft JhengHei", 11, "bold")).pack(side="left")
        ttk.Label(header,
                  text=f"（個人上限 {opt['individual_max']}、田賽 {opt['field_max']}、"
                       f"徑賽 {opt['track_max']}、接力 {opt['relay_max']}）",
                  foreground="#666").pack(side="left", padx=8)

    def _on_tab_change(self, event):
        tab = event.widget.nametowidget(event.widget.select())
        if hasattr(tab, "refresh"):
            tab.refresh()


class RegistrationTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=4)
        ttk.Label(top, text="年級").pack(side="left")
        self.grade_cb = ttk.Combobox(top, width=6, state="readonly",
                                      values=["全部", "1", "2", "3", "4", "5", "6"])
        self.grade_cb.current(0)
        self.grade_cb.pack(side="left", padx=4)
        self.grade_cb.bind("<<ComboboxSelected>>", lambda e: self._reload_students())

        ttk.Label(top, text="班級").pack(side="left", padx=(8, 0))
        self.class_cb = ttk.Combobox(top, width=6, state="readonly", values=["全部"])
        self.class_cb.current(0)
        self.class_cb.pack(side="left", padx=4)
        self.class_cb.bind("<<ComboboxSelected>>", lambda e: self._reload_students())

        ttk.Label(top, text="姓名/學號").pack(side="left", padx=(8, 0))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._reload_students())
        ttk.Entry(top, textvariable=self.search_var, width=15).pack(side="left", padx=4)

        ttk.Button(top, text="📥 匯入報名 Excel", command=self._import_regs).pack(side="right", padx=4)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=6)

        left = ttk.LabelFrame(body, text="學生名單", padding=4)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        cols = ("student_id", "name", "grade", "class_no", "gender", "bib")
        self.stu_tree = ttk.Treeview(left, columns=cols, show="headings", height=20)
        for c, w, t in [("student_id", 80, "學號"), ("name", 100, "姓名"),
                         ("grade", 50, "年級"), ("class_no", 50, "班"),
                         ("gender", 50, "性別"), ("bib", 80, "號碼")]:
            self.stu_tree.heading(c, text=t)
            self.stu_tree.column(c, width=w, anchor="center")
        self.stu_tree.pack(fill="both", expand=True)
        self.stu_tree.bind("<<TreeviewSelect>>", lambda e: self._on_student_select())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(4, 0))

        reg_frame = ttk.LabelFrame(right, text="已報名項目", padding=4)
        reg_frame.pack(fill="both", expand=True)
        self.reg_tree = ttk.Treeview(reg_frame, columns=("code", "name", "cat"),
                                      show="headings", height=8)
        for c, w, t in [("code", 80, "代碼"), ("name", 180, "項目"), ("cat", 60, "類別")]:
            self.reg_tree.heading(c, text=t)
            self.reg_tree.column(c, width=w, anchor="center")
        self.reg_tree.pack(fill="both", expand=True)
        ttk.Button(reg_frame, text="退報選取項目", command=self._unreg).pack(pady=4)

        add_frame = ttk.LabelFrame(right, text="新增報名", padding=4)
        add_frame.pack(fill="both", expand=True, pady=(6, 0))
        ttk.Label(add_frame, text="選擇項目：").pack(anchor="w")
        self.event_cb = ttk.Combobox(add_frame, state="readonly", width=40)
        self.event_cb.pack(fill="x", pady=2)
        ttk.Button(add_frame, text="報名", command=self._reg).pack(pady=4)
        self.msg_lbl = ttk.Label(add_frame, text="", foreground="blue")
        self.msg_lbl.pack(anchor="w")

    def refresh(self):
        self._reload_class_options()
        self._reload_students()
        self._reload_events()

    def _reload_class_options(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT class_no FROM students ORDER BY class_no")
        classes = ["全部"] + [str(r[0]) for r in cur.fetchall()]
        conn.close()
        self.class_cb["values"] = classes
        if self.class_cb.get() not in classes:
            self.class_cb.current(0)

    def _reload_students(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        sql = "SELECT student_id, name, grade, class_no, gender, bib_number FROM students WHERE 1=1"
        params = []
        g = self.grade_cb.get()
        if g and g != "全部":
            sql += " AND grade=?"
            params.append(int(g))
        c = self.class_cb.get()
        if c and c != "全部":
            sql += " AND class_no=?"
            params.append(int(c))
        s = self.search_var.get().strip()
        if s:
            sql += " AND (student_id LIKE ? OR name LIKE ?)"
            params += [f"%{s}%", f"%{s}%"]
        sql += " ORDER BY grade, class_no, seat_no"
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        self.stu_tree.delete(*self.stu_tree.get_children())
        for r in rows:
            self.stu_tree.insert("", "end", values=r)

    def _reload_events(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT event_id, code, name, category, gender FROM events "
                    "WHERE category != 'ball' ORDER BY category, name")
        self._events = cur.fetchall()
        conn.close()
        self.event_cb["values"] = [f"[{e[3]}] {e[1]} {e[2]} ({e[4]})" for e in self._events]

    def _selected_student(self):
        sel = self.stu_tree.selection()
        if not sel:
            return None
        return self.stu_tree.item(sel[0], "values")[0]

    def _on_student_select(self):
        sid = self._selected_student()
        if not sid:
            return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT e.event_id, e.code, e.name, e.category FROM registrations r
            JOIN events e ON r.event_id = e.event_id
            WHERE r.student_id=? ORDER BY e.category
        """, (sid,))
        rows = cur.fetchall()
        conn.close()
        self.reg_tree.delete(*self.reg_tree.get_children())
        for r in rows:
            self.reg_tree.insert("", "end", iid=str(r[0]), values=(r[1], r[2], r[3]))

    def _reg(self):
        sid = self._selected_student()
        if not sid:
            self.msg_lbl.config(text="請先選學生", foreground="red")
            return
        idx = self.event_cb.current()
        if idx < 0:
            self.msg_lbl.config(text="請選項目", foreground="red")
            return
        eid = self._events[idx][0]
        ok, msg = register(sid, eid)
        self.msg_lbl.config(text=msg, foreground=("green" if ok else "red"))
        if ok:
            self._on_student_select()

    def _import_regs(self):
        path = filedialog.askopenfilename(
            title="選擇報名 Excel",
            filetypes=[("Excel 檔案", "*.xlsx *.xls")],
        )
        if not path:
            return
        try:
            ok_n, fail_n, errors = import_registrations(path)
        except Exception as e:
            messagebox.showerror("匯入失敗", str(e))
            return
        msg = f"成功 {ok_n} 筆，失敗 {fail_n} 筆"
        if errors:
            msg += "\n\n失敗清單:\n" + "\n".join(errors[:20])
            if len(errors) > 20:
                msg += f"\n...(還有 {len(errors) - 20} 筆)"
        messagebox.showinfo("匯入結果", msg)
        self._on_student_select()
        self._reload_students()

    def _unreg(self):
        sid = self._selected_student()
        sel = self.reg_tree.selection()
        if not sid or not sel:
            return
        eid = int(sel[0])
        if messagebox.askyesno("確認", "確定要退報此項目？"):
            unregister(sid, eid)
            self._on_student_select()


class ScoreEntryTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=4)
        ttk.Label(top, text="選擇項目：").pack(side="left")
        self.event_cb = ttk.Combobox(top, state="readonly", width=40)
        self.event_cb.pack(side="left", padx=4)
        self.event_cb.bind("<<ComboboxSelected>>", lambda e: self._load_participants())
        ttk.Button(top, text="儲存全部成績並排名", command=self._save_all).pack(side="right", padx=8)

        cols = ("student_id", "bib", "name", "class", "performance", "note")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=22)
        for c, w, t in [("student_id", 80, "學號"), ("bib", 80, "號碼"),
                         ("name", 100, "姓名"), ("class", 60, "班"),
                         ("performance", 100, "成績"), ("note", 100, "備註")]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=6)
        self.tree.bind("<Double-1>", self._edit_cell)

        self.msg_lbl = ttk.Label(self, text="提示：雙擊「成績」欄可直接輸入", foreground="#666")
        self.msg_lbl.pack(anchor="w")

    def refresh(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT event_id, code, name, category, unit FROM events "
                    "WHERE category != 'ball' ORDER BY category, name")
        self._events = cur.fetchall()
        conn.close()
        self.event_cb["values"] = [f"{e[1]} {e[2]}" for e in self._events]
        if self._events and self.event_cb.current() < 0:
            self.event_cb.current(0)
            self._load_participants()

    def _current_event(self):
        i = self.event_cb.current()
        if i < 0:
            return None
        return self._events[i]

    def _load_participants(self):
        ev = self._current_event()
        if not ev:
            return
        eid = ev[0]
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT s.student_id, s.bib_number, s.name, s.grade || '-' || s.class_no,
                   COALESCE(res.performance, ''), COALESCE(res.note, '')
            FROM registrations r
            JOIN students s ON r.student_id = s.student_id
            LEFT JOIN results res ON res.event_id=r.event_id AND res.student_id=s.student_id
            WHERE r.event_id=?
            ORDER BY s.grade, s.class_no, s.seat_no
        """, (eid,))
        rows = cur.fetchall()
        conn.close()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", iid=r[0], values=r)

    def _edit_cell(self, event):
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row_id or col not in ("#5", "#6"):
            return
        x, y, w, h = self.tree.bbox(row_id, col)
        val = self.tree.set(row_id, col)
        entry = ttk.Entry(self.tree)
        entry.insert(0, val)
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()

        def commit(_=None):
            self.tree.set(row_id, col, entry.get())
            entry.destroy()
        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Escape>", lambda e: entry.destroy())

    def _save_all(self):
        ev = self._current_event()
        if not ev:
            return
        eid, code, name, category, unit = ev
        cfg = load_config()
        points_table = cfg["scoring_rules"]["individual_points"]
        bonus = cfg["scoring_rules"]["record_break_bonus"]
        relay_mul = cfg["scoring_rules"]["relay_points_multiplier"]

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT record_value FROM events WHERE event_id=?", (eid,))
        record_val = cur.fetchone()[0]
        cur.execute("DELETE FROM results WHERE event_id=?", (eid,))

        rows = []
        for iid in self.tree.get_children():
            v = self.tree.item(iid, "values")
            sid, bib, sname, cls, perf, note = v
            if not str(perf).strip():
                continue
            try:
                perf_f = float(perf)
            except ValueError:
                continue
            rows.append((sid, perf_f, note))

        higher_better = category == "field"
        rows.sort(key=lambda r: r[1], reverse=higher_better)

        saved = 0
        for rank, (sid, perf_f, note) in enumerate(rows, 1):
            broke = 0
            if record_val is not None:
                if (higher_better and perf_f > record_val) or (not higher_better and perf_f < record_val):
                    broke = 1
            base = points_table[rank - 1] if rank <= len(points_table) else 0
            if category == "relay":
                base *= relay_mul
            pts = base + (bonus if broke else 0)
            cur.execute("""
                INSERT INTO results(event_id, student_id, performance, rank, broke_record, points, note)
                VALUES(?,?,?,?,?,?,?)
            """, (eid, sid, perf_f, rank, broke, pts, note))
            saved += 1
        conn.commit()
        conn.close()
        self.msg_lbl.config(text=f"已儲存 {saved} 筆成績並排名", foreground="green")
        self._load_participants()


class OverviewTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=4)
        ttk.Label(top, text="檢視方式：").pack(side="left")
        self.mode_cb = ttk.Combobox(top, state="readonly", width=15,
                                     values=["依項目", "依班級"])
        self.mode_cb.current(0)
        self.mode_cb.pack(side="left", padx=4)
        self.mode_cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        ttk.Button(top, text="重新整理", command=self.refresh).pack(side="left", padx=8)

        self.txt = tk.Text(self, wrap="none", font=("Consolas", 10))
        self.txt.pack(fill="both", expand=True, pady=6)
        yscroll = ttk.Scrollbar(self.txt, orient="vertical", command=self.txt.yview)
        yscroll.pack(side="right", fill="y")
        self.txt.config(yscrollcommand=yscroll.set)

    def refresh(self):
        self.txt.delete("1.0", "end")
        mode = self.mode_cb.get()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        if mode == "依項目":
            cur.execute("SELECT event_id, code, name, category FROM events ORDER BY category, name")
            for eid, code, ename, cat in cur.fetchall():
                cur.execute("""
                    SELECT s.bib_number, s.name, s.grade || '-' || s.class_no
                    FROM registrations r JOIN students s ON r.student_id=s.student_id
                    WHERE r.event_id=? ORDER BY s.grade, s.class_no, s.seat_no
                """, (eid,))
                members = cur.fetchall()
                self.txt.insert("end", f"\n【{cat}】{code}  {ename}  共 {len(members)} 人\n")
                for m in members:
                    self.txt.insert("end", f"    {m[0]:8s} {m[1]:10s} {m[2]}\n")
        else:
            cur.execute("SELECT DISTINCT grade, class_no FROM students ORDER BY grade, class_no")
            for g, c in cur.fetchall():
                cur.execute("""
                    SELECT s.bib_number, s.name, e.code, e.name, e.category
                    FROM students s
                    JOIN registrations r ON s.student_id=r.student_id
                    JOIN events e ON r.event_id=e.event_id
                    WHERE s.grade=? AND s.class_no=?
                    ORDER BY s.seat_no, e.category
                """, (g, c))
                rows = cur.fetchall()
                self.txt.insert("end", f"\n===== {g} 年 {c} 班（共 {len(rows)} 項報名）=====\n")
                cur_bib = None
                for bib, sname, ecode, ename, cat in rows:
                    if bib != cur_bib:
                        self.txt.insert("end", f"\n  {bib} {sname}\n")
                        cur_bib = bib
                    self.txt.insert("end", f"      [{cat:6s}] {ecode} {ename}\n")
        conn.close()


if __name__ == "__main__":
    if not DB_PATH.exists():
        print("找不到資料庫，請先執行 db_init.py")
        raise SystemExit(1)
    app = SportMeetApp()
    app.mainloop()
