# 校內運動會報名及成績系統 — 操作手冊

## 〇、適用範圍與比賽制度

- **適用**：國中運動會（7/8/9 年級），也可用於國小（1-6 年級）
- **競賽方式**：**各年級獨立競賽**，項目依年級分開設置（例：`G7M100M` = 7 年級男子 100 公尺）
- **報名對象**：學生只能報名自己年級的項目（由 `grade_limit` 欄自動限定）
- **示範資料**：預設 3 年級 × 3 班 × 20 人 = 180 位學生，可用 `python make_demo_data.py` 重新產出

## 一、系統簡介

專為國小校內運動會設計，涵蓋田徑賽、球類賽的報名、分組、成績登錄、賽制編排與報表產出。三種介面共用同一 SQLite 資料庫：

| 介面 | 適用對象 | 用途 |
|---|---|---|
| **Web 網頁** | 學生自主報名、班導批次報名、體育組管理 | 主要操作介面 |
| **桌面 GUI** | 現場成績登錄 | 比賽當日 |
| **Excel + 命令列** | 大量匯入 / 產出 PDF 報表 | 前置與收尾 |

---

## 二、快速上手（新學年度五步驟）

```bash
cd "C:/Users/DW/AI/lt sport game"

python db_init.py                                     # 1. 建立資料庫
python import_data.py students <學生名冊.xlsx>        # 2. 匯入學生
python import_data.py events <賽事項目.xlsx>          # 3. 匯入項目
python import_data.py bib                             # 4. 產生號碼
python create_accounts.py                             # 5. 建立帳號
python web_app.py                                     # 啟動 → http://127.0.0.1:5000
```

**登入資訊**
- 學生：帳號 = 學號、密碼 = 學號（初次登入請改）
- 管理員：`admin` / `admin123`（**請立即修改**）

---

## 三、班級導師工作流程

### A. 用網頁批次報名（推薦，最快）
1. 到 http://127.0.0.1:5000 用 admin 登入
2. 點「儀表板 → 批次報名」
3. 選你的班級
4. 每位學生下拉選要報的項目 → 送出
5. 系統會即時檢核規則，違規會顯示原因

### B. 用 Excel 收單再上傳
1. 執行 `python make_registration_form.py each` 產出各班表單
2. 你的班：`templates/報名表_3年1班.xlsx`
3. 打開表 → 「報名表」分頁 → 每人下拉選項目
4. 儲存後上傳：admin 登入 →「上傳」→ 選檔案 → 送出

---

## 四、學生自主報名（可選）

1. 學生用瀏覽器打開 http://127.0.0.1:5000
2. 用學號登入（初次密碼 = 學號）
3. 點右上「改密碼」
4. 點「我的報名」→ 選項目 → 送出
5. 違反規則會擋下並顯示原因

---

## 五、管理員操作

### 儀表板 `/admin`
顯示總覽、未報名學生數、快速連結。

### 學生管理 `/admin/students`
- 新增一位學生（單筆表單）
- 批次上傳 Excel（自動產號碼、建帳號）
- 刪除學生（連同報名與帳號）
- 依年級 / 班級過濾檢視

### 報名規則 `/admin/rules`
內建 4 種規則：
| 規則名稱 | 個人上限 | 田賽 | 徑賽 | 接力 | 特殊 |
|---|---|---|---|---|---|
| 僅一項個人 | 1 | 999 | 999 | 999 | |
| 一田一徑 | 2 | 1 | 1 | 999 | |
| 二項個人不限田徑 | 2 | 999 | 999 | 999 | |
| 田或徑二選一 | 1 | 1 | 1 | 999 | 田/徑二選一類 |

**操作**：
- 直接改每欄數字 → 儲存
- 點「設為使用中」切換
- 表格下方可新增自訂規則
- 「田徑二選一」勾選後：學生只能報田賽或徑賽其中一類

### 批次報名 `/admin/batch`
- 選班級 → 每位學生一列，下拉選項目
- 下拉格數會依「目前規則」的個人上限自動調整
- 已報項目顯示為 chip，可點 × 直接退報

