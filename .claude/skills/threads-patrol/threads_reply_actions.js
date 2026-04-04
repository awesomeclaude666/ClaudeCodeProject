/* Threads 留言 DOM 操作 - 由 threads_patrol.sh 分步注入 */
/* 重要：所有註解必須使用 block comment，因為 AppleScript 注入時會把換行變空格 */
/* 如果使用 // 單行註解，會把後面所有程式碼都註解掉 */
var _threadsPatrolResult = null;

/* ACTION: click_reply - 找到並點擊回覆區域 */
function _threadsClickReply() {
    /* 策略 1: 找 contenteditable */
    var editables = document.querySelectorAll('[contenteditable="true"]');
    for (var i = 0; i < editables.length; i++) {
        var rect = editables[i].getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            editables[i].click();
            editables[i].focus();
            _threadsPatrolResult = 'REPLY_AREA_CLICKED';
            return;
        }
    }

    /* 策略 2: 找 data-placeholder 元素 */
    var placeholders = document.querySelectorAll('[data-placeholder]');
    for (var j = 0; j < placeholders.length; j++) {
        var rect2 = placeholders[j].getBoundingClientRect();
        if (rect2.width > 0 && rect2.height > 0) {
            placeholders[j].click();
            placeholders[j].focus();
            _threadsPatrolResult = 'REPLY_AREA_CLICKED';
            return;
        }
    }

    /* 策略 3: 找 role="textbox" */
    var textbox = document.querySelector('[role="textbox"]');
    if (textbox) {
        var rect3 = textbox.getBoundingClientRect();
        if (rect3.width > 0 && rect3.height > 0) {
            textbox.click();
            textbox.focus();
            _threadsPatrolResult = 'REPLY_AREA_CLICKED';
            return;
        }
    }

    /* 策略 4: 找回覆按鈕展開回覆區 */
    var buttons = document.querySelectorAll('div[role="button"], span');
    for (var k = 0; k < buttons.length; k++) {
        var text = buttons[k].textContent.trim();
        if (text === '回覆' || text === 'Reply' || text === '留言' || text === 'Comment') {
            var rect4 = buttons[k].getBoundingClientRect();
            if (rect4.width > 0 && rect4.height > 0 && rect4.width < 200) {
                buttons[k].click();
                _threadsPatrolResult = 'REPLY_BUTTON_CLICKED';
                return;
            }
        }
    }

    _threadsPatrolResult = 'REPLY_NOT_FOUND';
}

/* ACTION: check_reply_ready - 確認回覆區域已就緒 */
function _threadsCheckReplyReady() {
    var editables = document.querySelectorAll('[contenteditable="true"]');
    for (var i = 0; i < editables.length; i++) {
        var rect = editables[i].getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            _threadsPatrolResult = 'REPLY_READY';
            return;
        }
    }
    var textbox = document.querySelector('[role="textbox"]');
    if (textbox) {
        var rect2 = textbox.getBoundingClientRect();
        if (rect2.width > 0 && rect2.height > 0) {
            _threadsPatrolResult = 'REPLY_READY';
            return;
        }
    }
    _threadsPatrolResult = 'REPLY_NOT_READY';
}

/* ACTION: focus_reply - 聚焦回覆區域的 contenteditable（用於剪貼簿貼上前） */
/* 注意：不再使用 execCommand('insertText')，因為它不會觸發 React 狀態更新 */
/* 改用此函式聚焦後，由 shell 腳本透過 pbcopy + Cmd+V 貼上文字 */
function _threadsFocusReplyEditable() {
    var editables = document.querySelectorAll('[contenteditable="true"]');
    var target = null;
    var maxY = -1;

    /* 選擇位置最低的可見 contenteditable（通常是回覆輸入區） */
    for (var i = 0; i < editables.length; i++) {
        var rect = editables[i].getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && rect.y > maxY) {
            maxY = rect.y;
            target = editables[i];
        }
    }

    if (!target) {
        target = document.querySelector('[role="textbox"]');
    }

    if (target) {
        target.focus();
        target.click();
        /* 將游標放在開頭 */
        var sel = window.getSelection();
        var range = document.createRange();
        range.setStart(target, 0);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
        _threadsPatrolResult = 'REPLY_EDITABLE_FOCUSED';
    } else {
        _threadsPatrolResult = 'REPLY_EDITABLE_NOT_FOUND';
    }
}

/* ACTION: submit_reply - 點擊送出按鈕（選擇已啟用的按鈕） */
function _threadsSubmitReply() {
    var buttons = document.querySelectorAll('div[role="button"]');
    var candidates = [];

    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].textContent.trim();
        if (text === '發佈' || text === 'Post' || text === '張貼') {
            var rect = buttons[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && rect.width < 200) {
                var style = window.getComputedStyle(buttons[i]);
                var opacity = parseFloat(style.opacity);
                var cursor = style.cursor;
                candidates.push({
                    el: buttons[i],
                    y: rect.y,
                    opacity: opacity,
                    enabled: opacity > 0.5 && cursor !== 'not-allowed'
                });
            }
        }
    }

    /* 優先點擊已啟用的按鈕，多個時選 y 座標最大的 */
    var enabledOnes = candidates.filter(function(c) { return c.enabled; });
    if (enabledOnes.length > 0) {
        enabledOnes.sort(function(a, b) { return b.y - a.y; });
        enabledOnes[0].el.click();
        _threadsPatrolResult = 'REPLY_SUBMITTED';
        return;
    }

    /* aria-label 備用方案 */
    var ariaBtn = document.querySelector('[aria-label="Post"]')
        || document.querySelector('[aria-label="發佈"]')
        || document.querySelector('[aria-label="張貼"]')
        || document.querySelector('[aria-label="Reply"]')
        || document.querySelector('[aria-label="回覆"]');
    if (ariaBtn) {
        ariaBtn.click();
        _threadsPatrolResult = 'REPLY_SUBMITTED';
        return;
    }

    /* 沒有啟用的按鈕 */
    if (candidates.length > 0) {
        _threadsPatrolResult = 'REPLY_SUBMIT_DISABLED';
        return;
    }

    _threadsPatrolResult = 'REPLY_SUBMIT_NOT_FOUND';
}

/* ACTION: verify_reply - 驗證留言是否成功 */
function _threadsVerifyReply() {
    var spans = document.querySelectorAll('span[dir="auto"]');
    for (var i = 0; i < spans.length; i++) {
        var t = spans[i].textContent.trim();
        if (t.indexOf('錯誤') >= 0 || t.indexOf('error') >= 0
            || t.indexOf('Error') >= 0 || t.indexOf('失敗') >= 0
            || t.indexOf('無法') >= 0) {
            _threadsPatrolResult = 'REPLY_ERROR:' + t.substring(0, 100);
            return;
        }
    }

    var editables = document.querySelectorAll('[contenteditable="true"]');
    for (var j = 0; j < editables.length; j++) {
        var rect = editables[j].getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            var content = editables[j].textContent.trim();
            if (content.length === 0) {
                _threadsPatrolResult = 'REPLY_SUCCESS';
                return;
            }
        }
    }

    _threadsPatrolResult = 'REPLY_SUCCESS';
}
