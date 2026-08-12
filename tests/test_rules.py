# -*- coding: utf-8 -*-
"""規則引擎測試"""
import pytest


def _get_eid(db_path, code):
    import sqlite3
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT event_id FROM events WHERE code=?", (code,)).fetchone()
    conn.close()
    return row[0]


def test_basic_register(db_path, config_rule):
    from rules import register
    config_rule()
    ok, msg = register("70101", _get_eid(db_path, "G7M100"))
    assert ok, msg
    assert msg == "報名成功"


def test_gender_mismatch(db_path, config_rule):
    from rules import register
    config_rule()
    # 男生報女子項目
    ok, msg = register("70101", _get_eid(db_path, "G7F100"))
    assert not ok
    assert "性別" in msg


def test_grade_mismatch(db_path, config_rule):
    from rules import register
    config_rule()
    # 7 年級學生報 8 年級項目
    ok, msg = register("70101", _get_eid(db_path, "G8M100"))
    assert not ok
    assert "年級" in msg


def test_individual_limit_一田一徑(db_path, config_rule):
    """一田一徑：個人上限 2，田 1、徑 1"""
    from rules import register
    config_rule(individual_max=2, field_max=1, track_max=1)
    # 徑賽 ✓
    ok, _ = register("70101", _get_eid(db_path, "G7M100"))
    assert ok
    # 田賽 ✓
    ok, _ = register("70101", _get_eid(db_path, "G7MLJ"))
    assert ok
    # 第二個田賽 ✗ (田賽上限 1)
    ok, msg = register("70101", _get_eid(db_path, "G7MSP"))
    assert not ok
    assert "田賽已達上限" in msg


def test_only_one_individual(db_path, config_rule):
    """僅一項個人"""
    from rules import register
    config_rule(individual_max=1, field_max=999, track_max=999)
    register("70101", _get_eid(db_path, "G7M100"))
    ok, msg = register("70101", _get_eid(db_path, "G7MLJ"))
    assert not ok
    assert "個人項目已達上限" in msg


def test_category_exclusive(db_path, config_rule):
    """田或徑二選一：報了徑就不能報田"""
    from rules import register
    config_rule(individual_max=1, field_max=1, track_max=1,
                category_exclusive=True)
    ok, _ = register("70101", _get_eid(db_path, "G7M100"))  # 徑
    assert ok
    ok, msg = register("70101", _get_eid(db_path, "G7MLJ"))  # 田應被擋
    assert not ok
    assert "田賽或" in msg or "徑賽" in msg


def test_category_exclusive_field_first(db_path, config_rule):
    """田或徑二選一：報了田就不能報徑"""
    from rules import register
    config_rule(individual_max=1, field_max=1, track_max=1,
                category_exclusive=True)
    register("70101", _get_eid(db_path, "G7MLJ"))
    ok, msg = register("70101", _get_eid(db_path, "G7M100"))
    assert not ok
    assert "田賽或" in msg or "徑賽" in msg


def test_relay_unlimited(db_path, config_rule):
    """接力上限 999：接力不受個人上限影響"""
    from rules import register
    config_rule(individual_max=1)
    register("70101", _get_eid(db_path, "G7M100"))
    ok, _ = register("70101", _get_eid(db_path, "G7M4X100"))
    assert ok, "接力應可另外報"


def test_no_duplicate(db_path, config_rule):
    from rules import register
    config_rule()
    register("70101", _get_eid(db_path, "G7M100"))
    ok, msg = register("70101", _get_eid(db_path, "G7M100"))
    assert not ok
    assert "已報名" in msg


def test_unregister(db_path, config_rule):
    from rules import register, unregister
    config_rule()
    eid = _get_eid(db_path, "G7M100")
    register("70101", eid)
    assert unregister("70101", eid)
    assert not unregister("70101", eid)  # 第二次應失敗


def test_unregister_frees_slot(db_path, config_rule):
    """退報後應能報回同上限"""
    from rules import register, unregister
    config_rule(individual_max=1)
    register("70101", _get_eid(db_path, "G7M100"))
    unregister("70101", _get_eid(db_path, "G7M100"))
    ok, _ = register("70101", _get_eid(db_path, "G7MLJ"))
    assert ok
