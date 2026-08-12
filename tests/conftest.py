# -*- coding: utf-8 -*-
"""共用測試 fixture：建立臨時 SQLite DB 與示範學生/項目"""
import sqlite3
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """建立臨時 DB，並讓 rules.DB_PATH 指向它"""
    import rules
    import db_init

    path = tmp_path / "test.db"
    monkeypatch.setattr(rules, "DB_PATH", path)
    monkeypatch.setattr(db_init, "DB_PATH", path)
    db_init.init_db()

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # 三位學生
    students = [
        ("70101", "王小明", 7, 1, 1, "M"),
        ("70102", "陳小華", 7, 1, 2, "F"),
        ("80301", "林大明", 8, 3, 1, "M"),
    ]
    cur.executemany("""INSERT INTO students(student_id, name, grade, class_no,
                        seat_no, gender) VALUES(?,?,?,?,?,?)""", students)

    # 各類項目
    events = [
        ("G7M100", "7年級男子100m", "track", "M", "7", 13.5, None, 2024, "秒"),
        ("G7F100", "7年級女子100m", "track", "F", "7", 15.0, None, 2024, "秒"),
        ("G7MLJ",  "7年級男子跳遠", "field", "M", "7", 4.50, None, 2024, "公尺"),
        ("G7MSP",  "7年級男子鉛球", "field", "M", "7", 8.50, None, 2024, "公尺"),
        ("G7M4X100", "7年級男子接力", "relay", "M", "7", 55.0, None, 2024, "秒"),
        ("G8M100", "8年級男子100m", "track", "M", "8", 13.0, None, 2024, "秒"),
    ]
    cur.executemany("""INSERT INTO events(code, name, category, gender,
                        grade_limit, record_value, record_holder,
                        record_year, unit)
                       VALUES(?,?,?,?,?,?,?,?,?)""", events)
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def config_rule(monkeypatch, tmp_path):
    """回傳一個能切換 active_option 的 helper，並臨時寫入 config"""
    import rules
    orig_config_path = rules.CONFIG_PATH
    tmp_config = tmp_path / "config.json"

    def set_rule(individual_max=2, field_max=1, track_max=1,
                 relay_max=999, category_exclusive=False):
        import json
        cfg = {
            "meet_info": {"name": "測試賽", "year": 2026, "date": "2026-01-01"},
            "track_field_rules": {
                "active_option": "測試",
                "options": {
                    "測試": {
                        "individual_max": individual_max,
                        "field_max": field_max,
                        "track_max": track_max,
                        "relay_max": relay_max,
                    }
                },
            },
            "ball_game_rules": {"active_format": "循環賽",
                                 "formats": ["循環賽"], "team_unit": "班級",
                                 "min_players_per_team": 5,
                                 "max_players_per_team": 12},
            "scoring_rules": {"individual_points": [9, 7, 6, 5, 4, 3, 2, 1],
                              "relay_points_multiplier": 2,
                              "record_break_bonus": 3,
                              "team_ranking_top_n": 8},
            "number_encoding": {"individual_format": "{grade}{class_no:02d}-{seq:02d}",
                                 "team_format": "{grade}{class_no:02d}"},
            "grouping": {"track_lanes_per_group": 7,
                          "field_group_size": 10, "seeding_method": "snake"},
        }
        if category_exclusive:
            cfg["track_field_rules"]["options"]["測試"]["category_exclusive"] = True
        with open(tmp_config, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        monkeypatch.setattr(rules, "CONFIG_PATH", tmp_config)

    return set_rule
