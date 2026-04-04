---
name: reconciliation
description: 財務對帳工具：匯入銀行明細 CSV、電子發票、合約資料到 Google Sheet，自動比對銀行入帳、發票、合約付款狀態。支援多期付款追蹤。
argument-hint: <操作指令>
---

# 財務對帳系統

自動匯入銀行明細、電子發票、合約資料到 Google Sheet，執行三方對帳比對。

## 前置需求

- Python 3 已安裝依賴（google-api-python-client, google-auth, openpyxl）
- Google Sheets Service Account credentials.json 已設定
- 環境變數 `RECONCILIATION_SPREADSHEET_ID` 已設定（Google Sheet ID）
- 環境變數 `GOOGLE_SHEETS_CREDENTIALS_PATH` 已設定（Service Account JSON 路徑）

## 使用方式

用戶會以自然語言描述操作：$ARGUMENTS

根據用戶意圖，選擇對應的指令執行。

## 可用操作

### 初始化 Google Sheet 結構（首次使用）
```bash
python3 -m reconciliation.reconcile setup
```

### 匯入銀行明細
```bash
python3 -m reconciliation.reconcile import-bank <CSV路徑> [--mapping <mapping.json>]
```
首次匯入會自動偵測欄位，偵測結果存為 JSON 供後續使用。

### 匯入電子發票
```bash
python3 -m reconciliation.reconcile import-invoice <CSV路徑>
```

### 匯入/更新合約
```bash
python3 -m reconciliation.reconcile import-contract <CSV或Excel路徑>
```

### 執行自動對帳
```bash
python3 -m reconciliation.reconcile match [--auto-confirm]
```

### 查看對帳狀態
```bash
python3 -m reconciliation.reconcile status
```

### 查看未配對項目
```bash
python3 -m reconciliation.reconcile unmatched [--type bank|invoice|contract]
```

## 執行步驟

1. 解析用戶的意圖（匯入資料、執行對帳、查看狀態）
2. 如果用戶提供了檔案路徑，確認檔案存在
3. 如果是首次使用，先執行 `setup` 建立 Sheet 結構
4. 執行對應指令，設定 timeout 為 120000（匯入大檔案可能較慢）
5. 解析輸出結果，以易讀格式呈現
6. 如有「待確認」的配對，列出讓用戶確認

## 建議匯入順序

1. 先匯入合約（建立基礎資料）
2. 匯入發票
3. 匯入銀行明細
4. 執行對帳（match）

## 注意事項

- 銀行 CSV 格式因銀行不同而異，首次匯入時系統會自動偵測欄位
- 去重機制確保重複匯入同一份檔案不會產生重複資料
- 對帳結果中「待確認」的項目需要用戶人工確認
- 合約支援一次付清、頭尾款（預設30/70）、分期付款
- 所有操作都有審計日誌紀錄在「操作紀錄」分頁
