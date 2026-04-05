#!/usr/bin/env python3
"""Threads API 貼文管理 CLI — 發文、回覆、查看、搜尋、反查 ID、對話串"""

import os
import sys
import json
import time
import random
import subprocess
import argparse

import requests

SAFETY_MODULE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "threads-safety", "threads_safety.py"
)

RATE_LIMIT_CODES = {4, 32, 613, 80004}


def safety_check(action: str, skill: str = "threads-poster"):
    """執行全域安全預檢"""
    if not os.path.exists(SAFETY_MODULE):
        return {"allowed": True, "wait_seconds": 0}
    try:
        result = subprocess.run(
            [sys.executable, SAFETY_MODULE, "check", "--action", action, "--skill", skill],
            capture_output=True, text=True, timeout=10,
        )
        return json.loads(result.stdout)
    except Exception:
        return {"allowed": True, "wait_seconds": 0}


def safety_record(action: str, success: bool, skill: str = "threads-poster",
                   target: str = "", error: str = ""):
    """記錄操作結果到全域安全模組"""
    if not os.path.exists(SAFETY_MODULE):
        return
    try:
        subprocess.run(
            [sys.executable, SAFETY_MODULE, "record",
             "--action", action, "--skill", skill,
             "--success", "true" if success else "false",
             "--target", target, "--error", error],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        pass


class ThreadsAPI:
    """Threads Graph API 封裝"""

    BASE_URL = "https://graph.threads.net/v1.0"
    PUBLISH_WAIT_SECONDS = 30

    def __init__(self, access_token: str, user_id: str):
        self.access_token = access_token
        self.user_id = user_id
        self.session = requests.Session()

    def _request(self, method: str, endpoint: str, params: dict = None) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token
        resp = self.session.request(method, url, params=params, timeout=30)
        data = resp.json()
        if resp.status_code != 200:
            error_info = data.get("error", {})
            error_msg = error_info.get("message", resp.reason)
            error_code = error_info.get("code", 0)
            error_type = error_info.get("type", "unknown")

            if error_code in RATE_LIMIT_CODES:
                safety_record("reply", success=False, error=f"rate_limit:{error_code}")

            raise RuntimeError(
                json.dumps({
                    "api_error": True,
                    "code": error_code,
                    "type": error_type,
                    "message": error_msg,
                }, ensure_ascii=False)
            )
        return data

    def get_profile(self) -> dict:
        return self._request("GET", "me", {
            "fields": "id,username,threads_profile_picture_url,threads_biography"
        })

    def create_container(self, text: str, reply_to_id: str = None) -> str:
        params = {"media_type": "TEXT", "text": text}
        if reply_to_id:
            params["reply_to_id"] = reply_to_id
        result = self._request("POST", f"{self.user_id}/threads", params)
        return result["id"]

    def publish_container(self, container_id: str) -> dict:
        return self._request("POST", f"{self.user_id}/threads_publish", {
            "creation_id": container_id,
        })

    def post_thread(self, text: str) -> dict:
        print("建立貼文容器...", file=sys.stderr)
        container_id = self.create_container(text)
        wait = self.PUBLISH_WAIT_SECONDS + random.uniform(5, 15)
        print(f"容器已建立 (id: {container_id})，等待 {wait:.0f} 秒...", file=sys.stderr)
        time.sleep(wait)
        print("發布中...", file=sys.stderr)
        return self.publish_container(container_id)

    def reply_to_thread(self, text: str, reply_to_id: str) -> dict:
        print(f"建立回覆容器 (reply_to: {reply_to_id})...", file=sys.stderr)
        container_id = self.create_container(text, reply_to_id=reply_to_id)
        wait = self.PUBLISH_WAIT_SECONDS + random.uniform(5, 15)
        print(f"容器已建立 (id: {container_id})，等待 {wait:.0f} 秒...", file=sys.stderr)
        time.sleep(wait)
        print("發布回覆中...", file=sys.stderr)
        return self.publish_container(container_id)

    def list_threads(self, limit: int = 10) -> list:
        result = self._request("GET", f"{self.user_id}/threads", {
            "fields": "id,text,timestamp,is_reply,reply_audience",
            "limit": limit,
        })
        return result.get("data", [])

    def search_threads(self, query: str) -> list:
        result = self._request("GET", f"{self.user_id}/threads_keyword_search", {
            "q": query,
            "search_type": "TOP",
            "fields": "id,text,username,timestamp",
        })
        return result.get("data", [])

    def get_replies(self, thread_id: str) -> list:
        result = self._request("GET", f"{thread_id}/replies", {
            "fields": "id,text,username,timestamp",
        })
        return result.get("data", [])

    def get_conversation(self, thread_id: str) -> list:
        """取得貼文的完整對話串（含巢狀回覆）"""
        result = self._request("GET", f"{thread_id}/conversation", {
            "fields": "id,text,username,timestamp",
        })
        return result.get("data", [])


def output_json(data: dict):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_post(api: ThreadsAPI, args) -> dict:
    check = safety_check("post")
    if not check.get("allowed", True):
        return {"action": "post", "success": False, "safety_block": True,
                "reason": check.get("reason", "")}
    wait = check.get("wait_seconds", 0)
    if wait > 0:
        print(f"安全等待 {wait:.0f} 秒...", file=sys.stderr)
        time.sleep(wait)

    result = api.post_thread(args.text)
    safety_record("post", success=True, target=result.get("id", ""))
    return {"action": "post", "success": True, "post_id": result.get("id"), "text": args.text}


def cmd_reply(api: ThreadsAPI, args) -> dict:
    check = safety_check("reply")
    if not check.get("allowed", True):
        return {"action": "reply", "success": False, "safety_block": True,
                "reason": check.get("reason", "")}
    wait = check.get("wait_seconds", 0)
    if wait > 0:
        print(f"安全等待 {wait:.0f} 秒...", file=sys.stderr)
        time.sleep(wait)

    result = api.reply_to_thread(args.text, args.post_id)
    safety_record("reply", success=True, target=args.post_id)
    return {"action": "reply", "success": True, "reply_id": result.get("id"),
            "reply_to": args.post_id, "text": args.text}


def cmd_list(api: ThreadsAPI, args) -> dict:
    posts = api.list_threads(args.limit)
    return {"action": "list", "count": len(posts), "posts": posts}


def cmd_search(api: ThreadsAPI, args) -> dict:
    posts = api.search_threads(args.query)
    return {"action": "search", "query": args.query, "count": len(posts), "posts": posts}


def cmd_profile(api: ThreadsAPI, args) -> dict:
    profile = api.get_profile()
    return {"action": "profile", **profile}


def cmd_replies(api: ThreadsAPI, args) -> dict:
    replies = api.get_replies(args.thread_id)
    return {"action": "replies", "thread_id": args.thread_id, "count": len(replies), "replies": replies}


def cmd_get_id(api: ThreadsAPI, args) -> dict:
    """從貼文文字內容反查 media ID"""
    search_text = args.search_text
    posts = api.list_threads(25)

    for post in posts:
        post_text = post.get("text", "")
        if search_text[:30] in post_text or post_text[:30] in search_text:
            return {"action": "get_id", "success": True,
                    "media_id": post["id"], "text": post_text[:80],
                    "timestamp": post.get("timestamp", "")}

    return {"action": "get_id", "success": False,
            "error": f"找不到包含 '{search_text[:30]}...' 的貼文",
            "searched": len(posts)}


def cmd_conversation(api: ThreadsAPI, args) -> dict:
    """取得貼文的完整對話串"""
    conversation = api.get_conversation(args.thread_id)
    return {"action": "conversation", "thread_id": args.thread_id,
            "count": len(conversation), "messages": conversation}


def main():
    parser = argparse.ArgumentParser(description="Threads API 貼文管理")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_post = subparsers.add_parser("post", help="發布新貼文")
    p_post.add_argument("text", help="貼文內容")

    p_reply = subparsers.add_parser("reply", help="回覆貼文")
    p_reply.add_argument("post_id", help="要回覆的貼文 ID")
    p_reply.add_argument("text", help="回覆內容")

    p_list = subparsers.add_parser("list", help="查看最近貼文")
    p_list.add_argument("limit", nargs="?", type=int, default=10, help="顯示數量")

    p_search = subparsers.add_parser("search", help="搜尋公開貼文")
    p_search.add_argument("query", help="搜尋關鍵字")

    subparsers.add_parser("profile", help="查看帳號資訊")

    p_replies = subparsers.add_parser("replies", help="查看貼文回覆")
    p_replies.add_argument("thread_id", help="貼文 ID")

    p_get_id = subparsers.add_parser("get_id", help="從貼文文字反查 media ID")
    p_get_id.add_argument("search_text", help="貼文文字內容（前 30 字即可）")

    p_conversation = subparsers.add_parser("conversation", help="取得完整對話串")
    p_conversation.add_argument("thread_id", help="貼文 ID")

    args = parser.parse_args()

    token = os.environ.get("THREADS_ACCESS_TOKEN", "")
    user_id = os.environ.get("THREADS_USER_ID", "")
    if not token or not user_id:
        output_json({"error": "Missing environment variables: THREADS_ACCESS_TOKEN and/or THREADS_USER_ID"})
        sys.exit(1)

    api = ThreadsAPI(token, user_id)

    handlers = {
        "post": cmd_post,
        "reply": cmd_reply,
        "list": cmd_list,
        "search": cmd_search,
        "profile": cmd_profile,
        "replies": cmd_replies,
        "get_id": cmd_get_id,
        "conversation": cmd_conversation,
    }

    try:
        result = handlers[args.command](api, args)
        output_json(result)
    except RuntimeError as e:
        try:
            error_data = json.loads(str(e))
            safety_record(args.command, success=False, error=str(e))
            output_json({"action": args.command, "success": False, **error_data})
        except json.JSONDecodeError:
            output_json({"action": args.command, "success": False, "error": str(e)})
        sys.exit(1)
    except Exception as e:
        safety_record(args.command, success=False, error=str(e))
        output_json({"action": args.command, "success": False, "error": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    main()
