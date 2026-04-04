# Google Cloud 設定指引

## 步驟 1：建立 Google Cloud 專案

1. 前往 https://console.cloud.google.com/
2. 點擊頂部的「Select a project」→「NEW PROJECT」
3. 專案名稱輸入 `article-metrics`（任意名稱皆可）
4. 點擊「Create」，等待建立完成

## 步驟 2：啟用 API

1. 前往「APIs & Services」→「Library」
2. 搜尋 **Google Sheets API**，點進去後點「Enable」
3. 搜尋 **Google Drive API**，點進去後點「Enable」

## 步驟 3：建立 Service Account

1. 前往「APIs & Services」→「Credentials」
2. 點擊「Create Credentials」→「Service account」
3. 名稱輸入 `article-metrics-bot`
4. 跳過其他可選步驟，直接點「Done」
5. 點擊剛建立的 service account email
6. 切到「Keys」分頁，點「ADD KEY」→「Create new key」
7. 選 **JSON**，點「Create」
8. 會自動下載一個 `.json` 檔案

## 步驟 4：放置憑證檔案

```bash
mkdir -p ~/.config/gspread
mv ~/Downloads/article-metrics-*.json ~/.config/gspread/service_account.json
```

## 步驟 5：分享 Google Sheet

1. 打開你的 Google Sheet
2. 點右上角「Share」
3. 將 service account 的 email 貼上（在 JSON 檔案裡的 `client_email` 欄位，格式類似 `article-metrics-bot@project-name.iam.gserviceaccount.com`）
4. 權限選「Editor」
5. 點「Send」

## 步驟 6：取得 Sheet ID

Google Sheet 的 URL 長這樣：
```
https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
```

複製 `SHEET_ID_HERE` 的部分，填入 `config.json` 的 `sheet_id`。

## 步驟 7：安裝 Python 依賴

```bash
pip3 install -r .claude/skills/update-articles/scripts/requirements.txt
playwright install chromium
```

## 步驟 8：建立 config.json

```bash
cp .claude/skills/update-articles/scripts/config.example.json ./config.json
```

編輯 `config.json`，填入你的 `sheet_id`。如果憑證路徑不同也一併修改。

## Google Sheet 欄位格式

請確保你的 Sheet 第一行有以下標題（或根據 config.json 的 columns 設定調整）：

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| URL | 平台 | 標題 | 按讚數 | 留言數 | 瀏覽數 | 更新時間 |

從第二行開始在 A 欄貼上文章連結即可。
