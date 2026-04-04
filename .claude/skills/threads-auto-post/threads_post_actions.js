/* Threads 發文 DOM 操作 - 由 threads_auto_post.sh 分步注入 */
/* 重要：所有註解必須使用 block comment，因為 AppleScript 注入時會把換行變空格 */
/* 如果使用 // 單行註解，會把後面所有程式碼都註解掉 */
var _threadsPostResult = null;

/* ACTION: compose - 點擊撰寫區域 */
function _threadsClickCompose() {
    /* 策略 1: 首頁的內嵌撰寫區域 */
    var composeField = document.querySelector('div[role="button"][aria-label*="text field"]')
        || document.querySelector('div[role="button"][aria-label*="compose"]')
        || document.querySelector('div[role="button"][aria-label*="撰寫"]')
        || document.querySelector('div[role="button"][aria-label*="新貼文"]');
    if (composeField) {
        composeField.click();
        _threadsPostResult = 'COMPOSE_CLICKED';
        return;
    }

    /* 策略 2: 導航列的 Create SVG 按鈕 */
    var createSvg = document.querySelector('svg[aria-label="Create"]')
        || document.querySelector('svg[aria-label="建立"]')
        || document.querySelector('svg[aria-label="新串文"]');
    if (createSvg) {
        var parent = createSvg.parentElement;
        for (var i = 0; i < 5 && parent; i++) {
            if (parent.getAttribute('role') === 'button' || parent.tagName === 'A') {
                parent.click();
                _threadsPostResult = 'COMPOSE_CLICKED';
                return;
            }
            parent = parent.parentElement;
        }
        createSvg.parentElement.click();
        _threadsPostResult = 'COMPOSE_CLICKED';
        return;
    }

    /* 策略 3: aria-label 模糊搜尋 */
    var allBtns = document.querySelectorAll('div[role="button"], a[role="link"]');
    for (var j = 0; j < allBtns.length; j++) {
        var ariaLabel = (allBtns[j].getAttribute('aria-label') || '').toLowerCase();
        if (ariaLabel.indexOf('create') >= 0 || ariaLabel.indexOf('compose') >= 0
            || ariaLabel.indexOf('new thread') >= 0 || ariaLabel.indexOf('new post') >= 0
            || ariaLabel.indexOf('建立') >= 0 || ariaLabel.indexOf('新串文') >= 0
            || ariaLabel.indexOf('撰寫') >= 0) {
            allBtns[j].click();
            _threadsPostResult = 'COMPOSE_CLICKED';
            return;
        }
    }

    _threadsPostResult = 'COMPOSE_NOT_FOUND';
}

/* ACTION: check_modal - 檢查撰寫區域是否開啟 */
function _threadsCheckModal() {
    var editables = document.querySelectorAll('[contenteditable="true"]');
    for (var i = 0; i < editables.length; i++) {
        var rect = editables[i].getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            _threadsPostResult = 'MODAL_READY';
            return;
        }
    }
    var textbox = document.querySelector('[role="textbox"]');
    if (textbox) {
        var rect2 = textbox.getBoundingClientRect();
        if (rect2.width > 0 && rect2.height > 0) {
            _threadsPostResult = 'MODAL_READY';
            return;
        }
    }
    _threadsPostResult = 'MODAL_NOT_READY';
}

/* ACTION: focus - 聚焦 contenteditable 元素（用於剪貼簿貼上前） */
/* 注意：不再使用 execCommand('insertText')，因為它不會觸發 React 狀態更新 */
/* 改用此函式聚焦後，由 shell 腳本透過 pbcopy + Cmd+V 貼上文字 */
function _threadsFocusEditable() {
    var target = document.querySelector('[role="textbox"][contenteditable="true"]');

    if (!target) {
        var editables = document.querySelectorAll('[contenteditable="true"]');
        for (var i = 0; i < editables.length; i++) {
            var rect = editables[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                target = editables[i];
                break;
            }
        }
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
        _threadsPostResult = 'EDITABLE_FOCUSED';
    } else {
        _threadsPostResult = 'EDITABLE_NOT_FOUND';
    }
}

/* ACTION: post - 點擊發佈按鈕（選擇已啟用且位置最低的按鈕） */
function _threadsClickPost() {
    var buttons = document.querySelectorAll('div[role="button"]');
    var candidates = [];

    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].textContent.trim();
        if (text === 'Post' || text === '發佈' || text === '張貼') {
            var rect = buttons[i].getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0 && rect.width < 200 && rect.height < 80) {
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

    /* 優先點擊已啟用的按鈕，多個時選 y 座標最大的（通常是 modal 內的） */
    var enabledOnes = candidates.filter(function(c) { return c.enabled; });
    if (enabledOnes.length > 0) {
        enabledOnes.sort(function(a, b) { return b.y - a.y; });
        enabledOnes[0].el.click();
        _threadsPostResult = 'POST_CLICKED';
        return;
    }

    /* 沒有啟用的按鈕 */
    if (candidates.length > 0) {
        _threadsPostResult = 'POST_BUTTON_DISABLED';
        return;
    }

    _threadsPostResult = 'POST_BUTTON_NOT_FOUND';
}

/* ACTION: verify - 驗證發佈是否成功 */
function _threadsVerifyPost() {
    /* 檢查錯誤訊息 */
    var spans = document.querySelectorAll('span[dir="auto"]');
    for (var i = 0; i < spans.length; i++) {
        var t = spans[i].textContent.trim();
        if (t.indexOf('錯誤') >= 0 || t.indexOf('error') >= 0
            || t.indexOf('Error') >= 0 || t.indexOf('失敗') >= 0
            || t.indexOf('無法') >= 0 || t.indexOf('failed') >= 0) {
            _threadsPostResult = 'ERROR:' + t.substring(0, 100);
            return;
        }
    }

    /* modal 關閉 = 成功 */
    var editables = document.querySelectorAll('[contenteditable="true"]');
    var visibleCount = 0;
    for (var j = 0; j < editables.length; j++) {
        var rect = editables[j].getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) visibleCount++;
    }

    if (visibleCount === 0) {
        _threadsPostResult = 'POST_SUCCESS';
    } else {
        _threadsPostResult = 'POST_PENDING';
    }
}
