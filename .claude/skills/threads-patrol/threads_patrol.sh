#!/bin/bash
# Threads 海巡留言腳本（瀏覽器版）
# 用法：
#   bash threads_patrol.sh read "貼文URL"              — 讀取貼文內容
#   bash threads_patrol.sh reply "貼文URL" "留言內容"   — 留言
#   bash threads_patrol.sh discover "@用戶名"           — 發現用戶的貼文
# 透過 AppleScript 操作 Chrome 中已登入的 Threads 頁面

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="$1"
TARGET="$2"
REPLY_TEXT="$3"

if [ -z "$MODE" ] || [ -z "$TARGET" ]; then
    echo '{"success":false,"error":"用法: threads_patrol.sh <read|reply|discover> <URL或用戶名> [留言內容]"}'
    exit 1
fi

# 載入 JS 檔案
READ_JS="$SCRIPT_DIR/threads_read_post.js"
DISCOVER_JS="$SCRIPT_DIR/threads_discover_posts.js"
REPLY_JS="$SCRIPT_DIR/threads_reply_actions.js"

python3 -c "
import subprocess, sys, json, time

def random_sleep(low, high):
    \"\"\"隨機延遲，模擬人類行為\"\"\"
    import random
    delay = random.uniform(low, high)
    time.sleep(delay)

mode = sys.argv[1]
target = sys.argv[2]
reply_text = sys.argv[3] if len(sys.argv) > 3 else ''

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
    # 等待頁面載入
    random_sleep(3, 8)
    for _ in range(10):
        ready = run_applescript('document.readyState')
        if 'complete' in ready:
            break
        random_sleep(0.8, 2.5)
    random_sleep(1.5, 4)
    return True

def output(success, data='', error='', step=''):
    result = {'success': success}
    if data:
        result['data'] = data
    if error:
        result['error'] = error
    if step:
        result['step'] = step
    print(json.dumps(result, ensure_ascii=False))

# ===== MODE: read =====
if mode == 'read':
    # 導航到貼文
    if not navigate_to(target):
        output(False, error='找不到 threads.com 分頁', step='navigate')
        sys.exit(1)

    # 載入並執行讀取 JS
    with open('$READ_JS', 'r') as f:
        read_code = f.read()
    run_applescript(read_code)
    random_sleep(0.8, 2.5)
    result = run_applescript('_threadsPatrolResult')

    if 'POST_CONTENT' in result:
        parts = result.split('|||')
        username = parts[1] if len(parts) > 1 else ''
        content = parts[2] if len(parts) > 2 else ''
        output(True, data={'username': username, 'content': content}, step='read')
    elif 'NO_CONTENT' in result or 'NO_TEXT' in result:
        output(False, error='無法提取貼文內容', step='read')
    else:
        output(False, error=f'讀取失敗: {result}', step='read')

# ===== MODE: discover =====
elif mode == 'discover':
    username = target.lstrip('@')
    profile_url = f'https://www.threads.com/@{username}'

    if not navigate_to(profile_url):
        output(False, error='找不到 threads.com 分頁', step='navigate')
        sys.exit(1)

    # 滾動載入更多貼文
    for _ in range(3):
        run_applescript('window.scrollTo(0, document.body.scrollHeight)')
        random_sleep(1.5, 4)

    # 執行發現 JS
    with open('$DISCOVER_JS', 'r') as f:
        discover_code = f.read()
    run_applescript(discover_code)
    random_sleep(0.8, 2.5)
    result = run_applescript('_threadsPatrolResult')

    if result and result != '0' and '|||' in result:
        parts = result.split('|||')
        count = parts[0]
        urls = [p for p in parts[1:] if p.strip()]
        output(True, data={'count': int(count), 'urls': urls}, step='discover')
    else:
        output(False, error=f'找不到 @{username} 的貼文', step='discover')

