/* 讀取 Threads 貼文內容 - 回傳格式：POST_CONTENT|||@username|||貼文內容 */
var _threadsPatrolResult = null;
(function() {
    var containers = document.querySelectorAll('[data-pressable-container="true"]');
    if (containers.length === 0) {
        _threadsPatrolResult = 'NO_CONTENT';
        return;
    }

    var opContainer = containers[0];

    var userLink = opContainer.querySelector('a[href^="/@"]');
    var username = 'unknown';
    if (userLink) {
        username = userLink.getAttribute('href').replace('/@', '').split('/')[0].split('?')[0];
    }

    var spans = opContainer.querySelectorAll('span[dir="auto"]');
    var textParts = [];
    spans.forEach(function(span) {
        var t = span.textContent.trim();
        if (t.length > 2 && t !== username
            && t.indexOf('翻譯') === -1 && t.indexOf('Translate') === -1
            && t !== '回覆' && t !== 'Reply' && t !== '讚' && t !== 'Like'
            && t.indexOf('查看') !== 0 && t.indexOf('View') !== 0
            && t.indexOf('為你推薦') !== 0
            && !t.match(/^\d+[小時天分鐘週秒]+前?$/)
            && !t.match(/^\d+ (hours?|days?|minutes?|weeks?|seconds?) ago$/)
            && !t.match(/^[\d,]+$/)
            && t !== '已編輯' && t !== 'Edited') {
            textParts.push(t);
        }
    });

    var seen = {};
    var uniqueParts = [];
    textParts.forEach(function(t) {
        if (!seen[t]) {
            seen[t] = true;
            uniqueParts.push(t);
        }
    });

    var postText = uniqueParts.join(' ').substring(0, 500);

    if (postText.length > 0) {
        _threadsPatrolResult = 'POST_CONTENT|||@' + username + '|||' + postText;
    } else {
        _threadsPatrolResult = 'NO_TEXT|||@' + username + '|||';
    }
})();
