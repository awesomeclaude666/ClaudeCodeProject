"""Dcard.tw article metrics fetcher using public API."""

import re
import time

import requests

from . import BasePlatform

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class DcardPlatform(BasePlatform):
    name = "Dcard"
    url_pattern = r"dcard\.tw/.*?(?:/p/|@[\w.-]+/)(\d+)"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": _USER_AGENT,
            "Referer": "https://www.dcard.tw/",
            "Accept": "application/json",
        })

    def extract_post_id(self, url: str) -> str | None:
        match = re.search(r"/p/(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"@[\w.-]+/(\d+)", url)
        return match.group(1) if match else None

    def fetch_metrics(self, url: str) -> dict:
        post_id = self.extract_post_id(url)
        if not post_id:
            return self._error(f"Cannot extract post ID from URL: {url}")

        api_url = f"https://www.dcard.tw/_api/posts/{post_id}"

        for attempt in range(3):
            try:
                resp = self._session.get(api_url, timeout=15)

                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "title": data.get("title", ""),
                        "likes": data.get("likeCount"),
                        "comments": data.get("commentCount"),
                        "views": None,  # Dcard public API does not expose views
                        "error": None,
                    }

                if resp.status_code == 404:
                    return self._error("Post not found (404)")

                if resp.status_code in (403, 429):
                    wait = 2 ** (attempt + 1)
                    print(f"  [Dcard] HTTP {resp.status_code}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                return self._error(f"HTTP {resp.status_code}")

            except requests.RequestException as e:
                if attempt < 2:
                    time.sleep(2)
                    continue
                return self._error(str(e))

        return self._error("Max retries exceeded")

    @staticmethod
    def _error(msg: str) -> dict:
        return {
            "title": None,
            "likes": None,
            "comments": None,
            "views": None,
            "error": msg,
        }
