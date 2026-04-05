---
name: threads-patrol
description: 海巡留言功能：自動在 Threads 貼文下留言（API + 瀏覽器混合模式：瀏覽器讀取、API 發佈）。支援指定貼文 URL 或自動從用戶個人頁面發現貼文。Claude 可根據貼文內容生成回覆，或使用用戶提供的範本。
argument-hint: <貼文URL或@用戶名> [留言內容或範本]
---

# Threads 海巡留言（API + 瀏覽器混合模式：瀏覽器讀取、API 發佈）

自動在 Threads 貼文下留言。支援兩種模式：指定貼文 URL 直接留言，或給用戶名自動發現貼文後批次留言。讀取使用 AppleScript（瀏覽器），發佈使用 Threads Graph API。

## 前置需求

- 環境變數 `THREADS_ACCESS_TOKEN`：Threads API 長效存取權杖
- 環境變數 `THREADS_USER_ID`：Threads 用戶 ID（數字）
- Chrome 已開啟且有 threads.com 分頁（已登入，用於讀取貼文內容）
- Chrome 已啟用「允許 Apple 事件的 JavaScript」（檢視 > 開發人員 > 允許 Apple 事件的 JavaScript）

## 使用方式

用戶會提供目標和留言方式：$ARGUMENTS

支援的輸入格式：
- 貼文 URL：直接對該貼文留言
- 多個 URL（空格或換行分隔）：批次留言
- `@用戶名`：海巡該用戶的最近貼文
- 可額外指定留言內容範本，否則 Claude 根據貼文內容生成

## 執行步驟

### 模式 A：指定貼文 URL

1. 從 `$ARGUMENTS` 解析出貼文 URL
2. 讀取貼文內容（AppleScript，唯讀安全）：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_patrol.sh read "貼文URL"
```
3. 根據貼文內容生成留言（或使用用戶範本），要求：
   - 自然口語化，像真人留言
   - 與貼文內容相關
   - 不要太長（通常 1-3 句）
   - 不要使用 AI 感重的語氣
4. **顯示留言內容給用戶確認**
5. 確認後透過 API 發佈留言：

   a. 查詢貼文的 media ID：
   ```bash
   python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-poster/threads_poster.py get_id "貼文文字前30字"
   ```
   從結果中找到對應貼文的 media ID。

   b. 執行安全檢查：
   ```bash
   python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py check --action reply --skill threads-patrol
   ```
   如果回傳 `allowed: false`，**立即停止**，告知用戶原因。

   c. 透過 API 發佈留言（設定 timeout 為 60000）：
   ```bash
   python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-poster/threads_poster.py reply <media_id> "留言內容"
   ```

   d. 記錄操作結果：
   ```bash
   python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py record --action reply --skill threads-patrol --success true
   ```
   如果發佈失敗，將 `--success true` 改為 `--success false`。

6. 檢查結果，回報成功或失敗

### 模式 B：海巡用戶

1. 從 `$ARGUMENTS` 解析出用戶名（去掉 @ 前綴）
2. 發現該用戶的最近貼文（AppleScript，唯讀安全）：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_patrol.sh discover "@用戶名"
```
3. 列出發現的貼文 URL，讓用戶選擇要留言的
4. 對每則選定的貼文，執行模式 A 的步驟 2-6
5. 多則留言之間使用隨機延遲 **45-120 秒**：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py delay --context between_replies
```

## 安全規則

1. **每日回覆上限**：每日最多 25 則回覆（由安全模組追蹤）
2. **間隔限制**：留言之間隨機延遲 45-120 秒（使用 `threads_safety.py delay --context between_replies`）
3. **全域預檢**：每次操作前執行安全檢查，確認尚未達到每日上限
4. **操作記錄**：每次發佈後記錄操作結果，供安全模組追蹤
5. **不留言自己**：跳過 @jacksonwang88866 的貼文
6. **用戶確認**：每則留言前都要讓用戶確認內容

## 注意事項

- 每則留言前都要讓用戶確認內容
- 批次留言時，多則之間要使用安全模組的延遲功能（45-120 秒隨機）
- 如果回報 TAB_NOT_FOUND，請用戶確認 Chrome 有開啟 threads.com
- 如果回報 REPLY_NOT_FOUND，可能需要先滾動頁面載入回覆區域
- discover 模式需要 Chrome 當前分頁導航到目標用戶的個人頁面
