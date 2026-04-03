var _threadsResult = null;
(function() {
    var OP_PARAM = '_OP_USERNAME_';
    var replies = [];
    var seen = {};
    var links = document.querySelectorAll('a[href^="/@"]');
    links.forEach(function(link) {
        var href = link.getAttribute('href');
        var username = href.replace('/@', '').split('/')[0].split('?')[0];
        if (username === OP_PARAM || username === '') return;
        var container = link.closest('[data-pressable-container="true"]');
        if (!container) return;
        var spans = container.querySelectorAll('span[dir="auto"]');
        var replyText = '';
        spans.forEach(function(span) {
            var t = span.textContent.trim();
            if (t.length > 3 && t !== username && t.indexOf('翻譯') === -1 && t !== '回覆' && t.indexOf('查看') !== 0 && !t.match(/^\d+[小時天分鐘週]+前?$/) && !t.match(/^[\d,]+$/) && t !== '讚') {
                if (t.length > replyText.length) replyText = t;
            }
        });
        var key = username + replyText.substring(0, 30);
        if (replyText.length > 3 && !seen[key]) {
            seen[key] = true;
            replies.push('@' + username + ': ' + replyText.replace(/\n/g, ' ').substring(0, 60));
        }
    });
    _threadsResult = replies.length + '|||' + replies.join('|||');
})();
