---
name: threads-monitor
description: 監測 Threads 貼文的新留言，有新留言時透過 macOS 通知顯示留言內容。傳入貼文 URL 即可開始監測。
argument-hint: <Threads貼文URL> [間隔秒數]
---

# Threads 留言監測

監測指定 Threads 貼文的新留言，偵測到新留言時發送 macOS 通知（含留言內容）。

## 前置需求

- Chrome 已開啟且有該 Threads 貼文分頁
- Chrome 已啟用「允許 Apple 事件的 JavaScript」（檢視 > 開發人員 > 允許 Apple 事件的 JavaScript）

## 使用方式

用戶會提供 Threads 貼文 URL：$ARGUMENTS

## 執行步驟

1. 從用戶輸入解析貼文 URL
2. 確認 Chrome 中有開啟該 Threads 貼文（如果沒有，請用戶先開啟）
3. 如果用戶有指定間隔秒數就使用，否則預設 300 秒（5 分鐘）
4. 在背景執行監測腳本：

```bash
nohup bash ${CLAUDE_SKILL_DIR}/threads_monitor.sh <貼文URL> <間隔秒數> > /tmp/threads_monitor_output.log 2>&1 &
```

5. 等待約 15 秒後檢查 `/tmp/threads_monitor_output.log` 確認啟動成功
6. 告知用戶監測已啟動，並提供：
   - 目前留言數
   - 檢查頻率
   - PID
   - 查看 log 指令：`cat /tmp/threads_monitor.log`
   - 停止指令：`kill $(cat /tmp/threads_monitor.pid)`
