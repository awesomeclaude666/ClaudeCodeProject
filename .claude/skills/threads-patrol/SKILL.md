---
name: threads-patrol
description: 海巡留言功能：自動在 Threads 貼文下留言（不需 API）。支援指定貼文 URL 或自動從用戶個人頁面發現貼文。Claude 可根據貼文內容生成回覆，或使用用戶提供的範本。
argument-hint: <貼文URL或@用戶名> [留言內容或範本]
---

# Threads 海巡留言（瀏覽器版）

自動在 Threads 貼文下留言。支援兩種模式：指定貼文 URL 直接留言，或給用戶名自動發現貼文後批次留言。

## 前置需求

- Chrome 已開啟且有 threads.com 分頁（已登入）
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
2. 讀取貼文內容：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_patrol.sh read "貼文URL"
```
3. 根據貼文內容生成留言（或使用用戶範本），要求：
   - 自然口語化，像真人留言
   - 與貼文內容相關
   - 不要太長（通常 1-3 句）
   - 不要使用 AI 感重的語氣
4. **顯示留言內容給用戶確認**
5. 確認後執行留言（設定 timeout 為 60000）：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_patrol.sh reply "貼文URL" "留言內容"
```
6. 檢查結果，回報成功或失敗

### 模式 B：海巡用戶

1. 從 `$ARGUMENTS` 解析出用戶名（去掉 @ 前綴）
2. 發現該用戶的最近貼文：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_patrol.sh discover "@用戶名"
```
3. 列出發現的貼文 URL，讓用戶選擇要留言的
4. 對每則選定的貼文，執行模式 A 的步驟 2-6
5. 多則留言之間建議間隔 10-30 秒

## 注意事項

- 每則留言前都要讓用戶確認內容
- 批次留言時，多則之間要有適當間隔（10-30 秒）避免被偵測
- 如果回報 TAB_NOT_FOUND，請用戶確認 Chrome 有開啟 threads.com
- 如果回報 REPLY_NOT_FOUND，可能需要先滾動頁面載入回覆區域
- discover 模式需要 Chrome 當前分頁導航到目標用戶的個人頁面
