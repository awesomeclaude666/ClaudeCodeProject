---
name: threads-feed-patrol
description: 自動瀏覽 Threads 推薦動態，閱讀貼文後生成留言並透過 Threads Graph API 發佈（瀏覽器讀取、API 發佈）。像真人一樣滑 feed 然後留言互動。
argument-hint: [留言風格指示，例如：搞笑風、認真回覆、簡短回應]
---

# Threads 推薦動態海巡（API + 瀏覽器混合模式：瀏覽器讀取、API 發佈）

自動瀏覽 Threads 首頁「為你推薦」動態，讀取貼文內容，由 Claude 生成留言，確認後透過 Threads Graph API 發佈。

## 前置需求

- 環境變數 `THREADS_ACCESS_TOKEN`：Threads API 長效存取權杖
- 環境變數 `THREADS_USER_ID`：Threads 用戶 ID（數字）
- Chrome 已開啟且有 threads.com 分頁（已登入，用於瀏覽動態）
- Chrome 已啟用「允許 Apple 事件的 JavaScript」（檢視 > 開發人員 > 允許 Apple 事件的 JavaScript）

## 使用方式

用戶可提供留言風格指示：$ARGUMENTS

如果沒有提供風格指示，預設使用自然口語風格。

## 執行步驟

### Step 1：瀏覽推薦動態

執行 feed 瀏覽腳本（AppleScript，唯讀安全，設定 timeout 為 60000）：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_feed_patrol.sh browse 3
```

### Step 2：展示貼文清單

解析結果 JSON，整理貼文清單並顯示給用戶：
- 編號
- 用戶名
- 貼文內容摘要（前 50 字）

詢問用戶要對哪幾則貼文留言（可多選，例如「1, 3, 5」或「全部」）。

### Step 3：生成留言

對用戶選定的每則貼文，根據貼文內容生成適合的留言，要求：
- 自然口語化，像真人滑手機隨意留言
- 與貼文內容高度相關，要真的有在看文章
- 通常 1-2 句就好，偶爾可以長一點
- 不要使用 AI 感重的語氣（禁止「確實」「不得不說」「真的很棒」這類公式化開頭）
- 適當使用表情符號但不要過多
- 根據貼文語氣調整風格（搞笑的回搞笑、認真的回認真、感性的回感性）
- 如果用戶有提供風格指示，優先遵循

### Step 4：確認並透過 API 留言

**一次顯示所有生成的留言**，讓用戶一起確認：
- 列出每則貼文的用戶名 + 貼文摘要 + 生成的留言
- 用戶可以修改特定留言或全部通過

確認後，對每則貼文依序執行留言：

#### 4a. 查詢貼文的 media ID

```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-poster/threads_poster.py get_id "貼文文字前30字"
```
從結果中找到對應貼文的 media ID。

#### 4b. 執行安全檢查

```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py check --action reply --skill threads-feed-patrol
```
如果回傳 `allowed: false`，**立即停止**，告知用戶原因。

#### 4c. 透過 API 發佈留言（設定 timeout 為 60000）

```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-poster/threads_poster.py reply <media_id> "留言內容"
```

#### 4d. 記錄操作結果

```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py record --action reply --skill threads-feed-patrol --success true
```
如果發佈失敗，將 `--success true` 改為 `--success false`。

#### 4e. 安全間隔

**重要：多則留言之間使用隨機延遲 45-120 秒**：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py delay --context between_replies
```

### Step 5：回報結果

回報每則留言的結果（成功/失敗），統計成功率。

## 安全規則

1. **每日回覆上限**：每日最多 25 則回覆（由安全模組追蹤）
2. **間隔限制**：留言之間隨機延遲 45-120 秒（使用 `threads_safety.py delay --context between_replies`）
3. **全域預檢**：每則留言前執行安全檢查，確認尚未達到每日上限
4. **操作記錄**：每次發佈後記錄操作結果，供安全模組追蹤
5. **不留言自己**：不要對自己的貼文（@jacksonwang88866）留言
6. **用戶確認**：每批留言前一定要讓用戶確認所有內容

## 注意事項

- 每批留言前一定要讓用戶確認所有內容
- 如果回報 TAB_NOT_FOUND，請用戶確認 Chrome 有開啟 threads.com
- 如果 feed 為空，建議用戶先手動滾動 Threads 首頁載入一些內容
- 多則留言之間必須使用安全模組的延遲功能，避免帳號被限制
- 不要對自己的貼文（@jacksonwang88866）留言