### Excel 上傳 `/admin/upload`
- 支援 `registrations_template.xlsx` 與 `報名表_XXX.xlsx`
- 可勾「只試算不寫入」先驗證資料

---

## 六、比賽前產出檔案

在 `output/` 資料夾產出（檔名帶時間戳，不會覆蓋）：

```bash
python make_bib_cloth.py    # 號碼布 PDF（A4 每頁 3 張，含姓名+項目）
python make_grouping.py     # 田徑分組分道表（PDF + Excel）
python make_bracket.py      # 球類賽制表（依 config.active_format）
python make_checkin.py      # 檢錄組簽到單（橫式，含個人賽項目）
python make_bib_book.py     # 號碼簿（每班一頁的名單）
```

### 切換球類賽制
編輯 `config.json` 的 `ball_game_rules.active_format`：
- `"循環賽"`（預設）
- `"單淘汰"`
- `"分組預賽加複賽"`
然後重跑 `python make_bracket.py`。

---

## 七、比賽當天

### 現場成績登錄（桌面 GUI）
```bash
python gui_app.py
```
分頁 2「成績登錄」：
1. 選項目
2. 雙擊「成績」欄輸入成績
3. 按「儲存全部成績並排名」→ 自動排名 + 給積分 + 標記破紀錄

### 網頁即時查詢
- 選手 / 家長：連 http://127.0.0.1:5000 查項目、查分組、查即時成績
- 團體積分排行：`/standings` 即時計算

---

## 八、賽後分析

```bash
python make_analysis.py
```

產出兩份檔：
- **Excel 5 分頁**：班級積分 / 個人英雄榜 / 破紀錄清單 / 項目報名數 / 參與統計
- **PDF 圖表**：班級積分長條圖、年級性別參與度、項目熱門度等

---

## 九、常見問題

| 問題 | 解法 |
|---|---|
| 學生無法登入 | admin →「學生管理」→ 按「建立缺少的帳號」 |
| 號碼布是空的 | admin →「學生管理」→ 按「重產號碼」 |
| 分道表沒有新項目 | 重跑 `python make_grouping.py` |
| 賽制換了但 PDF 沒變 | 改 `config.json` 的 `active_format` 後重跑 `make_bracket.py` |
| 想匯入更多學生 | Web 學生管理頁「批次上傳 Excel」，或 `python import_data.py students xxx.xlsx` |
| 想改一人可報項目數 | Web `/admin/rules` 直接改個人上限 |
| 資料庫壞了 | 刪掉 `data/sportmeet.db` 重新跑第二節五步驟 |

---

## 十、檔案結構速查

```
C:/Users/DW/AI/lt sport game/
├── config.json                 # 規則、積分、號碼格式設定
├── data/sportmeet.db           # SQLite 資料庫（勿刪）
├── templates/                  # Excel 範本、填寫表單
├── output/                     # 產出的 PDF / Excel（帶時間戳）
├── web/                        # 網頁樣板與樣式
│
├── db_init.py                  # 初始化資料庫
├── import_data.py              # 命令列匯入
├── create_accounts.py          # 批次建帳號
├── rules.py                    # 報名規則引擎
├── scheduling.py               # 分組 / 賽程演算法
│
├── web_app.py                  # Flask 網頁伺服器
├── gui_app.py                  # tkinter 桌面 GUI
│
├── make_templates.py           # 產 Excel 空範本
├── make_demo_data.py           # 產示範資料
├── make_registration_form.py   # 產填寫式 Excel 報名表
│
├── make_bib_cloth.py           # 號碼布 PDF
├── make_bib_book.py            # 號碼簿 PDF
├── make_grouping.py            # 田徑分組 + 分道
├── make_bracket.py             # 球類賽制表
├── make_checkin.py             # 檢錄組表單
├── make_analysis.py            # 成績分析
│
└── USER_MANUAL.md              # 本手冊
```

---

## 十一、資料備份建議

比賽前後備份 `data/sportmeet.db`：
```bash
cp data/sportmeet.db data/sportmeet_backup_20261115.db
```

---

**版本**：2026.08 · 校內運動會系統 · 若有問題請聯絡體育組
