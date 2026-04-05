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

/* ACTION: focus_reply - 聚焦文章主體的回覆區 contenteditable（用於剪貼簿貼上前） */
/* 注意：選擇位置最上方（minY）的 contenteditable，那是文章主體的回覆輸入區 */
/* 而非最下方的（那通常是別人留言的回覆區） */
function _threadsFocusReplyEditable() {
    var editables = document.querySelectorAll('[contenteditable="true"]');
    var target = null;
    var minY = 999999;

    /* 選擇位置最上方的可見 contenteditable（文章主體的回覆區） */
    for (var i = 0; i < editables.length; i++) {
        var rect = editables[i].getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && rect.y < minY) {
            minY = rect.y;
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

/* ACTION: verify_reply - 驗證留言是否成功（基本檢查：錯誤彈窗 + 輸入區清空） */
/* 注意：只檢查 role="alert" 或小型錯誤提示元素，不掃描整頁 span 以免誤判 */
function _threadsVerifyReply() {
    /* 策略 1: 檢查 role="alert" 錯誤提示 */
    var alerts = document.querySelectorAll('[role="alert"], [role="alertdialog"]');
    for (var i = 0; i < alerts.length; i++) {
        var t = alerts[i].textContent.trim();
        if (t.length > 0 && t.length < 200) {
            _threadsPatrolResult = 'REPLY_ERROR:' + t.substring(0, 100);
            return;
        }
    }

    /* 策略 2: 檢查輸入區是否已清空（表示送出成功） */
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

/* ACTION: check_duplicate - 留言前檢查是否已有相同內容的留言 */
/* 用留言文字的前 10 個字搜尋頁面上所有回覆，如果找到就表示重複 */
function _threadsCheckDuplicate(searchText) {
    if (!searchText || searchText.length === 0) {
        _threadsPatrolResult = 'DUP_NO_TEXT';
        return;
    }

    var keyword = searchText.substring(0, 10).replace(/\s+/g, ' ').trim();
    if (keyword.length < 3) {
        _threadsPatrolResult = 'DUP_NOT_FOUND';
        return;
    }

    /* 搜尋所有 span[dir="auto"]，跳過第一個貼文容器（OP 內容） */
    var containers = document.querySelectorAll('[data-pressable-container="true"]');
    var opContainer = containers.length > 0 ? containers[0] : null;

    var spans = document.querySelectorAll('span[dir="auto"]');
    for (var i = 0; i < spans.length; i++) {
        /* 跳過 OP 貼文容器內的 span */
        if (opContainer && opContainer.contains(spans[i])) continue;

        var t = spans[i].textContent.trim();
        if (t.indexOf(keyword) >= 0) {
            _threadsPatrolResult = 'DUP_FOUND:' + t.substring(0, 50);
            return;
        }
    }

    _threadsPatrolResult = 'DUP_NOT_FOUND';
}

/* ACTION: verify_reply_content - 重新載入頁面後驗證留言文字是否真的出現 */
/* 參數 searchText 由 shell 動態注入 */
function _threadsVerifyReplyContent(searchText) {
    if (!searchText || searchText.length === 0) {
        _threadsPatrolResult = 'VERIFY_NO_SEARCH_TEXT';
        return;
    }

    /* 取前 15 個字作為搜尋關鍵字（避免換行或特殊字元干擾） */
    var keyword = searchText.substring(0, 15).replace(/\s+/g, ' ').trim();

    /* 搜尋所有 span[dir="auto"] 中是否包含我們的留言文字 */
    var spans = document.querySelectorAll('span[dir="auto"]');
    for (var i = 0; i < spans.length; i++) {
        var t = spans[i].textContent.trim();
        if (t.indexOf(keyword) >= 0) {
            _threadsPatrolResult = 'VERIFY_FOUND';
            return;
        }
    }

    /* 備用：搜尋所有可見文字節點 */
    var allText = document.body.innerText || '';
    if (allText.indexOf(keyword) >= 0) {
        _threadsPatrolResult = 'VERIFY_FOUND';
        return;
    }

    _threadsPatrolResult = 'VERIFY_NOT_FOUND';
}
