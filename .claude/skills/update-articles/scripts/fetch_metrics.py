#!/usr/bin/env python3
"""Main orchestrator: read Google Sheet URLs, fetch metrics, update sheet."""

import argparse
import json
import os
import sys
import time

# Add scripts directory to path so platforms package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from platforms import discover_platforms
from sheet_client import SheetClient


def load_config(config_path: str) -> dict:
    config_path = os.path.expanduser(config_path)
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        print("Copy config.example.json to config.json and fill in your settings.")
        sys.exit(1)

    with open(config_path) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Fetch article metrics and update Google Sheet")
    parser.add_argument("--config", default="./config.json", help="Path to config.json")
    parser.add_argument("--dry-run", action="store_true", help="Fetch metrics but don't write to sheet")
    parser.add_argument("--row", type=int, help="Process only a specific row number")
    parser.add_argument("--platform", help="Process only URLs from a specific platform")
    args = parser.parse_args()

    config = load_config(args.config)
    delay = config.get("request_delay_seconds", 1.5)

    # Init sheet client
    print("Connecting to Google Sheet...")
    sheet = SheetClient(config)

    # Discover platforms
    registry = discover_platforms()
    print(f"Loaded platforms: {', '.join(p.name for p in registry.platforms)}")

    # Read URLs
    rows = sheet.read_urls()
    if args.row:
        rows = [r for r in rows if r["row"] == args.row]
    if not rows:
        print("No URLs found to process.")
        return

    print(f"Found {len(rows)} URLs to process.\n")

    # Group by platform for efficiency (Dcard first, then Threads)
    categorized = []
    for row_data in rows:
        url = row_data["url"]
        platform = registry.get_platform(url)
        if platform is None:
            print(f"  [SKIP] Row {row_data['row']}: Unknown platform for {url}")
            continue
        if args.platform and platform.name.lower() != args.platform.lower():
            continue
        categorized.append((row_data, platform))

    # Sort: non-browser platforms first (faster)
    categorized.sort(key=lambda x: getattr(x[1], "_needs_browser", False))

    # Fetch metrics
    updates = []
    succeeded = 0
    failed = 0
    total = len(categorized)

    for i, (row_data, platform) in enumerate(categorized, 1):
        url = row_data["url"]
        row_num = row_data["row"]
        print(f"[{i}/{total}] {platform.name:<10} Row {row_num}: {url}")

        try:
            metrics = platform.fetch_metrics(url)
        except Exception as e:
            metrics = {
                "title": None, "likes": None, "comments": None,
                "views": None, "error": str(e),
            }

        if metrics.get("error"):
            print(f"  ERROR: {metrics['error']}")
            failed += 1
        else:
            parts = []
            if metrics.get("likes") is not None:
                parts.append(f"likes={metrics['likes']}")
            if metrics.get("comments") is not None:
                parts.append(f"comments={metrics['comments']}")
            if metrics.get("views") is not None:
                parts.append(f"views={metrics['views']}")
            print(f"  -> {', '.join(parts)}")
            succeeded += 1

        updates.append({
            "row": row_num,
            "platform": platform.name,
            "metrics": metrics,
        })

        if i < total:
            time.sleep(delay)

    # Update sheet
    print(f"\nSummary: {succeeded}/{total} succeeded, {failed} failed")

    if args.dry_run:
        print("[DRY RUN] Skipping sheet update.")
    elif updates:
        print("Updating Google Sheet...")
        sheet.batch_update(updates)
        print("Sheet updated successfully.")

    # Cleanup
    registry.cleanup_all()


if __name__ == "__main__":
    main()