# ===== MODE: reply =====
elif mode == 'reply':
    if not reply_text:
        output(False, error='未提供留言內容', step='validate')
        sys.exit(1)

    # 導航到貼文
    if not navigate_to(target):
        output(False, error='找不到 threads.com 分頁', step='navigate')
        sys.exit(1)

    # 載入回覆 JS functions
    with open('$REPLY_JS', 'r') as f:
        reply_code = f.read()
    run_applescript(reply_code)
    random_sleep(0.8, 2.5)

    # 重複留言檢查：在留言前先確認頁面上沒有相同內容
    dup_keyword = ''.join(c for c in reply_text[:10] if c.isalnum() or c == ' ')
    if len(dup_keyword) >= 3:
        dup_js = f'_threadsCheckDuplicate(\"{dup_keyword}\"); _threadsPatrolResult'
        run_applescript(dup_js)
        random_sleep(0.8, 2.5)
        dup_result = run_applescript('_threadsPatrolResult')
        if 'DUP_FOUND' in str(dup_result):
            dup_text = dup_result.split('DUP_FOUND:', 1)[1] if 'DUP_FOUND:' in str(dup_result) else ''
            output(False, error=f'偵測到重複留言，頁面上已有類似內容：{dup_text}', step='duplicate_check')
            sys.exit(1)

    # 點擊回覆區域
    run_applescript('_threadsClickReply(); _threadsPatrolResult')
    random_sleep(0.8, 2.5)
    result = run_applescript('_threadsPatrolResult')

    if 'REPLY_NOT_FOUND' in str(result):
        # 嘗試滾動後重試
        run_applescript('window.scrollTo(0, document.body.scrollHeight)')
        random_sleep(1.5, 4)
        run_applescript('_threadsClickReply(); _threadsPatrolResult')
        random_sleep(0.8, 2.5)
        result = run_applescript('_threadsPatrolResult')
        if 'REPLY_NOT_FOUND' in str(result):
            output(False, error='找不到回覆區域，請確認貼文頁面已完整載入', step='click_reply')
            sys.exit(1)

    random_sleep(1.5, 4)

    # 確認回覆區域就緒
    for attempt in range(3):
        run_applescript('_threadsCheckReplyReady(); _threadsPatrolResult')
        random_sleep(0.8, 2.5)
        result = run_applescript('_threadsPatrolResult')
        if 'REPLY_READY' in str(result):
            break
        random_sleep(1.5, 4)

    # 聚焦回覆輸入區域
    run_applescript('_threadsFocusReplyEditable(); _threadsPatrolResult')
    random_sleep(0.8, 2.5)
    result = run_applescript('_threadsPatrolResult')

    if 'REPLY_EDITABLE_NOT_FOUND' in str(result):
        output(False, error='找不到回覆輸入區域', step='focus_reply')
        sys.exit(1)

    # 用剪貼簿貼上留言文字
    # 使用 pbcopy + Cmd+V 才能正確觸發 React 狀態更新
    subprocess.run(['pbcopy'], input=reply_text.encode('utf-8'))

    paste_script = '''
tell application \"Google Chrome\" to activate
delay 0.5
tell application \"System Events\"
    keystroke \"v\" using command down
end tell
'''
    subprocess.run(['osascript', '-e', paste_script], capture_output=True, text=True)
    random_sleep(1.5, 4)

    # 送出留言
    run_applescript('_threadsSubmitReply(); _threadsPatrolResult')
    random_sleep(0.8, 2.5)
    result = run_applescript('_threadsPatrolResult')

    if 'REPLY_SUBMIT_NOT_FOUND' in str(result):
        output(False, error='找不到送出按鈕', step='submit')
        sys.exit(1)

    if 'REPLY_SUBMIT_DISABLED' in str(result):
        # 按鈕停用，嘗試重新貼上
        run_applescript('_threadsFocusReplyEditable(); _threadsPatrolResult')
        random_sleep(0.8, 2.5)
        select_paste_script = '''
tell application \"Google Chrome\" to activate
delay 0.3
tell application \"System Events\"
    keystroke \"a\" using command down
    delay 0.2
    keystroke \"v\" using command down
end tell
'''
        subprocess.run(['osascript', '-e', select_paste_script], capture_output=True, text=True)
        random_sleep(1.5, 4)
        run_applescript('_threadsSubmitReply(); _threadsPatrolResult')
        random_sleep(0.8, 2.5)
        result = run_applescript('_threadsPatrolResult')
        if 'REPLY_SUBMITTED' not in str(result):
            output(False, error='送出按鈕停用，請確認 Chrome 在前景並重試', step='submit')
            sys.exit(1)

    random_sleep(2, 6)

    # 基本驗證（錯誤訊息檢查）
    run_applescript('_threadsVerifyReply(); _threadsPatrolResult')
    random_sleep(0.8, 2.5)
    result = run_applescript('_threadsPatrolResult')

    if 'REPLY_ERROR' in str(result):
        error_msg = result.split('REPLY_ERROR:', 1)[1] if 'REPLY_ERROR:' in str(result) else '未知錯誤'
        output(False, error=f'留言出現錯誤：{error_msg}', step='verify')
        sys.exit(1)

    # 內容驗證：重新載入頁面，確認留言文字真的出現
    random_sleep(1.5, 4)
    navigate_to(target)

    # 重新注入 JS functions
    with open('$REPLY_JS', 'r') as f:
        reply_code_reload = f.read()
    run_applescript(reply_code_reload)
    random_sleep(0.8, 2.5)

    # 用留言文字前 15 字搜尋（只保留字母數字和空格，避免跳脫問題）
    search_keyword = ''.join(c for c in reply_text[:15] if c.isalnum() or c == ' ')
    verify_js = f'_threadsVerifyReplyContent(\"{search_keyword}\"); _threadsPatrolResult'
    run_applescript(verify_js)
    random_sleep(0.8, 2.5)
    result = run_applescript('_threadsPatrolResult')

    if 'VERIFY_FOUND' in str(result):
        output(True, data='留言成功（已驗證出現在頁面上）！', step='done')
    elif 'VERIFY_NOT_FOUND' in str(result):
        output(False, error='留言未出現在頁面上，可能送出失敗。請檢查 Chrome 是否在前景、Threads 是否正常。', step='verify_content')
    else:
        output(False, error=f'驗證異常: {result}', step='verify_content')

else:
    output(False, error=f'不支援的模式: {mode}，請使用 read / reply / discover')

" "$MODE" "$TARGET" "$REPLY_TEXT"
