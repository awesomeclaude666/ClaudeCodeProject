---
name: ptt-auto-reply
description: 使用 PyPtt 登入 PTT，自動抓取指定看板的熱門/爆文兩篇，由 Claude 依文章內容生成回覆並直接推文發送。需要環境變數 PTT_ID 與 PTT_PW。
---

# ptt-auto-reply

自動化 PTT 推文流程：登入 → 找熱門文 → 生成回覆 → 推文。

## 使用方式

使用者通常會說「幫我去 XXX 板推兩篇熱門文」之類的話。需要：
- **board**（必填）：看板名稱，例如 `Gossiping`、`Stock`、`C_Chat`
- **count**：要回幾篇，預設 2
- **push_type**：`推` / `噓` / `→`，預設 `推`

## 前置條件

1. 必須安裝 PyPtt：`pip install PyPtt`
2. 環境變數必須存在：`PTT_ID`、`PTT_PW`
   - 若缺少，**不要**詢問使用者密碼，直接報錯請對方設定環境變數
3. 此 skill 直接發送，不二次確認（使用者已授權全自動）

## 步驟

### 1. 檢查環境
```bash
python -c "import PyPtt" && echo OK
echo "ID set: ${PTT_ID:+yes}  PW set: ${PTT_PW:+yes}"
```
若任一缺失，停止並回報。

### 2. 抓取熱門文章
執行 `scripts/fetch_hot.py <board> <count>`，它會：
- 登入 PTT
- 從看板列表往前找「爆!」或推文數 ≥ 50 的文章
- 輸出 JSON：`[{aid, title, author, content}, ...]`
- 登出

### 3. 生成回覆內容
針對每篇文章，**Claude 自己**讀 content 後生成一條 PTT 風格的推文：
- 長度 ≤ 35 全形字（PTT 推文上限）
- 切題、不引戰、不違反板規
- 不使用會被擋的字元（避免控制碼）
- 不要無意義的「推」「+1」這類灌水

把每篇對應的回覆寫入暫存 JSON：`[{aid, push_type, content}, ...]`

### 4. 發送推文
執行 `scripts/push.py <board> <payload.json>` 完成推文，輸出每篇結果。

### 5. 回報
給使用者一份簡潔總結：板名、文章標題、推文內容、成功 / 失敗。

## 安全與限制

- 只在使用者明確指定的看板推文
- 同一執行不對同一篇文章重複推
- 若 PTT 顯示「請稍後再試」「嘗試太頻繁」立即停止
- 不處理需要重複登入 / 踢人的情況——直接回報並結束
- 絕不把 PTT_PW 寫入檔案或 log
