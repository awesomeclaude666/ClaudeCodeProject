#!/usr/bin/env python3
"""Fetch hot/explosive posts from a PTT board.

Usage: fetch_hot.py <board> <count>
Env: PTT_ID, PTT_PW
Output: JSON list to stdout: [{aid, title, author, push_count, content}]
"""
import json
import os
import sys

import PyPtt


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: fetch_hot.py <board> <count>", file=sys.stderr)
        return 2
    board = sys.argv[1]
    want = int(sys.argv[2])

    ptt_id = os.environ.get("PTT_ID")
    ptt_pw = os.environ.get("PTT_PW")
    if not ptt_id or not ptt_pw:
        print("PTT_ID / PTT_PW env not set", file=sys.stderr)
        return 3

    bot = PyPtt.API()
    results: list[dict] = []
    try:
        bot.login(ptt_id, ptt_pw, kick_other_session=False)
        newest = bot.get_newest_index(PyPtt.NewIndex.BOARD, board=board)
        # Walk backwards looking for hot posts (爆 or push >= 50)
        idx = newest
        scanned = 0
        while idx > 0 and len(results) < want and scanned < 80:
            scanned += 1
            try:
                post = bot.get_post(board, index=idx)
            except Exception:
                idx -= 1
                continue
            idx -= 1
            if not post:
                continue
            push_num = post.get(PyPtt.PostField.push_number)
            # push_number is a string like "爆", "X1", "10" or None
            hot = False
            if push_num == "爆":
                hot = True
            else:
                try:
                    if push_num and int(push_num) >= 50:
                        hot = True
                except (TypeError, ValueError):
                    pass
            if not hot:
                continue
            results.append(
                {
                    "aid": post.get(PyPtt.PostField.aid),
                    "url": post.get(PyPtt.PostField.url),
                    "title": post.get(PyPtt.PostField.title),
                    "author": post.get(PyPtt.PostField.author),
                    "push_count": push_num,
                    "content": (post.get(PyPtt.PostField.content) or "")[:4000],
                }
            )
    finally:
        try:
            bot.logout()
        except Exception:
            pass

    json.dump(results, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
