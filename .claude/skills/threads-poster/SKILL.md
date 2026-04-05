---
name: threads-poster
description: 透過 Threads API 發布貼文、回覆留言、查看最近貼文、搜尋公開貼文、反查貼文 ID、取得對話串。傳入操作指令即可執行。
argument-hint: <操作指令>
---

# Threads 貼文管理

透過 Threads Graph API 發布貼文、回覆留言、查看帳號貼文、搜尋公開貼文、從貼文文字反查 media ID、取得完整對話串。

## 前置需求

- 環境變數 `THREADS_ACCESS_TOKEN`：Threads API 長效存取權杖
- 環境變數 `THREADS_USER_ID`：Threads 用戶 ID（數字）
- Python 3 已安裝 `requests` 套件

如果用戶未設定環境變數，請引導他們：
1. 前往 Meta Developer Portal 建立應用程式
2. 新增 Threads API 產品，設定 OAuth redirect URI
3. 使用 OAuth 流程取得 access token（需要 threads_basic、threads_content_publish、threads_manage_replies、threads_read_replies、threads_keyword_search 權限）
4. 將 short-lived token 換成 long-lived token（有效期 60 天）
5. 設定環境變數：`export THREADS_ACCESS_TOKEN="..."` 和 `export THREADS_USER_ID="..."`

## 使用方式

用戶會以自然語言描述操作：$ARGUMENTS

根據用戶意圖，選擇對應的指令執行。

## 可用操作

### 發布新貼文
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py post "貼文內容"
```
注意：此操作需要約 35-45 秒（Meta API 容器處理時間 + 隨機抖動），請設定 timeout 為 60000。

### 回覆貼文
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py reply <貼文ID> "回覆內容"
```
貼文 ID 必須是數字格式的 media ID（非 URL 中的短碼）。如果用戶提供 URL，請先用 `list`、`search` 或 `get_id` 找到對應的數字 ID。
注意：此操作同樣需要約 35-45 秒（Meta API 容器處理時間 + 隨機抖動）。

### 查看最近貼文
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py list [數量]
```
預設顯示最近 10 篇貼文。

### 搜尋公開貼文
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py search "關鍵字"
```
需要 threads_keyword_search 權限。

### 查看帳號資訊
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py profile
```

### 查看貼文回覆
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py replies <貼文ID>
```

### 從貼文文字反查 media ID
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py get_id "搜尋文字"
```
根據貼文文字內容（通常取前 30 字）反查對應的 media ID。適用於只知道貼文內容但不知道 ID 的情境。

### 取得完整對話串
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py conversation <thread_id>
```
取得指定貼文的完整對話串，包含所有回覆。適用於需要找到特定留言的 reply_id 以進行回覆的情境。

## 執行步驟

1. 先確認環境變數 `THREADS_ACCESS_TOKEN` 和 `THREADS_USER_ID` 已設定（用 `echo $THREADS_ACCESS_TOKEN | head -c 10` 檢查）
2. 解析用戶的意圖，選擇對應指令
3. 對於 `post` 和 `reply` 指令，先告知用戶此操作需要約 35-45 秒
4. 執行指令，設定 timeout 為 60000
5. 解析 JSON 輸出，以易讀格式呈現給用戶
6. 如果出錯，顯示錯誤訊息並建議解決方式

## 安全模組整合

此工具被其他 skill（threads-auto-reply、threads-patrol、threads-feed-patrol、threads-auto-post）呼叫時，應搭配安全模組使用：

- **發佈前**：呼叫方 skill 應先執行 `threads_safety.py check` 確認操作是否被允許
- **發佈後**：呼叫方 skill 應執行 `threads_safety.py record` 記錄操作結果
- **延遲控制**：多次操作之間應使用 `threads_safety.py delay` 取得隨機延遲時間

安全模組路徑：`/Users/bobowang/Desktop/ClaudeCodeProject/.claude/skills/threads-safety/threads_safety.py`

## 安全規則

1. **每日發文上限**：每 24 小時最多發布 250 篇貼文（Meta API 限制，回覆不計入此限制）
2. **每日回覆上限**：每日最多 25 則回覆（由安全模組追蹤，跨 skill 共享計數）
3. **操作間隔**：發文和回覆操作之間建議保持適當間隔，避免被偵測為自動化行為
4. **內容長度**：貼文內容上限 500 字元

## 注意事項

- 發文和回覆會等待約 35-45 秒（Meta API 規定的容器處理時間 + 隨機抖動），請提前告知用戶
- 所有輸出為 JSON 格式
- 貼文內容上限 500 字元
- 如遇到 Token 過期錯誤（error code 190），請引導用戶重新取得 access token
