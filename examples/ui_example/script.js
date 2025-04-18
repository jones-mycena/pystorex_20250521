/**
 * 主要應用程式邏輯
 * 負責處理UI互動和呈現狀態
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM 已完全載入，初始化應用程式...");
    
    // 自動觸發控制變數
    let autoTriggerInterval = null;
    const timePoints = ['t0', 't1', 't2', 't3', 't4'];
    let currentTimeIndex = 0;
    
    // 初始化狀態機
    StateMachine.init();
    
    // 監聽狀態變更事件
    document.addEventListener('stateChange', function(event) {
        console.log("收到狀態變更事件:", event.detail);
        updateStateDisplay();
        updateStateHistory();
    });
    
    /**
     * 更新當前狀態顯示
     */
    function updateStateDisplay() {
        const currentStateEl = document.getElementById('current-state');
        if (!currentStateEl) {
            console.error("找不到狀態顯示元素");
            return;
        }
        
        const stateDisplay = StateMachine.getStateDisplay();
        
        // 設置狀態顯示
        currentStateEl.textContent = stateDisplay.text;
        currentStateEl.className = `p-3 rounded font-medium ${stateDisplay.class}`;
        
        console.log("狀態顯示已更新為:", stateDisplay.text);
    }
    
    /**
     * 更新狀態歷史顯示
     */
    function updateStateHistory() {
        const historyEl = document.getElementById('state-history');
        if (!historyEl) {
            console.error("找不到狀態歷史元素");
            return;
        }
        
        historyEl.innerHTML = '';
        
        StateMachine.getStateHistory().forEach((item, index) => {
            const stateClass = StateMachine.getStateColorClass(item.newState);
            const prevStateClass = StateMachine.getStateColorClass(item.prevState);
            
            const eventStr = JSON.stringify(item.event)
                .replace(/\[|\]|{|}|"/g, ' ')
                .replace(/,/g, ', ')
                .replace(/:/g, ': ');
            
            const itemEl = document.createElement('div');
            itemEl.className = `p-3 border-l-4 ${stateClass} bg-opacity-20`;
            itemEl.innerHTML = `
                <div class="flex justify-between">
                    <span class="font-semibold">${item.time} (${item.systemTime})</span>
                    <span class="text-sm">
                        <span class="${prevStateClass} px-2 py-1 rounded-l">${StateMachine.getStateName(item.prevState)}</span>
                        <span class="bg-gray-300 px-2 py-1">→</span>
                        <span class="${stateClass} px-2 py-1 rounded-r">${StateMachine.getStateName(item.newState)}</span>
                    </span>
                </div>
                <div class="mt-1 text-sm text-gray-600">事件數據: ${eventStr}</div>
            `;
            
            historyEl.appendChild(itemEl);
        });
        
        console.log("狀態歷史顯示已更新");
    }
    
    /**
     * 綁定事件觸發按鈕
     */
    function bindTriggerButtons() {
        console.log("正在綁定按鈕事件...");
        const buttons = document.querySelectorAll('.trigger-btn');
        console.log(`找到 ${buttons.length} 個按鈕`);
        
        buttons.forEach(btn => {
            // 移除舊的事件監聽器（避免重複綁定）
            btn.removeEventListener('click', handleButtonClick);
            // 添加新的事件監聽器
            btn.addEventListener('click', handleButtonClick);
            // 添加視覺反饋
            btn.classList.add('cursor-pointer');
            console.log(`按鈕 ${btn.getAttribute('data-time')} 已綁定事件`);
        });
    }
    
    /**
     * 按鈕點擊處理函數
     */
    function handleButtonClick(event) {
        console.log("按鈕被點擊!");
        const btn = event.currentTarget;
        const time = btn.getAttribute('data-time');
        const eventData = document.getElementById(`event-${time}`).value;
        console.log(`處理時間點 ${time} 的事件數據:`, eventData);
        
        // 添加視覺反饋
        btn.classList.add('bg-blue-700');
        setTimeout(() => {
            btn.classList.remove('bg-blue-700');
        }, 200);
        
        // 使用狀態機處理事件
        try {
            StateMachine.handleEvent(time, eventData);
        } catch (error) {
            console.error("處理事件時發生錯誤:", error);
            alert(`處理事件時發生錯誤: ${error.message}`);
        }
    }
    
    /**
     * 綁定自動觸發按鈕
     */
    function bindAutoTriggerButtons() {
        console.log("綁定自動觸發按鈕...");
        
        const autoTriggerBtn = document.getElementById('auto-trigger-btn');
        const stopTriggerBtn = document.getElementById('stop-trigger-btn');
        
        if (autoTriggerBtn) {
            autoTriggerBtn.removeEventListener('click', startAutoTrigger);
            autoTriggerBtn.addEventListener('click', startAutoTrigger);
            console.log("自動觸發按鈕已綁定");
        } else {
            console.error("找不到自動觸發按鈕!");
        }
        
        if (stopTriggerBtn) {
            stopTriggerBtn.removeEventListener('click', stopAutoTrigger);
            stopTriggerBtn.addEventListener('click', stopAutoTrigger);
            console.log("停止觸發按鈕已綁定");
        } else {
            console.error("找不到停止觸發按鈕!");
        }
    }
    
    /**
     * 開始自動觸發
     */
    function startAutoTrigger() {
        console.log("開始自動觸發序列");
        if (autoTriggerInterval) {
            console.log("已有觸發序列在運行，忽略");
            return;
        }
        
        const interval = parseInt(document.getElementById('interval-input').value) || 1000;
        currentTimeIndex = 0;
        
        // 切換按鈕顯示
        const autoTriggerBtn = document.getElementById('auto-trigger-btn');
        const stopTriggerBtn = document.getElementById('stop-trigger-btn');
        
        if (autoTriggerBtn) autoTriggerBtn.classList.add('hidden');
        if (stopTriggerBtn) stopTriggerBtn.classList.remove('hidden');
        
        // 立即觸發第一個時間點
        triggerCurrentTimePoint();
        
        // 設置自動觸發間隔
        console.log(`設置間隔為 ${interval} 毫秒的自動觸發`);
        autoTriggerInterval = setInterval(() => {
            currentTimeIndex++;
            if (currentTimeIndex >= timePoints.length) {
                console.log("已觸發所有時間點，停止序列");
                stopAutoTrigger();
                return;
            }
            console.log(`觸發時間點 ${timePoints[currentTimeIndex]}`);
            triggerCurrentTimePoint();
        }, interval);
    }
    
    /**
     * 觸發當前時間點
     */
    function triggerCurrentTimePoint() {
        const time = timePoints[currentTimeIndex];
        console.log(`正在觸發時間點 ${time}`);
        
        // 獲取事件數據
        const eventInput = document.getElementById(`event-${time}`);
        if (!eventInput) {
            console.error(`找不到時間點 ${time} 的事件輸入框`);
            return;
        }
        
        const eventData = eventInput.value;
        console.log(`時間點 ${time} 的事件數據:`, eventData);
        
        // 高亮當前按鈕
        document.querySelectorAll('.trigger-btn').forEach(btn => {
            btn.classList.remove('ring', 'ring-blue-300');
            if (btn.getAttribute('data-time') === time) {
                btn.classList.add('ring', 'ring-blue-300', 'bg-blue-600');
                // 添加短暫的視覺反饋
                setTimeout(() => {
                    btn.classList.remove('bg-blue-600');
                }, 200);
            }
        });
        
        // 使用狀態機處理事件
        try {
            const result = StateMachine.handleEvent(time, eventData);
            console.log(`時間點 ${time} 事件處理結果:`, result ? "成功" : "失敗");
        } catch (error) {
            console.error(`觸發時間點 ${time} 時發生錯誤:`, error);
        }
    }
    
    /**
     * 停止自動觸發
     */
    function stopAutoTrigger() {
        console.log("停止自動觸發序列");
        
        if (autoTriggerInterval) {
            clearInterval(autoTriggerInterval);
            autoTriggerInterval = null;
            console.log("已清除自動觸發間隔");
        }
        
        // 重置按鈕樣式
        document.querySelectorAll('.trigger-btn').forEach(btn => {
            btn.classList.remove('ring', 'ring-blue-300', 'bg-blue-600');
        });
        
        // 切換按鈕顯示
        const autoTriggerBtn = document.getElementById('auto-trigger-btn');
        const stopTriggerBtn = document.getElementById('stop-trigger-btn');
        
        if (autoTriggerBtn) {
            autoTriggerBtn.classList.remove('hidden');
            console.log("顯示自動觸發按鈕");
        }
        
        if (stopTriggerBtn) {
            stopTriggerBtn.classList.add('hidden');
            console.log("隱藏停止觸發按鈕");
        }
    }
    
    /**
     * 初始化所有功能
     */
    function initializeAll() {
        console.log("初始化所有功能...");
        
        // 初始化狀態顯示
        updateStateDisplay();
        
        // 確保當前狀態正確顯示
        const currentStateEl = document.getElementById('current-state');
        if (currentStateEl) {
            if (currentStateEl.textContent === '初始化中...') {
                // 設置初始狀態為「無人」
                const stateDisplay = StateMachine.getStateDisplay();
                currentStateEl.textContent = stateDisplay.text;
                currentStateEl.className = `p-3 rounded font-medium ${stateDisplay.class}`;
            }
            console.log("當前狀態已初始化為:", currentStateEl.textContent);
        } else {
            console.error("找不到當前狀態元素!");
        }
        
        // 確保所有按鈕正確綁定
        bindTriggerButtons();
        bindAutoTriggerButtons();
        
        console.log("所有功能初始化完成!");
    }
    
    // 立即初始化所有功能
    initializeAll();
});