#!/bin/bash
# Threads 推薦 Feed 海巡腳本（瀏覽器版）
# 用法：bash threads_feed_patrol.sh browse [滾動次數]
# 透過 AppleScript 操作 Chrome 中已登入的 Threads 頁面
# 瀏覽首頁推薦 feed，提取貼文內容與 URL

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="$1"
SCROLL_COUNT="${2:-3}"

if [ -z "$MODE" ]; then
    echo '{"success":false,"error":"用法: threads_feed_patrol.sh browse [滾動次數]"}'
    exit 1
fi

if [ "$MODE" != "browse" ]; then
    echo "{\"success\":false,\"error\":\"不支援的模式: $MODE，請使用 browse\"}"
    exit 1
fi

# 載入 JS 檔案
EXTRACT_JS="$SCRIPT_DIR/threads_feed_extract.js"
if [ ! -f "$EXTRACT_JS" ]; then
    echo '{"success":false,"error":"找不到 JS 檔案"}'
    exit 1
fi

python3 -c "
import subprocess, sys, json, time

scroll_count = int(sys.argv[1])
js_file = sys.argv[2]

def escape_for_applescript_js(code):
    return code.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"').replace('\\n', ' ')

def run_applescript(js_code, find_by='threads.com'):
    js_escaped = escape_for_applescript_js(js_code)
    applescript = f'''
tell application \"Google Chrome\"
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains \"{find_by}\" then
                set jsResult to execute t javascript \"{js_escaped}\"
                return jsResult
            end if
        end repeat
    end repeat
    return \"TAB_NOT_FOUND\"
end tell
'''
    try:
        result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.stdout else 'ERROR:' + (result.stderr.strip() or 'unknown')
    except subprocess.TimeoutExpired:
        return 'ERROR:timeout'

def navigate_to(url):
    nav_js = f'window.location.href = \"{url}\"; \"NAVIGATING\"'
    result = run_applescript(nav_js)
    if 'TAB_NOT_FOUND' in result:
        return False
    time.sleep(5)
    for _ in range(10):
        ready = run_applescript('document.readyState')
        if 'complete' in ready:
            break
        time.sleep(1)
    time.sleep(2)
    return True

def output(success, data=None, error='', step=''):
    result = {'success': success}
    if data is not None:
        result['data'] = data
    if error:
        result['error'] = error
    if step:
        result['step'] = step
    print(json.dumps(result, ensure_ascii=False))

# Step 1: 確認有 threads.com 分頁
check = run_applescript('document.title')
if 'TAB_NOT_FOUND' in check:
    output(False, error='找不到 threads.com 分頁，請確認 Chrome 中有開啟 Threads', step='find_tab')
    sys.exit(1)

# Step 2: 導航到首頁（如果不在首頁）
current_url = run_applescript('window.location.href')
if '/post/' in current_url or '/@' in current_url:
    if not navigate_to('https://www.threads.com'):
        output(False, error='無法導航到 Threads 首頁', step='navigate')
        sys.exit(1)
    time.sleep(3)

# Step 3: 滾動載入更多貼文
for i in range(scroll_count):
    run_applescript('window.scrollBy(0, 800); \"SCROLLED\"')
    time.sleep(2)

# 滾動回頂部以確保能讀取所有載入的貼文
run_applescript('window.scrollTo(0, 0); \"SCROLL_TOP\"')
time.sleep(1)

# Step 4: 注入提取 JS
with open(js_file, 'r') as f:
    extract_code = f.read()
run_applescript(extract_code)
time.sleep(1)
result = run_applescript('_threadsFeedResult')

if 'FEED_POSTS' in result:
    parts = result.split('|||')
    count = int(parts[1])
    posts = []
    for i in range(2, len(parts)):
        post_parts = parts[i].split('@@')
        if len(post_parts) >= 3:
            posts.append({
                'username': post_parts[0],
                'content': post_parts[1],
                'url': post_parts[2]
            })
    output(True, data={'count': len(posts), 'posts': posts}, step='done')
elif 'FEED_EMPTY' in result:
    output(False, error='首頁沒有找到任何貼文，請確認 Threads 首頁已載入', step='extract')
else:
    output(False, error=f'提取失敗: {result}', step='extract')

" "$SCROLL_COUNT" "$EXTRACT_JS"
