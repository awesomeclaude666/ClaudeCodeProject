#!/bin/bash
# Threads 自動回覆 - 留言監測腳本
# 用法：
#   bash threads_auto_reply_check.sh check "POST_URL"         # 檢查新留言
#   bash threads_auto_reply_check.sh read "POST_URL"          # 讀取原文內容
#   bash threads_auto_reply_check.sh mark_replied "POST_URL" "COMMENT_ID"  # 標記已回覆
#   bash threads_auto_reply_check.sh reset "POST_URL"         # 重設狀態（新 session）

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="$1"
POST_URL="$2"
COMMENT_ID="$3"

if [ -z "$MODE" ] || [ -z "$POST_URL" ]; then
    echo '{"success":false,"error":"用法: threads_auto_reply_check.sh <check|read|mark_replied|reset> <POST_URL> [COMMENT_ID]"}'
    exit 1
fi

EXTRACT_JS="$SCRIPT_DIR/threads_auto_reply_extract.js"
if [ ! -f "$EXTRACT_JS" ] && [ "$MODE" != "mark_replied" ] && [ "$MODE" != "reset" ]; then
    echo '{"success":false,"error":"找不到 JS 檔案"}'
    exit 1
fi

# 從 URL 提取 shortcode
SHORTCODE=$(echo "$POST_URL" | grep -oE 'post/([^/?]+)' | head -1 | sed 's|post/||')
if [ -z "$SHORTCODE" ]; then
    echo '{"success":false,"error":"無法從 URL 解析出 shortcode"}'
    exit 1
fi

STATE_FILE="/tmp/threads_auto_reply_STATE_${SHORTCODE}.json"
MY_USERNAME="jacksonwang88866"

python3 -c "
import subprocess, sys, json, time, os
from datetime import datetime

def random_sleep(low, high):
    \"\"\"隨機延遲，模擬人類行為\"\"\"
    import random
    delay = random.uniform(low, high)
    time.sleep(delay)

mode = sys.argv[1]
post_url = sys.argv[2]
comment_id = sys.argv[3] if len(sys.argv) > 3 else ''
shortcode = sys.argv[4]
state_file = sys.argv[5]
my_username = sys.argv[6]
js_file = sys.argv[7] if len(sys.argv) > 7 else ''

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

def load_state():
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'post_url': post_url,
        'replied_ids': [],
        'seen_ids': [],
        'session_reply_count': 0,
        'last_check': ''
    }

