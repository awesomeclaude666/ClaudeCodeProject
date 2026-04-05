/* Threads 回覆頁面重複留言提取 - 由 threads_dup_checker.sh 注入 */
/* 重要：所有註解必須使用 block comment，因為 AppleScript 注入時會把換行變空格 */
/* 如果使用 // 單行註解，會把後面所有程式碼都註解掉 */
var _threadsDupResult = null;
(function() {
    var MY_USERNAME = 'jacksonwang88866';

    /* 將相對時間文字轉換為小時數，回傳 -1 表示無法辨識 */
    function parseTimestampToHours(text) {
        if (!text) return -1;
        text = text.trim();

        /* 中文：剛剛 / 現在 */
        if (text === '\u525b\u525b' || text === '\u73fe\u5728') return 0;
        /* 英文：Just now / now */
        if (text.toLowerCase() === 'just now' || text.toLowerCase() === 'now') return 0;

        /* 中文格式：數字+單位+可選的「前」 */
        var zhMatch = text.match(/^(\d+)\s*(\u79d2|\u5206\u9418|\u5c0f\u6642|\u5929|\u65e5|\u9031)\u524d?$/);
        if (zhMatch) {
            var num = parseInt(zhMatch[1]);
            var unit = zhMatch[2];
            if (unit === '\u79d2') return num / 3600;
            if (unit === '\u5206\u9418') return num / 60;
            if (unit === '\u5c0f\u6642') return num;
            if (unit === '\u5929' || unit === '\u65e5') return num * 24;
            if (unit === '\u9031') return num * 24 * 7;
        }

        /* 英文短格式：1s, 30m, 3h, 1d, 1w */
        var enShortMatch = text.match(/^(\d+)\s*(s|m|h|d|w)$/);
        if (enShortMatch) {
            var num2 = parseInt(enShortMatch[1]);
            var unit2 = enShortMatch[2];
            if (unit2 === 's') return num2 / 3600;
            if (unit2 === 'm') return num2 / 60;
            if (unit2 === 'h') return num2;
            if (unit2 === 'd') return num2 * 24;
            if (unit2 === 'w') return num2 * 24 * 7;
        }

        /* 英文長格式：3 hours ago, 1 day ago */
        var enLongMatch = text.match(/^(\d+)\s+(seconds?|minutes?|hours?|days?|weeks?)\s*ago$/i);
        if (enLongMatch) {
            var num3 = parseInt(enLongMatch[1]);
            var unit3 = enLongMatch[2].toLowerCase();
            if (unit3.indexOf('second') === 0) return num3 / 3600;
            if (unit3.indexOf('minute') === 0) return num3 / 60;
            if (unit3.indexOf('hour') === 0) return num3;
            if (unit3.indexOf('day') === 0) return num3 * 24;
            if (unit3.indexOf('week') === 0) return num3 * 24 * 7;
        }

        return -1;
    }

    /* 在容器內尋找時間戳 */
    function findTimestamp(container) {
        /* 策略 1: <time datetime="..."> 屬性（最精確） */
        var timeEl = container.querySelector('time[datetime]');
        if (timeEl) {
            var dt = new Date(timeEl.getAttribute('datetime'));
            if (!isNaN(dt.getTime())) {
                var hoursAgo = (Date.now() - dt.getTime()) / (1000 * 60 * 60);
                return { hours: hoursAgo, text: timeEl.textContent.trim() };
            }
        }

        /* 策略 2: <time> 元素文字 */
        var timeEls = container.querySelectorAll('time');
        for (var i = 0; i < timeEls.length; i++) {
            var t = timeEls[i].textContent.trim();
            var h = parseTimestampToHours(t);
            if (h >= 0) return { hours: h, text: t };
        }

        /* 策略 3: span 中的時間戳文字 */
        var spans = container.querySelectorAll('span');
        for (var j = 0; j < spans.length; j++) {
            var st = spans[j].textContent.trim();
            if (st.length < 15) {
                var sh = parseTimestampToHours(st);
                if (sh >= 0) return { hours: sh, text: st };
            }
        }

        return null;
    }

    /* 提取回覆文字（過濾 UI 雜訊） */
    function extractReplyText(container, username) {
        var spans = container.querySelectorAll('span[dir="auto"]');
        var textParts = [];
        for (var i = 0; i < spans.length; i++) {
            var t = spans[i].textContent.trim();
            if (t.length > 2 && t !== username
                && t.indexOf('\u7ffb\u8b6f') === -1 && t.indexOf('Translate') === -1
                && t !== '\u56de\u8986' && t !== 'Reply' && t !== '\u8b9a' && t !== 'Like'
                && t.indexOf('\u67e5\u770b') !== 0 && t.indexOf('View') !== 0
                && t.indexOf('\u70ba\u4f60\u63a8\u85a6') !== 0 && t.indexOf('Suggested') !== 0
                && t !== '\u5df2\u7de8\u8f2f' && t !== 'Edited'
                && t !== '\u5df2\u8a8d\u8b49' && t !== 'Verified'
                && parseTimestampToHours(t) < 0
                && !t.match(/^[\d,]+$/)
                && !t.match(/^\d+\u842c?$/)
                && t.indexOf('\u500b\u8b9a') === -1 && t.indexOf('likes') === -1
                && t.indexOf('\u5247\u56de\u8986') === -1 && t.indexOf('replies') === -1
                && t.indexOf('\u5247\u7559\u8a00') === -1
                && t !== '\u7559\u8a00' && t !== 'Comment') {
                textParts.push(t);
            }
        }
        /* 去重文字片段 */
        var seen = {};
        var unique = [];
        for (var j = 0; j < textParts.length; j++) {
            if (!seen[textParts[j]]) {
                seen[textParts[j]] = true;
                unique.push(textParts[j]);
            }
        }
        return unique.join(' ').substring(0, 300);
    }

    /* 主提取邏輯 */
    var containers = document.querySelectorAll('[data-pressable-container="true"]');
    if (containers.length === 0) {
        _threadsDupResult = 'DUP_NO_REPLIES';
        return;
    }

    var replies = [];
    var seenKeys = {};

    for (var ci = 0; ci < containers.length; ci++) {
        var container = containers[ci];

        /* 檢查是否為自己的回覆（用戶名連結匹配） */
        var userLink = container.querySelector('a[href^="/@"]');
        if (!userLink) continue;
        var username = userLink.getAttribute('href').replace('/@', '').split('/')[0].split('?')[0];
        if (username !== MY_USERNAME) continue;

        /* 解析時間戳 */
        var ts = findTimestamp(container);
        if (!ts) continue;
        if (ts.hours > 24) continue;

        /* 提取回覆文字 */
        var replyText = extractReplyText(container, username);
        if (replyText.length < 3) continue;

        /* 提取所回覆的貼文 URL */
        var postLink = container.querySelector('a[href*="/post/"]');
        var postUrl = '';
        if (postLink) {
            var href = postLink.getAttribute('href');
            postUrl = href.startsWith('http') ? href : 'https://www.threads.com' + href;
            postUrl = postUrl.split('?')[0];
        }

        /* 去重 key（避免同一回覆被 DOM 重複計算） */
        var key = replyText.substring(0, 50) + '|' + postUrl;
        if (seenKeys[key]) continue;
        seenKeys[key] = true;

        replies.push(replyText + '@@' + ts.text + '@@' + postUrl);
    }

    if (replies.length > 0) {
        _threadsDupResult = 'DUP_REPLIES|||' + replies.length + '|||' + replies.join('|||');
    } else {
        _threadsDupResult = 'DUP_NO_REPLIES';
    }
})();
