---
name: dcard-monitor
description: 監測 Dcard 文章的新留言，有新留言時透過 macOS 通知顯示留言內容。傳入文章 URL 或 ID 即可開始監測。
argument-hint: <文章URL或ID> [間隔秒數]
---

# Dcard 留言監測

監測指定 Dcard 文章的新留言，偵測到新留言時發送 macOS 通知（含留言內容）。

## 前置需求

- Chrome 已開啟且有任意 Dcard 分頁
- Chrome 已啟用「允許 Apple 事件的 JavaScript」（檢視 > 開發人員 > 允許 Apple 事件的 JavaScript）

## 使用方式

用戶會提供文章 URL 或 ID：$ARGUMENTS

## 執行步驟

1. 從用戶輸入中解析文章 ID（支援完整 URL 或純數字 ID）
2. 如果用戶有指定間隔秒數就使用，否則預設 300 秒（5 分鐘）
3. 在背景執行監測腳本：

```bash
nohup bash ${CLAUDE_SKILL_DIR}/dcard_monitor.sh <文章ID> <間隔秒數> > /tmp/dcard_monitor_output.log 2>&1 &
```

4. 等待幾秒後檢查 `/tmp/dcard_monitor_output.log` 確認啟動成功
5. 告知用戶監測已啟動，並提供以下資訊：
   - 文章標題
   - 目前留言數
   - 檢查頻率
   - PID
   - 查看 log 指令：`cat /tmp/dcard_monitor_<文章ID>.log`
   - 停止指令：`kill $(cat /tmp/dcard_monitor.pid)`