def save_state(state):
    state['last_check'] = datetime.now().isoformat()
    tmp_file = state_file + '.tmp'
    with open(tmp_file, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.rename(tmp_file, state_file)

# ========== mark_replied 模式 ==========
if mode == 'mark_replied':
    if not comment_id:
        output(False, error='缺少 COMMENT_ID', step='mark_replied')
        sys.exit(1)
    state = load_state()
    if comment_id not in state['replied_ids']:
        state['replied_ids'].append(comment_id)
    state['session_reply_count'] = state.get('session_reply_count', 0) + 1
    save_state(state)
    output(True, data={
        'marked': comment_id,
        'session_reply_count': state['session_reply_count'],
        'total_replied': len(state['replied_ids'])
    }, step='mark_replied')
    sys.exit(0)

# ========== reset 模式 ==========
if mode == 'reset':
    state = load_state()
    state['session_reply_count'] = 0
    save_state(state)
    output(True, data={
        'reset': True,
        'kept_replied_ids': len(state['replied_ids'])
    }, step='reset')
    sys.exit(0)

# ========== 確認有 threads.com 分頁 ==========
check = run_applescript('document.title')
if 'TAB_NOT_FOUND' in check:
    output(False, error='找不到 threads.com 分頁，請確認 Chrome 中有開啟 Threads', step='find_tab')
    sys.exit(1)

# ========== 導航到貼文頁面 ==========
if not navigate_to(post_url):
    output(False, error='無法導航到貼文頁面', step='navigate')
    sys.exit(1)
random_sleep(2, 5)

# ========== read 模式：讀取原文 ==========
if mode == 'read':
    read_js = '''
    var _readResult = null;
    (function() {
        var containers = document.querySelectorAll('[data-pressable-container=\"true\"]');
        if (containers.length === 0) { _readResult = 'NO_POST'; return; }
        var c = containers[0];
        var userLink = c.querySelector('a[href^=\"/@\"]');
        var username = userLink ? userLink.getAttribute('href').replace('/@', '').split('/')[0] : 'unknown';
        var spans = c.querySelectorAll('span[dir=\"auto\"]');
        var text = '';
        for (var i = 0; i < spans.length; i++) {
            var t = spans[i].textContent.trim();
            if (t.length > text.length && t !== username && t.length > 3) text = t;
        }
        _readResult = 'POST_OK|||' + username + '|||' + text.substring(0, 500);
    })();
    '''
    run_applescript(read_js)
    random_sleep(0.8, 2.5)
    result = run_applescript('_readResult')

    if 'POST_OK' in result:
        parts = result.split('|||')
        output(True, data={
            'username': parts[1] if len(parts) > 1 else 'unknown',
            'content': parts[2] if len(parts) > 2 else ''
        }, step='read')
    else:
        output(False, error=f'無法讀取原文: {result}', step='read')
    sys.exit(0)

# ========== check 模式：檢查新留言 ==========
if mode == 'check':
    # 滾動載入更多留言
    for i in range(3):
        run_applescript('window.scrollTo(0, document.body.scrollHeight); \"SCROLLED\"')
        random_sleep(1.5, 4)
    run_applescript('window.scrollTo(0, 0); \"SCROLL_TOP\"')
    random_sleep(0.8, 2.5)

    # 注入提取 JS（替換 MY_USERNAME）
    with open(js_file, 'r') as f:
        extract_code = f.read()
    extract_code = extract_code.replace('_MY_USERNAME_', my_username)
    run_applescript(extract_code)
    random_sleep(0.8, 2.5)
    result = run_applescript('_threadsAutoReplyResult')

    if 'COMMENTS' in result and result.startswith('COMMENTS'):
        parts = result.split('|||')
        total_count = int(parts[1])
        all_comments = []
        for i in range(2, len(parts)):
            comment_parts = parts[i].split('@@')
            if len(comment_parts) >= 4:
                all_comments.append({
                    'id': comment_parts[0],
                    'username': comment_parts[1],
                    'text': comment_parts[2],
                    'time': comment_parts[3]
                })

        # 載入狀態
        state = load_state()
        replied_ids = set(state.get('replied_ids', []))
        seen_ids = set(state.get('seen_ids', []))

        # 過濾：排除自己的留言和已回覆的
        new_comments = []
        for c in all_comments:
            if c['username'] == my_username:
                continue
            if c['id'] in replied_ids:
                continue
            if c['id'] not in seen_ids:
                new_comments.append(c)

        # 更新 seen_ids（記錄所有看過的留言）
        for c in all_comments:
            if c['id'] not in seen_ids:
                state.setdefault('seen_ids', []).append(c['id'])
        save_state(state)

        output(True, data={
            'new_comments': new_comments,
            'total_comments': total_count,
            'previously_replied': len(replied_ids),
            'session_reply_count': state.get('session_reply_count', 0)
        }, step='check')

    elif 'NO_COMMENTS' in result:
        output(True, data={
            'new_comments': [],
            'total_comments': 0,
            'previously_replied': 0,
            'session_reply_count': 0
        }, step='check')
    else:
        output(False, error=f'提取失敗: {result}', step='extract')

    sys.exit(0)

output(False, error=f'不支援的模式: {mode}', step='unknown')
" "$MODE" "$POST_URL" "$COMMENT_ID" "$SHORTCODE" "$STATE_FILE" "$MY_USERNAME" "$EXTRACT_JS"
