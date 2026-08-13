# 校內運動會報名及成績系統

[![Tests](https://github.com/daone2026115-boop/lt-sport-game/actions/workflows/tests.yml/badge.svg)](https://github.com/daone2026115-boop/lt-sport-game/actions/workflows/tests.yml)

一套為國中/國小校內運動會設計的完整系統：報名 → 分組 → 檢錄 → 成績 → 積分分析，全流程涵蓋。

**主要用途**：田徑賽個人/接力報名、球類賽制編排、號碼布產出、檢錄點名、成績登錄與班級積分計算。

---

## 系統畫面

### 首頁與公告板
| 首頁 | 即時公告板（30 秒自動更新） |
|---|---|
| ![首頁](screenshots/home.png) | ![公告板](screenshots/scoreboard.png) |

### 學生自主報名
| 登入 | 我的報名 |
|---|---|
| ![登入](screenshots/login.png) | ![我的報名](screenshots/student_me.png) |

### 管理員儀表板與批次報名
| 儀表板 | 批次報名（依班級）|
|---|---|
| ![儀表板](screenshots/admin_dashboard.png) | ![批次報名](screenshots/admin_batch.png) |

### 學生管理與規則設定
| 學生管理 | 報名規則設定 |
|---|---|
| ![學生管理](screenshots/admin_students.png) | ![規則設定](screenshots/admin_rules.png) |

### 全站設定與 Excel 上傳
| 全站設定（大會/積分/賽制）| Excel 上傳 |
|---|---|
| ![設定](screenshots/admin_config.png) | ![上傳](screenshots/admin_upload.png) |

### 公開查詢頁
| 項目清單 | 團體積分排行 |
|---|---|
| ![項目](screenshots/events.png) | ![積分](screenshots/standings.png) |

### 產出範例：號碼布（A4 每頁 3 張）
![號碼布](screenshots/bib_cloth_sample.png)

---

## 特色

- 🎯 **可設定報名規則**：內建「一田一徑 / 僅一項個人 / 二項不限田徑 / 田或徑二選一」，或自訂
- 🌐 **三種介面共用同一資料庫**：桌面 GUI (tkinter) / 網頁 (Flask) / 命令列 + Excel
- 🏃 **各年級獨立競賽**：項目按年級劃分，7/8/9 年級各自分組
- 🏅 **賽制可切換**：循環賽 / 單淘汰 / **雙淘汰** / 分組預賽+複賽
- 📄 **PDF 產出**：號碼布 (A4 3張)、分組分道表 (7 跑道)、檢錄點名單 (一欄一跑道 + 成績登記)、球類賽制表、成績分析報表
- 📢 **即時公告板**：30 秒自動更新，適合大螢幕投影
- 📊 **成績分析**：班級積分 + 個人英雄榜 + 破紀錄清單 + PDF 圖表
- 🔒 **學生自主線上報名**：帳號=學號、密碼自定，套用規則引擎

---

## 快速上手

### Windows（一鍵）
```
1. 雙擊 setup.bat  → 安裝套件 + 建立示範資料
2. 雙擊 start.bat  → 啟動網頁
3. 瀏覽器打開 http://127.0.0.1:5000
```

### macOS / Linux
```bash
bash setup.sh
python web_app.py
```

### 手動安裝
```bash
pip install -r requirements.txt
python db_init.py
python make_demo_data.py
python import_data.py students templates/students_demo.xlsx
python import_data.py events templates/events_demo.xlsx
python import_data.py bib
python import_data.py regs templates/registrations_demo.xlsx
python create_accounts.py
python web_app.py
```

### 登入資訊
| 身分 | 帳號 | 密碼 |
|---|---|---|
| 管理員 | `admin` | `admin123` |
| 學生 | 學號 (如 `70101`) | 學號 |

首次登入請立即改密碼。

---

## 主要頁面

| 網址 | 說明 | 需登入 |
|---|---|---|
| `/` | 首頁，統計數字 | 否 |
| `/events` | 全部項目清單 | 否 |
| `/event/<id>` | 項目詳細（含分組、成績、對戰）| 否 |
| `/standings` | 團體積分排行 + CSV 匯出 | 否 |
| `/scoreboard` | 📢 即時公告板 (30 秒自動更新) | 否 |
| `/me` | 學生：我的報名 | 學生 |
| `/admin` | 管理員儀表板 | admin |
| `/admin/students` | 學生管理（新增/刪除/上傳）| admin |
| `/admin/batch` | 批次報名（依班級）| admin |
| `/admin/upload` | 上傳 Excel 報名 | admin |
| `/admin/rules` | 報名規則設定 | admin |
| `/admin/config` | 全站設定（大會/積分/賽制/分組）| admin |
| `/export/standings.csv` | 匯出班級積分 CSV | 否 |
| `/export/results.csv` | 匯出全部成績 CSV | 否 |

---

## 產出檔案

執行下列指令產生於 `output/`：

```bash
python make_bib_cloth.py            # 號碼布 PDF (A4 每頁 3 張)
python make_bib_book.py             # 號碼簿 (每班一頁)
python make_grouping.py             # 田徑分組分道表 (PDF + Excel)
python make_bracket.py              # 球類賽制表 (依 active_format)
python make_checkin.py              # 檢錄點名單 (橫式，一欄一跑道)
python make_analysis.py             # 成績分析 (5 分頁 Excel + PDF 圖表)
python make_registration_form.py    # 填寫式 Excel 報名表 (下拉選單)
python make_registration_form.py each  # 每班一份
```

---

## 檔案結構

```
lt-sport-game/
├── config.json                     # 規則、積分、號碼格式設定
├── data/sportmeet.db               # SQLite 資料庫
├── templates/                      # Excel 範本
├── output/                         # 產出的 PDF / Excel
├── web/{templates,static}/         # Flask 網頁資源
│
├── rules.py                        # 報名規則引擎
├── scheduling.py                   # 分組/賽程演算法
├── db_init.py                      # 建立資料庫
├── import_data.py                  # 命令列匯入
├── create_accounts.py              # 批次建帳號
│
├── web_app.py                      # Flask 網頁
├── gui_app.py                      # tkinter 桌面
│
├── make_bib_cloth.py               # 號碼布
├── make_bib_book.py                # 號碼簿
├── make_grouping.py                # 分組分道
├── make_bracket.py                 # 賽制表
├── make_checkin.py                 # 檢錄點名單
├── make_analysis.py                # 成績分析
├── make_registration_form.py       # 填寫式報名表
├── make_demo_data.py               # 示範資料
│
├── tests/                          # pytest 測試
├── setup.bat / setup.sh            # 一鍵初始化
├── start.bat                       # 啟動網頁
├── USER_MANUAL.md                  # 詳細操作手冊
└── requirements.txt                # Python 套件
```

---

## 執行測試

```bash
pip install pytest
pytest tests/ -v
```

規則引擎 11 個測試、分組/賽程演算法 13 個測試，共 24 項。

---

## 詳細操作手冊

見 **[USER_MANUAL.md](USER_MANUAL.md)**，涵蓋班導工作流程、學生自報流程、管理員操作、常見問題等。

---

## 授權

MIT License
