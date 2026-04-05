---
name: threads-auto-reply
description: 監測 Threads 貼文的新留言，自動生成回覆並透過 Threads Graph API 發佈。支援手動審核和全自動模式。
argument-hint: <貼文URL> [auto|manual] [最大回覆數]
---

# Threads 自動回覆（API 版）

監測指定 Threads 貼文的新留言，由 Claude 生成回覆，透過 Threads Graph API 發佈。支援手動確認或全自動模式。

## 前置需求

- 環境變數 `THREADS_ACCESS_TOKEN`：Threads API 長效存取權杖
- 環境變數 `THREADS_USER_ID`：Threads 用戶 ID（數字）
- Chrome 已開啟且有 threads.com 分頁（已登入，用於讀取留言）
- Chrome 已啟用「允許 Apple 事件的 JavaScript」

## 使用方式

用戶提供：$ARGUMENTS

- 貼文 URL（必填）
- 模式：`auto`（全自動）或 `manual`（手動確認，預設）
- 最大回覆數（預設 10）

範例：
- `/threads-auto-reply https://www.threads.com/@jacksonwang88866/post/ABC123`
- `/threads-auto-reply https://www.threads.com/@jacksonwang88866/post/ABC123 auto 15`

## 執行步驟

### Step 1：全域預檢

執行全域安全預檢：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py check --action reply --skill threads-auto-reply
```

如果回傳不允許（`allowed: false`），停止執行並告知用戶原因（例如已達每日上限）。

### Step 2：讀取原文內容

執行（設定 timeout 為 60000）：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_auto_reply_check.sh read "POST_URL"
```

儲存原文內容，作為後續生成回覆的上下文。告訴用戶原文內容和選擇的模式。

### Step 3：首次檢查現有留言

```bash
bash ${CLAUDE_SKILL_DIR}/threads_auto_reply_check.sh check "POST_URL"
```

報告目前留言數。如果有現有留言：
- **manual 模式**：詢問用戶要回覆哪些現有留言，或只監測新留言
- **auto 模式**：跳過現有留言，只等待新留言

### Step 4：監測迴圈

Claude 自己控制迴圈，每次循環：

#### 4a. 檢查新留言
```bash
bash ${CLAUDE_SKILL_DIR}/threads_auto_reply_check.sh check "POST_URL"
```
設定 timeout 為 60000。

#### 4b. 為每則新留言生成回覆

根據**原文內容 + 留言內容**生成回覆，要求：
- 台灣口語風格，自然不做作
- 1-2 句，直接回應留言的具體內容
- 作為貼文作者回覆讀者，語氣親切但不諂媚
- **禁止**：「確實」「不得不說」「真的很棒」「太有道理了」等 AI 公式化語氣
- 適當加入個人觀點或補充資訊
- 可適度使用 emoji 但不過多

#### 4c. 模式分流

**manual 模式**：
- 顯示每則留言 + 生成的回覆
- 等用戶確認、修改或跳過
- 用戶說「全部通過」則一起發佈

**auto 模式**：
- 直接進入發佈流程
- 不需用戶確認

#### 4d. 透過 Threads API 發佈回覆

**重要：所有寫入操作（發佈回覆）一律使用 Threads Graph API，不使用瀏覽器自動化。**

發佈步驟：

1. 查詢貼文的 media ID：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-poster/threads_poster.py list 10
```
從結果中找到對應貼文的 media ID。

2. 取得完整對話串，找到要回覆的留言 ID：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-poster/threads_poster.py conversation <media_id>
```
從對話串中找到目標留言的 reply_id。

3. 執行安全檢查：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py check --action reply --skill threads-auto-reply
```
如果回傳 `allowed: false`，**立即停止**，告知用戶原因。

4. 透過 API 發佈回覆（設定 timeout 為 60000）：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-poster/threads_poster.py reply <reply_id> "回覆內容"
```

5. 記錄操作結果：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py record --action reply --skill threads-auto-reply --success true
```
如果發佈失敗，將 `--success true` 改為 `--success false`。

如果發佈失敗，重試最多 2 次。

#### 4e. 標記已回覆

每則成功發佈後：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_auto_reply_check.sh mark_replied "POST_URL" "COMMENT_ID"
```

#### 4f. 安全間隔

- 每則留言之間使用隨機延遲 **45-120 秒**：
```bash
python3 /Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py delay --context between_replies
```
- 檢查 `session_reply_count` 是否已達上限（預設 10）
- 檢查每日回覆數是否已達 **25 則**上限
- 如果達到任一上限，停止監測並告知用戶

#### 4g. 等待下次檢查

如果沒有新留言，或所有新留言已處理完：
```bash
sleep 60
```
然後回到 4a 繼續迴圈。

**manual 模式**：每輪結束後詢問用戶是否繼續監測
**auto 模式**：自動繼續，直到達上限或用戶中斷

### Step 5：結束報告

當迴圈結束時（用戶停止 / 達到上限 / 錯誤），報告：
- 本次 session 回覆總數
- 成功 / 失敗數
- 監測時長

## 安全規則

1. **不回覆自己**：跳過 @jacksonwang88866 的留言
2. **Session 回覆上限**：預設每 session 最多 10 則（可由用戶調整）
3. **每日回覆上限**：每日最多 25 則回覆（由安全模組追蹤）
4. **間隔限制**：留言之間隨機延遲 45-120 秒（使用 `threads_safety.py delay --context between_replies`）
5. **防重複**：狀態檔追蹤已回覆的留言 ID
6. **手動模式優先**：manual 模式下永遠先顯示再發佈
7. **失敗停止**：連續失敗 3 次則停止監測並告知用戶
8. **全域預檢**：每次 session 開始前執行安全預檢，確認尚未達到每日上限
9. **操作記錄**：每次發佈後記錄操作結果，供安全模組追蹤

## 注意事項

- 如果回報 TAB_NOT_FOUND，請用戶確認 Chrome 有開啟 threads.com
- 此 skill 通常搭配 `/threads-auto-post` 使用：先發文，再監測回覆
- 可以用 `reset` 指令重設 session 計數：
  ```bash
  bash ${CLAUDE_SKILL_DIR}/threads_auto_reply_check.sh reset "POST_URL"
  ```
- 狀態檔位於 `/tmp/threads_auto_reply_STATE_<shortcode>.json`
- 重開機後狀態檔會清除，但不影響功能
