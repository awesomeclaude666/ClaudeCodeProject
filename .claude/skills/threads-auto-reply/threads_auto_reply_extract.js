/* Threads 貼文留言提取 - 由 threads_auto_reply_check.sh 注入 */
/* 重要：所有註解必須使用 block comment，因為 AppleScript 注入時會把換行變空格 */
/* 如果使用 // 單行註解，會把後面所有程式碼都註解掉 */
var _threadsAutoReplyResult = null;
(function() {
    var MY_USERNAME = '_MY_USERNAME_';

    /* 提取留言文字（過濾 UI 雜訊），回傳最長的有意義文字 */
    function extractCommentText(container, username) {
        var spans = container.querySelectorAll('span[dir="auto"]');
        var bestText = '';
        var timeHint = '';
        for (var i = 0; i < spans.length; i++) {
            var t = spans[i].textContent.trim();
            if (t.length <= 2) continue;

            /* 檢查是否為時間標記 */
            if (t.match(/^\d+\s*(\u79d2|\u5206\u9418|\u5c0f\u6642|\u5929|\u65e5|\u9031)\u524d?$/)
                || t.match(/^\d+\s*(s|m|h|d|w)$/)
                || t.match(/^\d+\s+(seconds?|minutes?|hours?|days?|weeks?)\s*ago$/i)
                || t === '\u525b\u525b' || t === '\u73fe\u5728'
                || t.toLowerCase() === 'just now' || t.toLowerCase() === 'now') {
                if (!timeHint) timeHint = t;
                continue;
            }

            /* 過濾 UI 雜訊 */
            if (t === username) continue;
            if (t.indexOf('\u7ffb\u8b6f') !== -1 || t.indexOf('Translate') !== -1) continue;
            if (t === '\u56de\u8986' || t === 'Reply') continue;
            if (t === '\u8b9a' || t === 'Like') continue;
            if (t.indexOf('\u67e5\u770b') === 0 || t.indexOf('View') === 0) continue;
            if (t.indexOf('\u70ba\u4f60\u63a8\u85a6') === 0 || t.indexOf('Suggested') === 0) continue;
            if (t === '\u5df2\u7de8\u8f2f' || t === 'Edited') continue;
            if (t === '\u5df2\u8a8d\u8b49' || t === 'Verified') continue;
            if (t.match(/^[\d,]+$/)) continue;
            if (t.match(/^\d+\u842c?$/)) continue;
            if (t.indexOf('\u500b\u8b9a') !== -1 || t.indexOf('likes') !== -1) continue;
            if (t.indexOf('\u5247\u56de\u8986') !== -1 || t.indexOf('replies') !== -1) continue;
            if (t.indexOf('\u5247\u7559\u8a00') !== -1) continue;
            if (t === '\u7559\u8a00' || t === 'Comment') continue;
            if (t === '\u8ee2\u767c' || t === 'Repost' || t === 'Share') continue;
            if (t === '\u5f15\u7528' || t === 'Quote') continue;
            if (t === '\u66f4\u591a' || t === 'More') continue;

            /* 保留最長的有意義文字 */
            if (t.length > bestText.length) {
                bestText = t;
            }
        }

        /* 也嘗試從 <time> 元素取得時間 */
        if (!timeHint) {
            var timeEl = container.querySelector('time[datetime]');
            if (timeEl) {
                timeHint = timeEl.textContent.trim();
            }
        }

        return { text: bestText, time: timeHint };
    }

    /* 主提取邏輯 */
    var containers = document.querySelectorAll('[data-pressable-container="true"]');
    if (containers.length <= 1) {
        /* 只有 OP 原文或沒有任何容器 */
        _threadsAutoReplyResult = 'NO_COMMENTS';
        return;
    }

    var replies = [];
    var seen = {};

    /* 從 index 1 開始，跳過第一個 container（OP 原文） */
    for (var ci = 1; ci < containers.length; ci++) {
        var container = containers[ci];

        /* 提取用戶名 */
        var userLink = container.querySelector('a[href^="/@"]');
        if (!userLink) continue;
        var username = userLink.getAttribute('href').replace('/@', '').split('/')[0].split('?')[0];
        if (!username || username.length === 0) continue;

        /* 提取留言內容 */
        var result = extractCommentText(container, username);
        if (result.text.length < 3) continue;

        /* 產生 comment_id（確定性 key） */
        var commentId = username + '::' + result.text.substring(0, 30).replace(/\s+/g, '_').replace(/\|/g, '-').replace(/@/g, '-');

        /* 去重 */
        if (seen[commentId]) continue;
        seen[commentId] = true;

        /* 清理文字中的分隔符（避免破壞解析） */
        var cleanText = result.text.replace(/\n/g, ' ').replace(/\|/g, '/').replace(/@/g, '(at)').substring(0, 200);
        var cleanTime = (result.time || '').replace(/\|/g, '/').replace(/@/g, '(at)');

        replies.push(commentId + '@@' + username + '@@' + cleanText + '@@' + cleanTime);
    }

    if (replies.length > 0) {
        _threadsAutoReplyResult = 'COMMENTS|||' + replies.length + '|||' + replies.join('|||');
    } else {
        _threadsAutoReplyResult = 'NO_COMMENTS';
    }
})();
