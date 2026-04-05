#!/bin/bash
# Threads 留言監測腳本
# 用法：bash threads_monitor.sh <Threads貼文URL> [檢查間隔秒數]
# 停止方式：kill $(cat /tmp/threads_monitor.pid)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="$1"
CHECK_INTERVAL="${2:-300}"
PID_FILE="/tmp/threads_monitor.pid"
LOG_FILE="/tmp/threads_monitor.log"

# 解析 URL 和 OP username
if [[ "$INPUT" != *"threads"* ]]; then
    echo "[錯誤] 請提供 Threads 貼文 URL"
    echo "用法: bash $0 <Threads貼文URL> [檢查間隔秒數]"
    exit 1
fi

# Extract OP username from URL: /@username/post/shortcode
OP_USERNAME=$(echo "$INPUT" | grep -oE '/@([^/]+)/' | head -1 | tr -d '/@/')
SHORTCODE=$(echo "$INPUT" | grep -oE 'post/([^/?]+)' | head -1 | sed 's|post/||')

if [ -z "$OP_USERNAME" ] || [ -z "$SHORTCODE" ]; then
    echo "[錯誤] 無法從 URL 解析出用戶名或短碼"
    exit 1
fi

STATE_FILE="/tmp/threads_monitor_${SHORTCODE}.txt"
echo $$ > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') [啟動] Threads 監測: @${OP_USERNAME}/post/${SHORTCODE} (PID: $$)" | tee -a "$LOG_FILE"

# 準備 JavaScript：把 OP_USERNAME 替換進去
JS_CODE=$(cat "$SCRIPT_DIR/threads_extract.js" | sed "s/_OP_USERNAME_/$OP_USERNAME/g" | tr '\n' ' ')

get_replies() {
    python3 -c "
import subprocess

js_code = '''$JS_CODE'''
js_escaped = js_code.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"')

# 先重載頁面，等待載入，滾動載入更多留言，再提取
applescript = f'''
tell application \"Google Chrome\"
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains \"$SHORTCODE\" then
                execute t javascript \"location.reload()\"
                delay 6
                repeat 10 times
                    set readyState to execute t javascript \"document.readyState\"
                    if readyState is \"complete\" then exit repeat
                    delay 1
                end repeat
                delay 2
                -- 滾動載入更多留言
                execute t javascript \"window.scrollTo(0, document.body.scrollHeight)\"
                delay 2
                execute t javascript \"window.scrollTo(0, document.body.scrollHeight)\"
                delay 2
                execute t javascript \"{js_escaped}\"
                delay 1
                set result to execute t javascript \"_threadsResult\"
                return result
            end if
        end repeat
    end repeat
    return \"TAB_NOT_FOUND\"
end tell
'''

result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True)
print(result.stdout.strip() if result.stdout else 'ERROR')
" 2>/dev/null
}

send_notification() {
    local old_count=$1
    local new_count=$2
    local diff=$((new_count - old_count))
    local text="$3"
    osascript -e "display notification \"留言 ${old_count} → ${new_count}（+${diff}）\n${text}\" with title \"Threads 新留言\" subtitle \"@${OP_USERNAME} 的貼文\" sound name \"Glass\""
}

# 取得初始留言
RESULT=$(get_replies)

if [ "$RESULT" = "TAB_NOT_FOUND" ] || [ "$RESULT" = "ERROR" ] || [ -z "$RESULT" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [錯誤] 無法取得留言: $RESULT" | tee -a "$LOG_FILE"
    echo "請確認 Chrome 中有開啟該 Threads 貼文"
    exit 1
fi

# 解析結果：格式為 "數量|||留言1|||留言2|||..."
CURRENT_COUNT=$(echo "$RESULT" | cut -d'|' -f1)
echo "$CURRENT_COUNT" > "$STATE_FILE"

echo "$(date '+%Y-%m-%d %H:%M:%S') [初始] 目前留言數: $CURRENT_COUNT" | tee -a "$LOG_FILE"

# 顯示現有留言到 log
IFS='|||' read -ra PARTS <<< "$RESULT"
for part in "${PARTS[@]}"; do
    if [[ "$part" == @* ]]; then
        echo "  $part" | tee -a "$LOG_FILE"
    fi
done

osascript -e "display notification \"開始監測，目前 ${CURRENT_COUNT} 則留言\" with title \"Threads 監測已啟動\" subtitle \"@${OP_USERNAME}\" sound name \"Pop\""

# 主迴圈
while true; do
    JITTER=$((RANDOM % 60 - 30))
    ACTUAL_INTERVAL=$((CHECK_INTERVAL + JITTER))
    if [ "$ACTUAL_INTERVAL" -lt 30 ]; then ACTUAL_INTERVAL=30; fi
    sleep "$ACTUAL_INTERVAL"

    RESULT=$(get_replies)
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    if [ "$RESULT" = "TAB_NOT_FOUND" ] || [ "$RESULT" = "ERROR" ] || [ -z "$RESULT" ]; then
        echo "$TIMESTAMP [警告] 無法取得留言，下次重試" | tee -a "$LOG_FILE"
        continue
    fi

    NEW_COUNT=$(echo "$RESULT" | cut -d'|' -f1)
    OLD_COUNT=$(cat "$STATE_FILE" 2>/dev/null || echo "0")

    if [ "$NEW_COUNT" -gt "$OLD_COUNT" ] 2>/dev/null; then
        DIFF=$((NEW_COUNT - OLD_COUNT))
        echo "$TIMESTAMP [新留言] 留言數: $OLD_COUNT → $NEW_COUNT (+$DIFF)" | tee -a "$LOG_FILE"

        # 取出新留言（最後 DIFF 則）
        IFS='|||' read -ra ALL_PARTS <<< "$RESULT"
        REPLY_PARTS=()
        for part in "${ALL_PARTS[@]}"; do
            if [[ "$part" == @* ]]; then
                REPLY_PARTS+=("$part")
            fi
        done

        FIRST_NEW=""
        START_IDX=$((${#REPLY_PARTS[@]} - DIFF))
        if [ "$START_IDX" -lt 0 ]; then START_IDX=0; fi
        for ((i=START_IDX; i<${#REPLY_PARTS[@]}; i++)); do
            echo "  → ${REPLY_PARTS[$i]}" | tee -a "$LOG_FILE"
            if [ -z "$FIRST_NEW" ]; then
                FIRST_NEW="${REPLY_PARTS[$i]}"
            fi
        done

        NOTIFY_TEXT="$FIRST_NEW"
        if [ "$DIFF" -gt 1 ]; then
            NOTIFY_TEXT="${FIRST_NEW} ...等${DIFF}則"
        fi
        send_notification "$OLD_COUNT" "$NEW_COUNT" "$NOTIFY_TEXT"

        echo "$NEW_COUNT" > "$STATE_FILE"
    else
        echo "$TIMESTAMP [檢查] 留言數: $NEW_COUNT（無變化）" | tee -a "$LOG_FILE"
    fi
done
