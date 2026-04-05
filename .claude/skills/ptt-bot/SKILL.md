---
name: ptt-bot
description: PTT 自動化工具：登入 PTT 後可發文、推文、讀文、列出看板文章、監測看板新文。帳號密碼每次由用戶提供。
argument-hint: <操作指令，例如：發文到 Gossiping、推文、監測 NBA 板>
---

# PTT 自動化工具

登入 PTT（批踢踢實業坊）後執行各種操作：發文、推文、讀文、列出文章、監測看板。

## 前置需求

- Python 3 已安裝 `PyPtt` 套件（`pip3 install PyPtt`）
- Python 3 已安裝 `PySocks` 套件（`pip3 install PySocks`，使用代理時需要）
- 用戶提供 PTT 帳號和密碼（每次執行時提供，不儲存）
- （可選）SOCKS5 代理帳號，用於更換登入 IP

## 使用方式

用戶會提供操作指令：$ARGUMENTS

支援的操作：
- **發文**：指定看板和主題，Claude 生成內容
- **推文**：對指定文章推文/噓文/箭頭
- **讀文**：讀取指定文章內容和推文
- **列表**：列出看板最新文章
- **監測**：持續監測看板新文章

## 執行步驟

### 共通：取得帳號密碼與代理設定

每次執行前，先詢問用戶的 PTT 帳號和密碼。收到後以 inline 環境變數方式傳入指令。

如果用戶要求使用代理（換 IP），加上 `PTT_PROXY` 環境變數：
```bash
PTT_PROXY="socks5://user:pass@host:port" PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py test
```

支援的代理格式：
- `socks5://host:port`（無認證）
- `socks5://user:pass@host:port`（帳密認證）

推薦使用台灣住宅代理（如 IPRoyal），每次連線自動取得不同台灣 IP。

### 模式 A：發文

1. 用戶提供看板名稱和主題方向
2. Claude 生成文章標題和內容，要求：
   - 繁體中文
   - 符合 PTT 的文化和風格
   - 使用適當的標題格式（如 [問卦] [心得] [閒聊]）
   - 內容排版清楚
3. **顯示給用戶確認**，等待同意
4. 確認後執行：

   a. 安全預檢：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/ptt_safety.py check --action post
   ```
   如果回傳 `allowed: false`，**立即停止**。

   b. 發文（設定 timeout 為 120000）：
   ```bash
   PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py post --board "看板名" --title "標題" --content "內容" --category 1
   ```

   c. 記錄結果：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/ptt_safety.py record --action post --success true
   ```

5. 回報結果

### 模式 B：推文

1. 用戶提供目標（看板+文章編號/AID，或請 Claude 先列出文章選擇）
2. 如果需要，先讀取文章內容：
   ```bash
   PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py read --board "看板" --aid "AID"
   ```
3. 根據文章內容生成推文，要求：
   - 自然口語化
   - 符合 PTT 推文風格（簡短、有梗）
   - 推文上限 45 個中文字
4. **顯示給用戶確認**推文內容和類型（推/噓/→）
5. 確認後執行：

   a. 安全預檢：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/ptt_safety.py check --action push
   ```

   b. 推文（設定 timeout 為 120000）：
   ```bash
   PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py push --board "看板" --aid "AID" --type push --content "推文內容"
   ```

   c. 記錄結果：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/ptt_safety.py record --action push --success true
   ```

6. 多則推文之間使用安全延遲：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/ptt_safety.py delay --context between_pushes
   ```

### 模式 C：讀文

```bash
PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py read --board "看板" --aid "AID"
```

或用 index：
```bash
PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py read --board "看板" --index 12345
```

### 模式 D：列出文章

```bash
PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py list --board "看板" --count 10
```

搜尋特定關鍵字：
```bash
PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py list --board "看板" --keyword "關鍵字"
```

### 模式 E：監測看板

```bash
PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py monitor --board "看板" --interval 60 --keyword "關鍵字"
```

監測到新文時會透過 macOS 通知提醒。

### 輔助：測試連線

```bash
PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py test
```

### 輔助：搜尋看板

```bash
PTT_USERNAME="帳號" PTT_PASSWORD="密碼" python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py boards --keyword "NBA"
```

## 安全規則

1. **每日發文上限**：5 篇（由安全模組追蹤）
2. **每日推文上限**：30 則
3. **推文間隔**：隨機 30-60 秒
4. **發文間隔**：隨機 120-300 秒
5. **全域預檢**：每次寫入操作前執行安全檢查
6. **操作記錄**：每次操作後記錄結果
7. **用戶確認**：每次發文和推文前都要讓用戶確認內容
8. **帳密不保存**：帳號密碼僅在指令中以 inline 環境變數傳入，不寫入檔案

## 代理（Proxy）設定

支援透過 SOCKS5 代理連線 PTT，用於更換登入 IP。

設定方式：加上 `PTT_PROXY` 環境變數：
```bash
PTT_PROXY="socks5://user:pass@geo.iproyal.com:32325" \
PTT_USERNAME="帳號" PTT_PASSWORD="密碼" \
python3 ${CLAUDE_SKILL_DIR}/ptt_bot.py test
```

推薦使用台灣住宅代理服務（如 IPRoyal），每次連線自動分配不同的台灣家用 IP。

## 注意事項

- PTT 帳號密碼每次都要問用戶，不要嘗試從環境變數或檔案中讀取
- 如果用戶有提供代理資訊，加上 `PTT_PROXY` 環境變數
- 發文需要看板的發文權限，部分看板有限制
- 推文內容上限約 45 個中文字
- PTT 系統本身也有推文間隔限制（約 5 秒），安全模組的間隔更為保守
- 如果遇到 `LoginError`，可能是 PTT 伺服器忙碌，建議稍後再試
- 如果遇到 `OnlySecureConnection`，可能是 PTT 伺服器要求安全連線
- monitor 模式會持續運行，用戶可以中斷或設定較長的間隔
- 文章分類編號 (--category) 因看板而異，常見: 1=一般類別
