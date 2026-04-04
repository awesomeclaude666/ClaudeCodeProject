/* Threads 首頁 Feed 貼文提取 - 由 threads_feed_patrol.sh 注入 */
/* 重要：所有註解必須使用 block comment，因為 AppleScript 注入時會把換行變空格 */
/* 如果使用 // 單行註解，會把後面所有程式碼都註解掉 */
var _threadsFeedResult = null;
(function() {
    var containers = document.querySelectorAll('[data-pressable-container="true"]');
    if (containers.length === 0) {
        _threadsFeedResult = 'FEED_EMPTY';
        return;
    }

    var posts = [];
    var seenUrls = {};

    for (var ci = 0; ci < containers.length && posts.length < 10; ci++) {
        var container = containers[ci];

        /* 提取用戶名 */
        var userLink = container.querySelector('a[href^="/@"]');
        var username = '';
        if (userLink) {
            username = userLink.getAttribute('href').replace('/@', '').split('/')[0].split('?')[0];
        }
        if (!username) continue;

        /* 跳過自己的貼文 */
        if (username === 'jacksonwang88866') continue;

        /* 提取貼文 URL */
        var postLink = container.querySelector('a[href*="/post/"]');
        var postUrl = '';
        if (postLink) {
            var href = postLink.getAttribute('href');
            postUrl = href.startsWith('http') ? href : 'https://www.threads.com' + href;
            postUrl = postUrl.split('?')[0];
        }
        if (!postUrl) continue;

        /* 去重 */
        if (seenUrls[postUrl]) continue;
        seenUrls[postUrl] = true;

        /* 提取貼文內容 */
        var spans = container.querySelectorAll('span[dir="auto"]');
        var textParts = [];
        for (var si = 0; si < spans.length; si++) {
            var t = spans[si].textContent.trim();
            if (t.length > 2 && t !== username
                && t.indexOf('翻譯') === -1 && t.indexOf('Translate') === -1
                && t !== '回覆' && t !== 'Reply' && t !== '讚' && t !== 'Like'
                && t.indexOf('查看') !== 0 && t.indexOf('View') !== 0
                && t.indexOf('為你推薦') !== 0 && t.indexOf('Suggested') !== 0
                && t !== '已編輯' && t !== 'Edited'
                && t !== '已認證' && t !== 'Verified'
                && !t.match(/^\d+[小時天分鐘週秒]+前?$/)
                && !t.match(/^\d+ (hours?|days?|minutes?|weeks?|seconds?) ago$/)
                && !t.match(/^[\d,]+$/)
                && !t.match(/^\d+萬?$/)
                && t.indexOf('個讚') === -1 && t.indexOf('likes') === -1
                && t.indexOf('則回覆') === -1 && t.indexOf('replies') === -1
                && t.indexOf('則留言') === -1) {
                textParts.push(t);
            }
        }

        /* 去重文字片段 */
        var seen = {};
        var uniqueParts = [];
        for (var ti = 0; ti < textParts.length; ti++) {
            if (!seen[textParts[ti]]) {
                seen[textParts[ti]] = true;
                uniqueParts.push(textParts[ti]);
            }
        }

        var postText = uniqueParts.join(' ').substring(0, 300);
        if (postText.length < 3) continue;

        posts.push('@' + username + '@@' + postText + '@@' + postUrl);
    }

    if (posts.length > 0) {
        _threadsFeedResult = 'FEED_POSTS|||' + posts.length + '|||' + posts.join('|||');
    } else {
        _threadsFeedResult = 'FEED_EMPTY';
    }
})();
