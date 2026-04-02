#!/bin/bash
# Dcard 留言監測腳本
# 每 5 分鐘檢查一次文章留言數，有新留言時發送 macOS 通知（含留言內容）
# 文章：https://www.dcard.tw/f/talk/p/261224266
# 停止方式：kill $(cat /tmp/dcard_monitor.pid)

POST_ID="261224266"
CHECK_INTERVAL=300  # 5 分鐘 = 300 秒
STATE_FILE="/tmp/dcard_comment_count.txt"
LOG_FILE="/tmp/dcard_monitor.log"
PID_FILE="/tmp/dcard_monitor.pid"

echo $$ > "$PID_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') [啟動] Dcard 留言監測開始 (PID: $$)" | tee -a "$LOG_FILE"

# 透過 Chrome fetch API 取得留言數
get_comment_count() {
    osascript -e "
tell application \"Google Chrome\"
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains \"dcard\" then
                execute t javascript \"
                    var _dcardResult = null;
                    fetch('https://www.dcard.tw/service/api/v2/posts/$POST_ID')
                        .then(function(r) { return r.json(); })
                        .then(function(d) { _dcardResult = String(d.commentCount); })
                        .catch(function(e) { _dcardResult = 'ERROR'; });
                \"
                delay 3
                set result to execute t javascript \"_dcardResult\"
                return result
            end if
        end repeat
    end repeat
    return \"TAB_NOT_FOUND\"
end tell
" 2>/dev/null
}

# 透過 Chrome fetch API 取得指定樓層之後的新留言內容
get_new_comments() {
    local after_floor=$1
    osascript -e "
tell application \"Google Chrome\"
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains \"dcard\" then
                execute t javascript \"
                    var _dcardComments = null;
                    fetch('https://www.dcard.tw/service/api/v2/posts/$POST_ID/comments?after=$after_floor&limit=30')
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            if (Array.isArray(data)) {
                                _dcardComments = data.map(function(c) {
                                    var text = (c.content || '').replace(/\\n/g, ' ').substring(0, 60);
                                    return 'B' + c.floor + ' ' + text;
                                }).join('|||');
                            } else {
                                _dcardComments = 'ERROR';
                            }
                        })
                        .catch(function(e) { _dcardComments = 'ERROR'; });
                \"
                delay 3
                set result to execute t javascript \"_dcardComments\"
                return result
            end if
        end repeat
    end repeat
    return \"TAB_NOT_FOUND\"
end tell
" 2>/dev/null
}

# 發送包含留言內容的 macOS 通知
send_notification() {
    local old_count=$1
    local new_count=$2
    local diff=$((new_count - old_count))
    local comments_text="$3"

    # 系統通知（簡短摘要）
    osascript -e "display notification \"留言數 ${old_count} → ${new_count}（+${diff}）\n${comments_text}\" with title \"Dcard 新留言通知\" subtitle \"65歲大象全身被漆粉紅色\" sound name \"Glass\""
}

# 取得初始留言數
CURRENT_COUNT=$(get_comment_count)

if [ "$CURRENT_COUNT" = "ERROR" ] || [ "$CURRENT_COUNT" = "TAB_NOT_FOUND" ] || [ -z "$CURRENT_COUNT" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [錯誤] 無法取得留言數: $CURRENT_COUNT" | tee -a "$LOG_FILE"
    echo "請確認 Chrome 中有開啟任意 Dcard 頁面"
    exit 1
fi

echo "$CURRENT_COUNT" > "$STATE_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') [初始] 目前留言數: $CURRENT_COUNT" | tee -a "$LOG_FILE"
osascript -e "display notification \"開始監測，目前留言數: ${CURRENT_COUNT}\" with title \"Dcard 監測已啟動\" sound name \"Pop\""

# 主迴圈
while true; do
    sleep "$CHECK_INTERVAL"

    NEW_COUNT=$(get_comment_count)
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    if [ "$NEW_COUNT" = "ERROR" ] || [ "$NEW_COUNT" = "TAB_NOT_FOUND" ] || [ -z "$NEW_COUNT" ]; then
        echo "$TIMESTAMP [警告] 無法取得留言數，將在下次重試" | tee -a "$LOG_FILE"
        continue
    fi

    OLD_COUNT=$(cat "$STATE_FILE" 2>/dev/null || echo "0")

    if [ "$NEW_COUNT" -gt "$OLD_COUNT" ] 2>/dev/null; then
        DIFF=$((NEW_COUNT - OLD_COUNT))

        # 取得新留言內容
        RAW_COMMENTS=$(get_new_comments "$OLD_COUNT")

        # 解析留言內容並記錄到 log
        echo "$TIMESTAMP [新留言] 留言數: $OLD_COUNT → $NEW_COUNT (+$DIFF)" | tee -a "$LOG_FILE"

        # 將 ||| 分隔的留言逐條寫入 log
        FIRST_COMMENT=""
        IFS='|||' read -ra COMMENT_ARRAY <<< "$RAW_COMMENTS"
        for comment in "${COMMENT_ARRAY[@]}"; do
            if [ -n "$comment" ]; then
                echo "  → $comment" | tee -a "$LOG_FILE"
                if [ -z "$FIRST_COMMENT" ]; then
                    FIRST_COMMENT="$comment"
                fi
            fi
        done

        # 通知（macOS 通知有字數限制，只顯示第一則新留言摘要）
        NOTIFY_TEXT="${FIRST_COMMENT}"
        if [ "$DIFF" -gt 1 ]; then
            NOTIFY_TEXT="${FIRST_COMMENT} ...等${DIFF}則"
        fi
        send_notification "$OLD_COUNT" "$NEW_COUNT" "$NOTIFY_TEXT"

        echo "$NEW_COUNT" > "$STATE_FILE"
    else
        echo "$TIMESTAMP [檢查] 留言數: $NEW_COUNT（無變化）" | tee -a "$LOG_FILE"
    fi
done
