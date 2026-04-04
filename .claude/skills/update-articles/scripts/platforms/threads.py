"""Threads.com article metrics fetcher using Playwright headless browser."""

import json
import re

from . import BasePlatform

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class ThreadsPlatform(BasePlatform):
    name = "Threads"
    url_pattern = r"threads\.net/@[\w.]+/post/([\w-]+)"
    _needs_browser = True

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._timeout_ms = 30000

    def configure(self, config: dict):
        threads_cfg = config.get("threads", {})
        self._timeout_ms = threads_cfg.get("timeout_ms", 30000)
        self._headless = threads_cfg.get("headless", True)

    def _ensure_browser(self):
        if not HAS_PLAYWRIGHT:
            raise ImportError(
                "playwright is required for Threads scraping.\n"
                "Install with: pip3 install playwright && playwright install chromium"
            )
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=getattr(self, "_headless", True)
            )

    def fetch_metrics(self, url: str) -> dict:
        self._ensure_browser()

        page = self._browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self._timeout_ms)
            page.wait_for_timeout(3000)  # Wait for JS to render

            html = page.content()
            metrics = self._extract_from_embedded_json(html)

            if metrics:
                return metrics

            # Fallback: try to extract from visible page content
            return self._extract_from_page(page)

        except PwTimeout:
            return self._error(f"Page load timeout ({self._timeout_ms}ms)")
        except Exception as e:
            return self._error(str(e))
        finally:
            page.close()

    def _extract_from_embedded_json(self, html: str) -> dict | None:
        """Try to extract metrics from embedded JSON in script tags."""
        # Threads embeds post data in <script type="application/json" data-sjs>
        pattern = r'<script[^>]*type="application/json"[^>]*data-sjs[^>]*>(.*?)</script>'
        scripts = re.findall(pattern, html, re.DOTALL)

        for script_content in scripts:
            try:
                data = json.loads(script_content)
                result = self._deep_find_thread_items(data)
                if result:
                    return result
            except (json.JSONDecodeError, KeyError):
                continue

        return None

    def _deep_find_thread_items(self, obj, depth=0) -> dict | None:
        """Recursively search for thread_items in nested JSON structure."""
        if depth > 15:
            return None

        if isinstance(obj, dict):
            if "thread_items" in obj:
                items = obj["thread_items"]
                if items and isinstance(items, list) and len(items) > 0:
                    return self._parse_thread_item(items[0])

            for value in obj.values():
                result = self._deep_find_thread_items(value, depth + 1)
                if result:
                    return result

        elif isinstance(obj, list):
            for item in obj:
                result = self._deep_find_thread_items(item, depth + 1)
                if result:
                    return result

        return None

    def _parse_thread_item(self, item: dict) -> dict | None:
        """Parse a thread_item dict into our metrics format."""
        post = item.get("post", {})
        if not post:
            return None

        caption = post.get("caption", {})
        text = caption.get("text", "") if isinstance(caption, dict) else str(caption)
        title = text[:100] if text else None

        like_count = post.get("like_count")
        text_info = post.get("text_post_app_info", {})
        reply_count = text_info.get("direct_reply_count") if text_info else None

        return {
            "title": title,
            "likes": like_count,
            "comments": reply_count,
            "views": None,
            "error": None,
        }

    def _extract_from_page(self, page) -> dict:
        """Fallback: extract metrics from visible page elements."""
        try:
            # Try to find like count from aria labels or text
            like_el = page.query_selector('[aria-label*="like"], [aria-label*="Like"]')
            likes = None
            if like_el:
                label = like_el.get_attribute("aria-label") or ""
                nums = re.findall(r"[\d,]+", label)
                if nums:
                    likes = int(nums[0].replace(",", ""))

            reply_el = page.query_selector('[aria-label*="repl"], [aria-label*="Repl"]')
            comments = None
            if reply_el:
                label = reply_el.get_attribute("aria-label") or ""
                nums = re.findall(r"[\d,]+", label)
                if nums:
                    comments = int(nums[0].replace(",", ""))

            if likes is not None or comments is not None:
                return {
                    "title": None,
                    "likes": likes,
                    "comments": comments,
                    "views": None,
                    "error": None,
                }

            return self._error("Could not extract metrics from page")

        except Exception as e:
            return self._error(f"Page extraction failed: {e}")

    def cleanup(self):
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    @staticmethod
    def _error(msg: str) -> dict:
        return {
            "title": None,
            "likes": None,
            "comments": None,
            "views": None,
            "error": msg,
        }
