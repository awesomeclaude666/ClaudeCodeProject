#!/usr/bin/env python3
"""Push (comment) on PTT posts.

Usage: push.py <board> <payload.json>
payload.json: [{"aid": "...", "push_type": "推|噓|→", "content": "..."}]
Env: PTT_ID, PTT_PW
Output: JSON list of results to stdout.
"""
import json
import os
import sys
import time

import PyPtt


PUSH_MAP = {
    "推": PyPtt.CommentType.PUSH,
    "噓": PyPtt.CommentType.BOO,
    "→": PyPtt.CommentType.ARROW,
}


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: push.py <board> <payload.json>", file=sys.stderr)
        return 2
    board = sys.argv[1]
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        payload = json.load(f)

    ptt_id = os.environ.get("PTT_ID")
    ptt_pw = os.environ.get("PTT_PW")
    if not ptt_id or not ptt_pw:
        print("PTT_ID / PTT_PW env not set", file=sys.stderr)
        return 3

    bot = PyPtt.API()
    out: list[dict] = []
    try:
        bot.login(ptt_id, ptt_pw, kick_other_session=False)
        for item in payload:
            aid = item["aid"]
            push_type = PUSH_MAP.get(item.get("push_type", "推"), PyPtt.CommentType.PUSH)
            content = item["content"]
            # PTT 推文上限大約 35 全形字，硬性截斷
            if len(content) > 35:
                content = content[:35]
            try:
                bot.comment(board, push_type, content, aid=aid)
                out.append({"aid": aid, "ok": True})
            except Exception as e:  # noqa: BLE001
                out.append({"aid": aid, "ok": False, "error": str(e)})
            time.sleep(3)  # 避免被視為灌水
    finally:
        try:
            bot.logout()
        except Exception:
            pass

    json.dump(out, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
