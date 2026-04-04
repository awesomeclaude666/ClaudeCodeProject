---
name: threads-auto-post
description: 透過 Chrome 瀏覽器自動在 Threads 發布貼文（不需 API）。Claude 根據主題生成內容，確認後自動發佈。
argument-hint: <主題或方向描述>
---

# Threads 自動發文（瀏覽器版）

透過 Chrome 瀏覽器自動化在 Threads 發布貼文，不需要 Threads API token。

## 前置需求

- Chrome 已開啟且有 threads.com 分頁（已登入）
- Chrome 已啟用「允許 Apple 事件的 JavaScript」（檢視 > 開發人員 > 允許 Apple 事件的 JavaScript）

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
4. 用戶確認後，執行發文腳本（設定 timeout 為 60000）：

```bash
bash ${CLAUDE_SKILL_DIR}/threads_auto_post.sh "貼文內容"
```

5. 檢查腳本輸出的 JSON 結果：
   - `success: true` → 告知用戶發文成功
   - `success: false` → 顯示錯誤訊息，建議解決方式
6. 如果使用 execCommand 方式失敗，腳本會自動嘗試剪貼簿貼上方式（需要 Chrome 在前景）

## 注意事項

- 發文前一定要讓用戶確認內容
- 如果腳本回報 TAB_NOT_FOUND，請用戶確認 Chrome 有開啟 threads.com
- 如果回報 COMPOSE_NOT_FOUND，可能是 Threads 介面更新，需要更新 JS 選擇器
- 發文完成後建議等待幾秒再進行下一次操作
