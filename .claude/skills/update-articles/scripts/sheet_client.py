"""Google Sheets client for reading article URLs and writing metrics."""

import os
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


class SheetClient:
    def __init__(self, config: dict):
        sheets_cfg = config["google_sheets"]
        cred_path = os.path.expanduser(sheets_cfg["credentials_path"])

        if not os.path.exists(cred_path):
            raise FileNotFoundError(
                f"Credentials file not found: {cred_path}\n"
                "Please follow setup.md to configure Google Cloud Service Account."
            )

        credentials = Credentials.from_service_account_file(cred_path, scopes=SCOPES)
        gc = gspread.authorize(credentials)

        try:
            spreadsheet = gc.open_by_key(sheets_cfg["sheet_id"])
        except gspread.exceptions.SpreadsheetNotFound:
            raise ValueError(
                f"Sheet not found (ID: {sheets_cfg['sheet_id']}). "
                "Verify the sheet_id in config.json and ensure the sheet is "
                "shared with the service account email in your credentials file."
            )

        worksheet_name = sheets_cfg.get("worksheet_name", "Sheet1")
        try:
            self.ws = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            available = [s.title for s in spreadsheet.worksheets()]
            raise ValueError(
                f"Worksheet '{worksheet_name}' not found. "
                f"Available worksheets: {available}"
            )

        self.columns = config.get("columns", {
            "url": "A",
            "platform": "B",
            "title": "C",
            "likes": "D",
            "comments": "E",
            "views": "F",
            "last_updated": "G",
        })
        self.data_start_row = config.get("data_start_row", 2)

    def read_urls(self) -> list[dict]:
        """Read all article URLs from the sheet."""
        url_col = self.columns["url"]
        all_values = self.ws.col_values(self._col_to_num(url_col))

        rows = []
        for i, val in enumerate(all_values):
            row_num = i + 1
            if row_num < self.data_start_row:
                continue
            url = val.strip() if val else ""
            if url and url.startswith("http"):
                rows.append({"row": row_num, "url": url})

        return rows

    def batch_update(self, updates: list[dict]):
        """Batch update metrics for multiple rows.

        Each update: {"row": int, "platform": str, "metrics": dict}
        """
        if not updates:
            return

        cells = []
        for item in updates:
            row = item["row"]
            metrics = item.get("metrics", {})
            platform = item.get("platform", "")

            if platform:
                cells.append({
                    "range": f"{self.columns['platform']}{row}",
                    "values": [[platform]],
                })

            if metrics.get("title") is not None:
                cells.append({
                    "range": f"{self.columns['title']}{row}",
                    "values": [[metrics["title"]]],
                })

            if metrics.get("likes") is not None:
                cells.append({
                    "range": f"{self.columns['likes']}{row}",
                    "values": [[metrics["likes"]]],
                })

            if metrics.get("comments") is not None:
                cells.append({
                    "range": f"{self.columns['comments']}{row}",
                    "values": [[metrics["comments"]]],
                })

            if metrics.get("views") is not None:
                cells.append({
                    "range": f"{self.columns['views']}{row}",
                    "values": [[metrics["views"]]],
                })

            cells.append({
                "range": f"{self.columns['last_updated']}{row}",
                "values": [[datetime.now().strftime("%Y-%m-%d %H:%M:%S")]],
            })

        # gspread batch_update expects list of {"range": ..., "values": ...}
        self.ws.batch_update(cells, value_input_option="USER_ENTERED")

    @staticmethod
    def _col_to_num(col_letter: str) -> int:
        """Convert column letter (A, B, ..., Z, AA, ...) to 1-based number."""
        result = 0
        for ch in col_letter.upper():
            result = result * 26 + (ord(ch) - ord("A") + 1)
        return result
