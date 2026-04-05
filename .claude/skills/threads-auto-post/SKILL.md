---
name: threads-auto-post
description: 透過 Threads API 發布貼文。Claude 根據主題生成內容，確認後透過 API 發佈。
argument-hint: <主題或方向描述>
---

# Threads 自動發文（API 版）

透過 Threads Graph API 發布貼文。Claude 根據主題生成內容，確認後透過 API 發佈。

## 前置需求

- 環境變數 `THREADS_ACCESS_TOKEN`：Threads API 長效存取權杖
- 環境變數 `THREADS_USER_ID`：Threads 用戶 ID（數字）
- Python 3 已安裝 `requests` 套件

## 使用方式

用戶會提供發文主題或方向：$ARGUMENTS

## 執行步驟

1. 解析用戶提供的主題或方向
2. 根據主題生成貼文內容（繁體中文、台灣風格、500 字以內），要求：
   - 自然口語化，像真人發文
   - 不要使用 AI 感重的語氣
   - 適當使用表情符號但不要過多
   - 符合 Threads 的短文風格
3. **顯示生成的貼文內容給用戶確認**，等用戶同意後才繼續
4. 用戶確認後，執行發文流程：

   a. 執行安全檢查：
   ```bash
   python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py check --action post --skill threads-auto-post
   ```
   如果回傳 `allowed: false`，**立即停止**，告知用戶原因（例如已達每日上限）。

   b. 透過 API 發佈貼文（設定 timeout 為 60000）：
   ```bash
   python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-poster/threads_poster.py post "貼文內容"
   ```

   c. 記錄操作結果：
   ```bash
   python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py record --action post --skill threads-auto-post --success true
   ```
   如果發佈失敗，將 `--success true` 改為 `--success false`。

5. 檢查輸出的 JSON 結果：
   - `success: true` -> 告知用戶發文成功
   - `success: false` -> 顯示錯誤訊息，建議解決方式
6. 如果遇到 Token 過期錯誤（error code 190），請引導用戶重新取得 access token

## 安全規則

1. **每日發文上限**：由安全模組追蹤每日發文數量
2. **全域預檢**：發文前執行安全檢查，確認尚未達到每日上限
3. **操作記錄**：每次發佈後記錄操作結果，供安全模組追蹤
4. **用戶確認**：發文前一定要讓用戶確認內容
5. **內容長度**：貼文內容上限 500 字元
6. **API 限制**：每 24 小時最多發布 250 篇貼文（Meta API 限制）

## 注意事項

- 發文前一定要讓用戶確認內容
- 發文操作需要約 35 秒（Meta API 要求建立容器後等待處理時間），請提前告知用戶
- 如果遇到 Token 過期錯誤（error code 190），請引導用戶重新取得 access token
- 發文完成後建議等待幾秒再進行下一次操作
- 所有輸出為 JSON 格式
