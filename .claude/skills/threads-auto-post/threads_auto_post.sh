#!/bin/bash
# Threads 自動發文腳本（瀏覽器版）
# 用法：bash threads_auto_post.sh "貼文內容"
# 透過 AppleScript 操作 Chrome 中已登入的 Threads 頁面
#
# 重要：文字輸入使用 pbcopy + Cmd+V 剪貼簿貼上方式
# 因為 execCommand('insertText') 不會觸發 React 狀態更新，導致 Post 按鈕停用

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
POST_TEXT="$1"

if [ -z "$POST_TEXT" ]; then
    echo '{"success":false,"error":"未提供貼文內容","step":"validate"}'
    exit 1
fi

# 檢查文字長度
TEXT_LEN=${#POST_TEXT}
if [ "$TEXT_LEN" -gt 500 ]; then
    echo "{\"success\":false,\"error\":\"貼文內容超過 500 字（目前 ${TEXT_LEN} 字）\",\"step\":\"validate\"}"
    exit 1
fi

# 載入 JS 檔案
JS_FILE="$SCRIPT_DIR/threads_post_actions.js"
if [ ! -f "$JS_FILE" ]; then
    echo '{"success":false,"error":"找不到 JS 檔案","step":"init"}'
    exit 1
fi

# 使用 Python 處理跳脫和 AppleScript 執行
python3 -c "
import subprocess, sys, json, time

def random_sleep(low, high):
    \"\"\"隨機延遲，模擬人類行為\"\"\"
    import random
    delay = random.uniform(low, high)
    time.sleep(delay)

post_text = sys.argv[1]
js_file = sys.argv[2]

# 讀取 JS 檔案
with open(js_file, 'r') as f:
    js_code = f.read()

# 跳脫 JS 文字（用於嵌入 AppleScript 字串）
def escape_for_applescript_js(code):
    return code.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"').replace('\\n', ' ')

js_escaped = escape_for_applescript_js(js_code)

def run_applescript(js_to_execute, find_by='threads.com'):
    js_clean = escape_for_applescript_js(js_to_execute)
    applescript = f'''
tell application \"Google Chrome\"
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains \"{find_by}\" then
                set jsResult to execute t javascript \"{js_clean}\"
                return jsResult
            end if
        end repeat
    end repeat
    return \"TAB_NOT_FOUND\"
end tell
'''
    try:
        result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True, timeout=30)
        return (result.stdout.strip() if result.stdout else 'ERROR:' + (result.stderr.strip() or 'unknown'))
    except subprocess.TimeoutExpired:
        return 'ERROR:timeout'

def output(success, message, step=''):
    print(json.dumps({'success': success, 'message': message, 'step': step}, ensure_ascii=False))

# Step 1: 載入 JS functions
result = run_applescript(js_escaped)
if result == 'TAB_NOT_FOUND':
    output(False, '找不到 threads.com 分頁，請確認 Chrome 中有開啟 Threads', 'find_tab')
    sys.exit(1)

# Step 2: 點擊撰寫按鈕
result = run_applescript('_threadsClickCompose(); _threadsPostResult')

if 'COMPOSE_NOT_FOUND' in str(result):
    random_sleep(1.5, 4)
    result = run_applescript('_threadsClickCompose(); _threadsPostResult')
    if 'COMPOSE_NOT_FOUND' in str(result):
        output(False, '找不到撰寫按鈕，請確認 Threads 首頁已載入完成', 'compose')
        sys.exit(1)

random_sleep(1.5, 4)

# Step 3: 檢查 modal 是否開啟
modal_ready = False
for attempt in range(5):
    result = run_applescript('_threadsCheckModal(); _threadsPostResult')
    if 'MODAL_READY' in str(result):
        modal_ready = True
        break
    random_sleep(1.5, 4)

if not modal_ready:
    output(False, '撰寫視窗未開啟，請重試', 'modal')
    sys.exit(1)

random_sleep(0.8, 2.5)

# Step 4: 聚焦文字輸入區域
result = run_applescript('_threadsFocusEditable(); _threadsPostResult')

if 'EDITABLE_NOT_FOUND' in str(result):
    output(False, '找不到文字輸入區域', 'focus')
    sys.exit(1)

random_sleep(0.3, 1.0)

# Step 5: 用剪貼簿貼上文字
# 這是最關鍵的步驟：使用 pbcopy + Cmd+V 才能正確觸發 React 狀態更新
# execCommand('insertText') 雖然能顯示文字，但 React 不會感知，Post 按鈕會保持停用
subprocess.run(['pbcopy'], input=post_text.encode('utf-8'))

paste_script = '''
tell application \"Google Chrome\" to activate
delay 0.5
tell application \"System Events\"
    keystroke \"v\" using command down
end tell
'''
subprocess.run(['osascript', '-e', paste_script], capture_output=True, text=True)
random_sleep(1.5, 4)

# Step 6: 點擊發佈
result = run_applescript('_threadsClickPost(); _threadsPostResult')

if 'POST_BUTTON_NOT_FOUND' in str(result):
    output(False, '找不到發佈按鈕', 'post')
    sys.exit(1)

if 'POST_BUTTON_DISABLED' in str(result):
    # 按鈕停用，文字可能未正確輸入，嘗試重新貼上
    # 重新聚焦
    run_applescript('_threadsFocusEditable(); _threadsPostResult')
    random_sleep(0.3, 1.0)
    # 先選全部再貼上覆蓋
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

    # 再試一次點擊發佈
    result = run_applescript('_threadsClickPost(); _threadsPostResult')
    if 'POST_CLICKED' not in str(result):
        output(False, '發佈按鈕停用，文字可能未正確輸入。請確認 Chrome 在前景並重試', 'post')
        sys.exit(1)

random_sleep(2, 6)

# Step 7: 驗證
result = run_applescript('_threadsVerifyPost(); _threadsPostResult')

if 'POST_SUCCESS' in str(result):
    output(True, '貼文發佈成功！', 'done')
elif 'ERROR:' in str(result):
    error_msg = result.split('ERROR:', 1)[1] if 'ERROR:' in str(result) else '未知錯誤'
    output(False, f'發佈出現錯誤：{error_msg}', 'verify')
else:
    output(True, '貼文已送出（請確認 Threads 上是否出現）', 'done')

" "$POST_TEXT" "$JS_FILE"
