#!/bin/bash
# Threads 重複留言檢查腳本（瀏覽器版）
# 用法：bash threads_dup_checker.sh [滾動次數]
# 檢查 @jacksonwang88866 過去 24 小時內的回覆是否有重複
# 透過 AppleScript 操作 Chrome 中已登入的 Threads 頁面

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCROLL_COUNT="${1:-5}"

EXTRACT_JS="$SCRIPT_DIR/threads_dup_extract.js"
if [ ! -f "$EXTRACT_JS" ]; then
    echo '{"success":false,"error":"找不到 JS 檔案"}'
    exit 1
fi

python3 -c "
import subprocess, sys, json, time
from collections import defaultdict

def random_sleep(low, high):
    \"\"\"隨機延遲，模擬人類行為\"\"\"
    import random
    delay = random.uniform(low, high)
    time.sleep(delay)

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
    random_sleep(3, 8)
    for _ in range(10):
        ready = run_applescript('document.readyState')
        if 'complete' in ready:
            break
        random_sleep(0.8, 2.5)
    random_sleep(1.5, 4)
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

# Step 2: 導航到回覆頁面
if not navigate_to('https://www.threads.com/@jacksonwang88866/replies'):
    output(False, error='無法導航到回覆頁面', step='navigate')
    sys.exit(1)
random_sleep(2, 5)

# Step 3: 滾動載入更多回覆
for i in range(scroll_count):
    run_applescript('window.scrollBy(0, 800); \"SCROLLED\"')
    random_sleep(1.5, 4)

# 滾動回頂部
run_applescript('window.scrollTo(0, 0); \"SCROLL_TOP\"')
random_sleep(0.8, 2.5)

# Step 4: 注入提取 JS
with open(js_file, 'r') as f:
    extract_code = f.read()
run_applescript(extract_code)
random_sleep(0.8, 2.5)
result = run_applescript('_threadsDupResult')

# Step 5: 解析結果
if 'DUP_REPLIES' in result:
    parts = result.split('|||')
    total_count = int(parts[1])
    replies = []
    for i in range(2, len(parts)):
        reply_parts = parts[i].split('@@')
        if len(reply_parts) >= 3:
            replies.append({
                'text': reply_parts[0],
                'timestamp': reply_parts[1],
                'post_url': reply_parts[2]
            })

    # 按文字內容分組，找出重複
    groups = defaultdict(list)
    for r in replies:
        groups[r['text']].append(r)

    duplicates = []
    for text, items in groups.items():
        if len(items) > 1:
            duplicates.append({
                'text': text,
                'count': len(items),
                'occurrences': [{'timestamp': it['timestamp'], 'post_url': it['post_url']} for it in items]
            })

    output(True, data={
        'total_replies_24h': total_count,
        'duplicate_groups': len(duplicates),
        'duplicates': duplicates
    }, step='done')

elif 'DUP_NO_REPLIES' in result:
    output(True, data={
        'total_replies_24h': 0,
        'duplicate_groups': 0,
        'duplicates': []
    }, step='done')
else:
    output(False, error=f'提取失敗: {result}', step='extract')

" "$SCROLL_COUNT" "$EXTRACT_JS"
