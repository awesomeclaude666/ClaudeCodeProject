/* 從用戶個人頁面提取貼文 URL - 回傳格式：數量|||url1|||url2|||... */
var _threadsPatrolResult = null;
(function() {
    var links = document.querySelectorAll('a[href*="/post/"]');
    var urls = [];
    var seen = {};

    links.forEach(function(link) {
        var href = link.getAttribute('href');
        if (!href) return;

        var fullUrl = href.startsWith('http') ? href : 'https://www.threads.com' + href;
        fullUrl = fullUrl.split('?')[0];

        if (!seen[fullUrl]) {
            seen[fullUrl] = true;
            urls.push(fullUrl);
        }
    });

    if (urls.length > 0) {
        _threadsPatrolResult = urls.length + '|||' + urls.join('|||');
    } else {
        _threadsPatrolResult = '0';
    }
})();
