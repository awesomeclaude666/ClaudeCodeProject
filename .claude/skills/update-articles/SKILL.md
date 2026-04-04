---
name: update-articles
description: 從 Google Sheet 讀取文章連結（Dcard、Threads 等平台），抓取最新的按讚數、留言數、瀏覽數等互動數據，並更新回 Google Sheet。
disable-model-invocation: true
allowed-tools: Bash(python3 *) Bash(pip3 install *) Bash(playwright install *) Read
argument-hint: "[--dry-run] [--row N]"
---

## 文章數據更新工具

自動從 Google Sheet 讀取文章連結，抓取各平台互動數據並回寫。

### 前置檢查

1. **檢查 Python 依賴**：執行 `pip3 list` 確認 gspread、google-auth、requests、playwright 是否已安裝。若缺少，執行：
   ```
   pip3 install -r ${CLAUDE_SKILL_DIR}/scripts/requirements.txt
   playwright install chromium
   ```

2. **檢查設定檔**：確認專案根目錄有 `config.json`。若無，提示用戶：
   ```
   cp ${CLAUDE_SKILL_DIR}/scripts/config.example.json ./config.json
   ```
   然後請用戶填入 Google Sheet ID。

3. **檢查 Google 憑證**：確認 `~/.config/gspread/service_account.json` 存在。若不存在，請用戶參考 `${CLAUDE_SKILL_DIR}/setup.md` 完成 Google Cloud 設定。

### 執行

完成前置檢查後，執行主程式：

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/fetch_metrics.py --config ./config.json $ARGUMENTS
```

### 支援的參數

- `--dry-run`：只抓取數據但不寫入 Sheet（測試用）
- `--row N`：只處理第 N 行（除錯用）
- `--platform NAME`：只處理指定平台（如 `Dcard` 或 `Threads`）

### 結果報告

執行完成後，向用戶報告：
- 總共處理了幾筆 URL
- 成功和失敗的數量
- 失敗的具體原因
- 若有更新，告知 Google Sheet 已更新

### 支援平台

- **Dcard**（dcard.tw）：透過公開 API 抓取按讚數、留言數
- **Threads**（threads.net）：透過 Playwright 無頭瀏覽器抓取按讚數、回覆數

### 新增平台

如需支援新平台，在 `${CLAUDE_SKILL_DIR}/scripts/platforms/` 新增一個 `.py` 檔案，實作 `BasePlatform` 子類即可。
