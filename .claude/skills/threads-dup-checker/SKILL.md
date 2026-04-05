---
name: threads-dup-checker
description: 檢查 Threads 個人回覆頁面在過去 24 小時內是否有重複留言。自動瀏覽回覆頁面，提取近期回覆並比對是否有相同內容。
argument-hint: [滾動次數，預設5]
---

# Threads 重複留言檢查

自動瀏覽 Threads 回覆頁面（/@jacksonwang88866/replies），提取過去 24 小時內的所有回覆，檢查是否有完全相同的留言文字。

## 前置需求

- Chrome 已開啟且有 threads.com 分頁（已登入）
- Chrome 已啟用「允許 Apple 事件的 JavaScript」（檢視 > 開發人員 > 允許 Apple 事件的 JavaScript）

## 使用方式

可選擇性提供滾動次數（預設 5）：$ARGUMENTS

## 執行步驟

### Step 1：執行重複檢查

執行檢查腳本（設定 timeout 為 60000）：
```bash
bash ${CLAUDE_SKILL_DIR}/threads_dup_checker.sh 5
```

如果用戶有提供滾動次數，使用該數字取代預設的 5。

### Step 2：解析並報告結果

解析結果 JSON，向用戶報告：

**如果沒有重複留言：**
- 告知用戶過去 24 小時內共有 N 則回覆，沒有重複

**如果有重複留言：**
- 列出每組重複留言：
  - 重複的文字內容
  - 出現次數
  - 分別出現在哪些貼文（post URL）
  - 各自的時間標記
- 建議用戶手動刪除多餘的重複留言

## 注意事項

- 如果回報 TAB_NOT_FOUND，請用戶確認 Chrome 有開啟 threads.com
- 滾動次數越多，能載入越多歷史回覆，但速度越慢
- 時間判斷基於頁面顯示的相對時間（如「1小時」「3h」），可能有少許誤差
- 此 skill 只做檢查，不會自動刪除任何留言
