#!/usr/bin/env python3
"""PTT 自動化 CLI — 發文、推文、讀文、列表、監測"""

import os
import sys
import json
import time
import random
import argparse
import subprocess

try:
    import PyPtt
except ImportError:
    print(json.dumps({
        "error": "PyPtt 未安裝，請執行: pip3 install PyPtt",
    }, ensure_ascii=False))
    sys.exit(1)

SAFETY_MODULE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "ptt_safety.py"
)


def safety_check(action: str):
    """執行安全預檢"""
    if not os.path.exists(SAFETY_MODULE):
        return {"allowed": True, "wait_seconds": 0}
    try:
        result = subprocess.run(
            [sys.executable, SAFETY_MODULE, "check", "--action", action],
            capture_output=True, text=True, timeout=10,
        )
        return json.loads(result.stdout)
    except Exception:
        return {"allowed": True, "wait_seconds": 0}


def safety_record(action: str, success: bool, target: str = "", error: str = ""):
    """記錄操作結果"""
    if not os.path.exists(SAFETY_MODULE):
        return
    try:
        subprocess.run(
            [sys.executable, SAFETY_MODULE, "record",
             "--action", action,
             "--success", "true" if success else "false",
             "--target", target, "--error", error],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        pass


def create_api():
    """建立 PyPtt API 實例（靜音模式）"""
    try:
        from SingleLog import LogLevel
        return PyPtt.API(log_level=LogLevel.SILENT)
    except ImportError:
        # fallback: 嘗試 PyPtt 自帶的 LogLevel
        try:
            return PyPtt.API(log_level=PyPtt.LogLevel.SILENT)
        except Exception:
            return PyPtt.API()


def login_ptt():
    """登入 PTT，從環境變數取得帳密"""
    username = os.environ.get("PTT_USERNAME", "")
    password = os.environ.get("PTT_PASSWORD", "")

    if not username or not password:
        return None, {"error": "缺少環境變數 PTT_USERNAME 和/或 PTT_PASSWORD"}

    ptt = create_api()
    try:
        ptt.login(ptt_id=username, ptt_pw=password, kick_other_session=True)
        return ptt, None
    except PyPtt.WrongIDorPassword:
        return None, {"error": "帳號或密碼錯誤"}
    except PyPtt.LoginError as e:
        return None, {"error": f"登入失敗: {str(e)}"}
    except PyPtt.OnlySecureConnection:
        return None, {"error": "PTT 要求安全連線，請稍後再試"}
    except Exception as e:
        return None, {"error": f"登入時發生錯誤: {str(e)}"}


def safe_logout(ptt):
    """安全登出"""
    if ptt:
        try:
            ptt.logout()
        except Exception:
            pass


def output_json(data: dict):
    print(json.dumps(data, ensure_ascii=False, indent=2))


# === 指令處理 ===

def cmd_post(args):
    """發文到指定看板"""
    check = safety_check("post")
    if not check.get("allowed", True):
        return {"action": "post", "success": False, "safety_block": True,
                "reason": check.get("reason", "")}

    wait = check.get("wait_seconds", 0)
    if wait > 0:
        print(f"安全等待 {wait:.0f} 秒...", file=sys.stderr)
        time.sleep(wait)

    ptt, err = login_ptt()
    if err:
        return {"action": "post", "success": False, **err}

    try:
        # title_index: 分類編號，通常 1="[閒聊]" 之類
        # 不同看板有不同分類，預設用 args.category (數字)
        ptt.post(
            board=args.board,
            title_index=args.category,
            title=args.title,
            content=args.content,
            sign_file=0,
        )
        safety_record("post", success=True, target=f"{args.board}/{args.title}")
        return {
            "action": "post",
            "success": True,
            "board": args.board,
            "title": args.title,
            "content_length": len(args.content),
        }
    except PyPtt.NoPermission:
        safety_record("post", success=False, error="no_permission")
        return {"action": "post", "success": False,
                "error": f"沒有在 {args.board} 發文的權限"}
    except PyPtt.NoSuchBoard:
        safety_record("post", success=False, error="no_such_board")
        return {"action": "post", "success": False,
                "error": f"看板 {args.board} 不存在"}
    except Exception as e:
        safety_record("post", success=False, error=str(e))
        return {"action": "post", "success": False, "error": str(e)}
    finally:
        safe_logout(ptt)


def cmd_push(args):
    """對文章推文/噓文/箭頭"""
    check = safety_check("push")
    if not check.get("allowed", True):
        return {"action": "push", "success": False, "safety_block": True,
                "reason": check.get("reason", "")}

    wait = check.get("wait_seconds", 0)
    if wait > 0:
        print(f"安全等待 {wait:.0f} 秒...", file=sys.stderr)
        time.sleep(wait)

    # 解析推文類型
    push_type_map = {
        "push": PyPtt.CommentType.PUSH,
        "boo": PyPtt.CommentType.BOO,
        "arrow": PyPtt.CommentType.ARROW,
    }
    comment_type = push_type_map.get(args.type, PyPtt.CommentType.PUSH)

    ptt, err = login_ptt()
    if err:
        return {"action": "push", "success": False, **err}

    try:
        kwargs = {
            "board": args.board,
            "comment_type": comment_type,
            "content": args.content,
        }
        # 支援 AID 或 index
        if args.aid:
            kwargs["aid"] = args.aid
        elif args.index:
            kwargs["index"] = int(args.index)
        else:
            return {"action": "push", "success": False,
                    "error": "需要指定 --aid 或 --index"}

        ptt.comment(**kwargs)
        safety_record("push", success=True,
                      target=f"{args.board}/{args.aid or args.index}")
        return {
            "action": "push",
            "success": True,
            "board": args.board,
            "type": args.type,
            "aid": args.aid,
            "index": args.index,
            "content": args.content,
        }
    except PyPtt.NoFastComment:
        safety_record("push", success=False, error="too_fast")
        return {"action": "push", "success": False,
                "error": "推文間隔太短，請稍後再試"}
    except PyPtt.NoPermission:
        safety_record("push", success=False, error="no_permission")
        return {"action": "push", "success": False,
                "error": f"沒有在 {args.board} 推文的權限"}
    except PyPtt.NoSuchPost:
        safety_record("push", success=False, error="no_such_post")
        return {"action": "push", "success": False,
                "error": "文章不存在"}
    except Exception as e:
        safety_record("push", success=False, error=str(e))
        return {"action": "push", "success": False, "error": str(e)}
    finally:
        safe_logout(ptt)


def cmd_read(args):
    """讀取文章內容"""
    ptt, err = login_ptt()
    if err:
        return {"action": "read", "success": False, **err}

    try:
        kwargs = {"board": args.board}
        if args.aid:
            kwargs["aid"] = args.aid
        elif args.index:
            kwargs["index"] = int(args.index)
        else:
            return {"action": "read", "success": False,
                    "error": "需要指定 --aid 或 --index"}

        post = ptt.get_post(**kwargs)

        if post is None:
            return {"action": "read", "success": False,
                    "error": "文章不存在或已刪除"}

        # 提取推文列表
        comments = []
        raw_comments = post.get("comments", []) or []
        for c in raw_comments[:50]:  # 最多回傳 50 則推文
            comments.append({
                "type": str(c.get("type", "")),
                "author": c.get("author", ""),
                "content": c.get("content", ""),
                "time": c.get("time", ""),
            })

        return {
            "action": "read",
            "success": True,
            "board": args.board,
            "aid": post.get("aid", args.aid or ""),
            "title": post.get("title", ""),
            "author": post.get("author", ""),
            "date": post.get("date", ""),
            "content": post.get("content", ""),
            "push_number": post.get("push_number", ""),
            "comments_count": len(raw_comments),
            "comments": comments,
            "url": post.get("url", ""),
        }
    except PyPtt.NoSuchBoard:
        return {"action": "read", "success": False,
                "error": f"看板 {args.board} 不存在"}
    except Exception as e:
        return {"action": "read", "success": False, "error": str(e)}
    finally:
        safe_logout(ptt)


def cmd_list(args):
    """列出看板最新文章"""
    ptt, err = login_ptt()
    if err:
        return {"action": "list", "success": False, **err}

    try:
        count = args.count or 10

        # 如果有搜尋關鍵字
        search_list = None
        if args.keyword:
            search_list = [(PyPtt.SearchType.KEYWORD, args.keyword)]

        newest = ptt.get_newest_index(
            PyPtt.NewIndex.BOARD, args.board,
            search_list=search_list,
        )

        articles = []
        for i in range(newest, max(newest - count, 0), -1):
            try:
                post = ptt.get_post(
                    args.board, index=i, query=True,
                    search_list=search_list,
                )
                if post is None:
                    continue

                # 跳過已刪除的文章
                title = post.get("title", "")
                if not title or title == "(本文已被刪除)":
                    continue

                articles.append({
                    "index": i,
                    "aid": post.get("aid", ""),
                    "title": title,
                    "author": post.get("author", ""),
                    "date": post.get("list_date", ""),
                    "push_number": post.get("push_number", ""),
                    "url": post.get("url", ""),
                })
            except Exception:
                continue

        return {
            "action": "list",
            "success": True,
            "board": args.board,
            "count": len(articles),
            "newest_index": newest,
            "keyword": args.keyword or None,
            "articles": articles,
        }
    except PyPtt.NoSuchBoard:
        return {"action": "list", "success": False,
                "error": f"看板 {args.board} 不存在"}
    except Exception as e:
        return {"action": "list", "success": False, "error": str(e)}
    finally:
        safe_logout(ptt)


def cmd_monitor(args):
    """持續監測看板新文"""
    ptt, err = login_ptt()
    if err:
        output_json({"action": "monitor", "success": False, **err})
        return

    try:
        board = args.board
        interval = args.interval or 60
        keyword = args.keyword

        search_list = None
        if keyword:
            search_list = [(PyPtt.SearchType.KEYWORD, keyword)]

        # 取得初始最新編號
        last_index = ptt.get_newest_index(
            PyPtt.NewIndex.BOARD, board,
            search_list=search_list,
        )

        output_json({
            "action": "monitor",
            "status": "started",
            "board": board,
            "keyword": keyword,
            "interval": interval,
            "starting_index": last_index,
        })
        sys.stdout.flush()

        while True:
            time.sleep(interval + random.uniform(-10, 10))

            try:
                newest = ptt.get_newest_index(
                    PyPtt.NewIndex.BOARD, board,
                    search_list=search_list,
                )

                if newest > last_index:
                    new_posts = []
                    for i in range(last_index + 1, newest + 1):
                        try:
                            post = ptt.get_post(
                                board, index=i, query=True,
                                search_list=search_list,
                            )
                            if post and post.get("title"):
                                new_posts.append({
                                    "index": i,
                                    "aid": post.get("aid", ""),
                                    "title": post.get("title", ""),
                                    "author": post.get("author", ""),
                                    "push_number": post.get("push_number", ""),
                                })
                        except Exception:
                            continue

                    if new_posts:
                        output_json({
                            "action": "monitor",
                            "status": "new_posts",
                            "board": board,
                            "count": len(new_posts),
                            "posts": new_posts,
                        })
                        sys.stdout.flush()

                        # macOS 通知
                        for p in new_posts[:3]:
                            try:
                                subprocess.run([
                                    "osascript", "-e",
                                    f'display notification "{p["author"]}: {p["title"][:40]}" '
                                    f'with title "PTT {board} 新文章"'
                                ], timeout=5)
                            except Exception:
                                pass

                    last_index = newest

            except Exception as e:
                print(f"監測錯誤: {e}", file=sys.stderr)
                # 嘗試重新連線
                try:
                    safe_logout(ptt)
                    time.sleep(5)
                    ptt, err = login_ptt()
                    if err:
                        output_json({"action": "monitor", "status": "error",
                                     "error": "重新連線失敗"})
                        return
                except Exception:
                    output_json({"action": "monitor", "status": "error",
                                 "error": "重新連線失敗"})
                    return

    except KeyboardInterrupt:
        output_json({"action": "monitor", "status": "stopped"})
    except PyPtt.NoSuchBoard:
        output_json({"action": "monitor", "success": False,
                     "error": f"看板 {board} 不存在"})
    finally:
        safe_logout(ptt)


def cmd_test(args):
    """測試登入連線"""
    ptt, err = login_ptt()
    if err:
        return {"action": "test", "success": False, **err}

    try:
        username = os.environ.get("PTT_USERNAME", "")
        user_info = ptt.get_user(username)
        return {
            "action": "test",
            "success": True,
            "message": "登入成功",
            "username": username,
            "login_count": user_info.get("login_count", ""),
            "last_login": user_info.get("last_login", ""),
        }
    except Exception as e:
        return {"action": "test", "success": True,
                "message": f"登入成功（取得用戶資訊失敗: {e}）"}
    finally:
        safe_logout(ptt)


def cmd_boards(args):
    """搜尋看板"""
    ptt, err = login_ptt()
    if err:
        return {"action": "boards", "success": False, **err}

    try:
        boards = ptt.get_all_boards()
        keyword = args.keyword.lower() if args.keyword else ""

        if keyword:
            boards = [b for b in boards if keyword in b.lower()]

        return {
            "action": "boards",
            "success": True,
            "keyword": args.keyword,
            "count": len(boards[:50]),
            "boards": boards[:50],
        }
    except Exception as e:
        return {"action": "boards", "success": False, "error": str(e)}
    finally:
        safe_logout(ptt)


def main():
    parser = argparse.ArgumentParser(description="PTT 自動化 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # post
    p_post = subparsers.add_parser("post", help="發文到指定看板")
    p_post.add_argument("--board", required=True, help="看板名稱")
    p_post.add_argument("--title", required=True, help="文章標題")
    p_post.add_argument("--content", required=True, help="文章內容")
    p_post.add_argument("--category", type=int, default=1,
                        help="文章分類編號（預設 1）")

    # push (comment)
    p_push = subparsers.add_parser("push", help="推文/噓文/箭頭")
    p_push.add_argument("--board", required=True, help="看板名稱")
    p_push.add_argument("--aid", help="文章 AID")
    p_push.add_argument("--index", help="文章編號")
    p_push.add_argument("--type", choices=["push", "boo", "arrow"],
                        default="push", help="推文類型")
    p_push.add_argument("--content", required=True, help="推文內容")

    # read
    p_read = subparsers.add_parser("read", help="讀取文章內容")
    p_read.add_argument("--board", required=True, help="看板名稱")
    p_read.add_argument("--aid", help="文章 AID")
    p_read.add_argument("--index", help="文章編號")

    # list
    p_list = subparsers.add_parser("list", help="列出看板最新文章")
    p_list.add_argument("--board", required=True, help="看板名稱")
    p_list.add_argument("--count", type=int, default=10, help="顯示數量")
    p_list.add_argument("--keyword", help="搜尋關鍵字")

    # monitor
    p_monitor = subparsers.add_parser("monitor", help="持續監測看板新文")
    p_monitor.add_argument("--board", required=True, help="看板名稱")
    p_monitor.add_argument("--interval", type=int, default=60,
                           help="檢查間隔（秒）")
    p_monitor.add_argument("--keyword", help="過濾關鍵字")

    # test
    subparsers.add_parser("test", help="測試登入連線")

    # boards
    p_boards = subparsers.add_parser("boards", help="搜尋看板")
    p_boards.add_argument("--keyword", help="看板名稱關鍵字")

    args = parser.parse_args()

    handlers = {
        "post": cmd_post,
        "push": cmd_push,
        "read": cmd_read,
        "list": cmd_list,
        "monitor": cmd_monitor,
        "test": cmd_test,
        "boards": cmd_boards,
    }

    handler = handlers[args.command]

    if args.command == "monitor":
        # monitor 自行處理輸出
        handler(args)
    else:
        try:
            result = handler(args)
            output_json(result)
        except Exception as e:
            output_json({"action": args.command, "success": False,
                         "error": str(e)})
            sys.exit(1)


if __name__ == "__main__":
    main()
