#!/usr/bin/env python3
"""Threads 全域安全模組 — 跨所有 skill 的速率限制、隨機延遲、指數退避"""

import os
import sys
import json
import time
import random
import argparse
from datetime import datetime, date

# === 安全限制常數 ===

DAILY_LIMITS = {
    "replies": 25,
    "posts": 8,
    "total_actions": 30,
}

MIN_SECONDS_BETWEEN_ACTIONS = 45

DELAY_RANGES = {
    "between_replies": (45, 120),
    "between_posts": (120, 300),
    "between_reply_and_post": (60, 180),
    "page_load_settle": (3, 8),
    "pre_type_pause": (1, 3),
    "post_type_pause": (1, 4),
    "post_submit_verify": (3, 8),
    "between_scrolls": (1.5, 4),
    "session_start": (5, 15),
}

BACKOFF = {
    "initial_wait": 60,
    "multiplier": 2.0,
    "max_wait": 1800,
    "max_consecutive_errors": 5,
}

STATE_FILE = "/tmp/threads_global_safety.json"


def load_state():
    """載入全域狀態檔"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "version": 1,
        "daily_counts": {},
        "last_action": None,
        "backoff": {
            "current_multiplier": 1.0,
            "consecutive_errors": 0,
            "cooldown_until": None,
        },
        "action_log": [],
    }


def save_state(state):
    """儲存全域狀態檔"""
    state["action_log"] = state["action_log"][-100:]
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_today():
    return date.today().isoformat()


def get_daily_counts(state):
    today = get_today()
    if today not in state["daily_counts"]:
        state["daily_counts"][today] = {
            "replies": 0,
            "posts": 0,
            "total_actions": 0,
        }
    return state["daily_counts"][today]


def cmd_check(args):
    """預檢：檢查是否允許執行操作"""
    state = load_state()
    counts = get_daily_counts(state)
    action = args.action
    now = datetime.now()

    backoff = state["backoff"]
    if backoff["consecutive_errors"] >= BACKOFF["max_consecutive_errors"]:
        print(json.dumps({
            "allowed": False,
            "wait_seconds": 0,
            "reason": f"連續失敗 {backoff['consecutive_errors']} 次，已達上限 {BACKOFF['max_consecutive_errors']}。請手動執行 reset 指令解除",
        }, ensure_ascii=False))
        return

    if backoff.get("cooldown_until"):
        cooldown = datetime.fromisoformat(backoff["cooldown_until"])
        if now < cooldown:
            wait = (cooldown - now).total_seconds()
            print(json.dumps({
                "allowed": False,
                "wait_seconds": round(wait, 1),
                "reason": f"指數退避中，還需等待 {round(wait)}s（連續失敗 {backoff['consecutive_errors']} 次）",
            }, ensure_ascii=False))
            return

    action_key = "replies" if action == "reply" else "posts"
    if counts.get(action_key, 0) >= DAILY_LIMITS.get(action_key, 999):
        print(json.dumps({
            "allowed": False,
            "wait_seconds": 0,
            "reason": f"今日 {action_key} 已達上限 {DAILY_LIMITS[action_key]}（目前 {counts[action_key]}）",
        }, ensure_ascii=False))
        return

    if counts.get("total_actions", 0) >= DAILY_LIMITS["total_actions"]:
        print(json.dumps({
            "allowed": False,
            "wait_seconds": 0,
            "reason": f"今日總操作已達上限 {DAILY_LIMITS['total_actions']}（目前 {counts['total_actions']}）",
        }, ensure_ascii=False))
        return

    wait_seconds = 0
    if state["last_action"]:
        last_time = datetime.fromisoformat(state["last_action"]["timestamp"])
        elapsed = (now - last_time).total_seconds()
        if elapsed < MIN_SECONDS_BETWEEN_ACTIONS:
            wait_seconds = MIN_SECONDS_BETWEEN_ACTIONS - elapsed
            wait_seconds += random.uniform(5, 30)

    if action == "reply":
        delay_range = DELAY_RANGES["between_replies"]
    else:
        delay_range = DELAY_RANGES["between_posts"]

    min_delay = max(wait_seconds, 0)
    if min_delay < delay_range[0] and state["last_action"]:
        extra = random.uniform(delay_range[0] - min_delay, delay_range[1] - min_delay)
        wait_seconds = max(wait_seconds, extra)

    print(json.dumps({
        "allowed": True,
        "wait_seconds": round(max(wait_seconds, 0), 1),
        "reason": f"允許。今日 {action_key}: {counts.get(action_key, 0)}/{DAILY_LIMITS.get(action_key, 999)}",
        "daily_counts": counts,
    }, ensure_ascii=False))


def cmd_record(args):
    """記錄一次操作"""
    state = load_state()
    counts = get_daily_counts(state)
    now = datetime.now()

    action = args.action
    success = args.success.lower() == "true"
    action_key = "replies" if action == "reply" else "posts"

    if success:
        counts[action_key] = counts.get(action_key, 0) + 1
        counts["total_actions"] = counts.get("total_actions", 0) + 1

        state["backoff"]["consecutive_errors"] = 0
        state["backoff"]["current_multiplier"] = 1.0
        state["backoff"]["cooldown_until"] = None
    else:
        errors = state["backoff"]["consecutive_errors"] + 1
        state["backoff"]["consecutive_errors"] = errors

        wait = min(
            BACKOFF["initial_wait"] * (BACKOFF["multiplier"] ** (errors - 1)),
            BACKOFF["max_wait"],
        )
        cooldown = datetime.fromtimestamp(now.timestamp() + wait)
        state["backoff"]["cooldown_until"] = cooldown.isoformat()
        state["backoff"]["current_multiplier"] = BACKOFF["multiplier"] ** errors

    state["last_action"] = {
        "timestamp": now.isoformat(),
        "type": action,
        "skill": args.skill,
        "success": success,
    }

    state["action_log"].append({
        "timestamp": now.isoformat(),
        "type": action,
        "skill": args.skill,
        "success": success,
        "target": getattr(args, "target", ""),
        "error": getattr(args, "error", ""),
    })

    save_state(state)

    print(json.dumps({
        "recorded": True,
        "action": action,
        "success": success,
        "daily_counts": counts,
        "consecutive_errors": state["backoff"]["consecutive_errors"],
    }, ensure_ascii=False))


def cmd_delay(args):
    """取得隨機延遲秒數"""
    context = args.context
    if context in DELAY_RANGES:
        low, high = DELAY_RANGES[context]
        wait = random.uniform(low, high)
    else:
        wait = random.uniform(3, 10)

    print(json.dumps({
        "wait_seconds": round(wait, 1),
        "context": context,
    }, ensure_ascii=False))


def cmd_status(args):
    """查看目前狀態"""
    state = load_state()
    counts = get_daily_counts(state)

    recent = state["action_log"][-10:] if state["action_log"] else []

    print(json.dumps({
        "today": get_today(),
        "daily_counts": counts,
        "daily_limits": DAILY_LIMITS,
        "last_action": state["last_action"],
        "backoff": state["backoff"],
        "recent_actions": recent,
    }, ensure_ascii=False, indent=2))


def cmd_reset(args):
    """重設退避狀態"""
    state = load_state()
    state["backoff"] = {
        "current_multiplier": 1.0,
        "consecutive_errors": 0,
        "cooldown_until": None,
    }
    save_state(state)
    print(json.dumps({"reset": True, "message": "退避狀態已重設"}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Threads 全域安全模組")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_check = subparsers.add_parser("check", help="預檢是否允許操作")
    p_check.add_argument("--action", required=True, choices=["reply", "post"])
    p_check.add_argument("--skill", required=True)

    p_record = subparsers.add_parser("record", help="記錄操作結果")
    p_record.add_argument("--action", required=True, choices=["reply", "post"])
    p_record.add_argument("--skill", required=True)
    p_record.add_argument("--success", required=True, choices=["true", "false"])
    p_record.add_argument("--target", default="")
    p_record.add_argument("--error", default="")

    p_delay = subparsers.add_parser("delay", help="取得隨機延遲")
    p_delay.add_argument("--context", required=True)

    subparsers.add_parser("status", help="查看狀態")
    subparsers.add_parser("reset", help="重設退避狀態")

    args = parser.parse_args()

    handlers = {
        "check": cmd_check,
        "record": cmd_record,
        "delay": cmd_delay,
        "status": cmd_status,
        "reset": cmd_reset,
    }

    handlers[args.command](args)


if __name__ == "__main__":
    main()
