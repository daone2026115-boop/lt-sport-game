#!/usr/bin/env bash
set -e

DB=/app/data/sportmeet.db

if [ ! -f "$DB" ]; then
    echo "=== 首次啟動：建立資料庫與示範資料 ==="
    python db_init.py
    python make_demo_data.py
    python import_data.py students templates/students_demo.xlsx
    python import_data.py events templates/events_demo.xlsx
    python import_data.py bib
    python import_data.py regs templates/registrations_demo.xlsx
    python create_accounts.py
    echo "=== 初始化完成 ==="
fi

case "$1" in
    web)
        echo "啟動網頁：http://localhost:${FLASK_PORT:-5000}"
        exec python -X utf8 web_app.py
        ;;
    shell)
        exec /bin/bash
        ;;
    pytest)
        pip install --no-cache-dir pytest
        exec pytest tests/ -v
        ;;
    *)
        exec "$@"
        ;;
esac
