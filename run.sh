#!/usr/bin/env bash
# ─────────────────────────────────────────
#  一鍵呼叫啟動 (macOS / Linux)
# ─────────────────────────────────────────
set -e
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python3}

echo ""
echo "=== [1/4] 檢查 Python ==="
$PYTHON --version || { echo "[X] 需 Python 3.10+"; exit 1; }

echo ""
echo "=== [2/4] 檢查套件 ==="
if ! $PYTHON -c "import flask, pandas, openpyxl, matplotlib" 2>/dev/null; then
    echo "缺少套件，執行安裝..."
    $PYTHON -m pip install -r requirements.txt
else
    echo "[OK] 套件齊全"
fi

echo ""
echo "=== [3/4] 檢查資料庫 ==="
if [ ! -f data/sportmeet.db ]; then
    echo "首次啟動，建立資料庫與示範資料..."
    $PYTHON db_init.py
    $PYTHON make_demo_data.py
    $PYTHON import_data.py students templates/students_demo.xlsx
    $PYTHON import_data.py events templates/events_demo.xlsx
    $PYTHON import_data.py bib
    $PYTHON import_data.py regs templates/registrations_demo.xlsx
    $PYTHON create_accounts.py
else
    echo "[OK] 資料庫已存在"
fi

echo ""
echo "=== [4/4] 啟動網頁 ==="
echo ""
echo "  ─────────────────────────────────────"
echo "   網址：http://127.0.0.1:5000"
echo "   管理員：admin / admin123"
echo "   學生：帳號=學號、密碼=學號"
echo "  ─────────────────────────────────────"
echo "  Ctrl+C 停止伺服器"
echo ""

# 5 秒後開瀏覽器 (背景)
(sleep 5 && (open http://127.0.0.1:5000 2>/dev/null || xdg-open http://127.0.0.1:5000 2>/dev/null)) &

exec $PYTHON -X utf8 web_app.py
