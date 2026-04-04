---
name: threads-poster
description: 透過 Threads API 發布貼文、回覆留言、查看最近貼文、搜尋公開貼文。傳入操作指令即可執行。
argument-hint: <操作指令>
---

# Threads 貼文管理

透過 Threads Graph API 發布貼文、回覆留言、查看帳號貼文、搜尋公開貼文。

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
注意：此操作需要約 35 秒（Meta API 要求建立容器後等待 30 秒才能發布），請設定 timeout 為 60000。

### 回覆貼文
```bash
python3 ${CLAUDE_SKILL_DIR}/threads_poster.py reply <貼文ID> "回覆內容"
```
貼文 ID 必須是數字格式的 media ID（非 URL 中的短碼）。如果用戶提供 URL，請先用 `list` 或 `search` 找到對應的數字 ID。
注意：此操作同樣需要約 35 秒。

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

## 執行步驟

1. 先確認環境變數 `THREADS_ACCESS_TOKEN` 和 `THREADS_USER_ID` 已設定（用 `echo $THREADS_ACCESS_TOKEN | head -c 10` 檢查）
2. 解析用戶的意圖，選擇對應指令
3. 對於 `post` 和 `reply` 指令，先告知用戶此操作需要約 35 秒
4. 執行指令，設定 timeout 為 60000
5. 解析 JSON 輸出，以易讀格式呈現給用戶
6. 如果出錯，顯示錯誤訊息並建議解決方式

## 注意事項

- 發文和回覆會等待約 30 秒（Meta API 規定的容器處理時間），請提前告知用戶
- 所有輸出為 JSON 格式
- 貼文內容上限 500 字元
- 每 24 小時最多發布 250 篇貼文（回覆不計入此限制）
- 如遇到 Token 過期錯誤（error code 190），請引導用戶重新取得 access token
