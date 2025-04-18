/**
 * 安全帽檢測狀態機
 * 負責處理狀態邏輯和狀態轉換
 */
const StateMachine = {
    currentState: 'NO_PERSON',
    stateHistory: [],
    
    /**
     * 初始化狀態機
     * @returns {void}
     */
    init: function() {
        console.log("初始化狀態機...");
        this.currentState = 'NO_PERSON';
        this.stateHistory = [];
        console.log("狀態機初始化完成，當前狀態:", this.currentState);
    },
    
    /**
     * 處理事件並更新狀態
     * @param {string} time - 時間點標識符 (t0, t1, ...)
     * @param {string|object} eventData - 事件數據，可以是JSON字串或已解析的對象
     * @returns {boolean} 處理是否成功
     */
    handleEvent: function(time, eventData) {
        console.log(`處理時間點 ${time} 的事件`);
        try {
            // 確保 eventData 是非空的
            if (!eventData || (typeof eventData === 'string' && eventData.trim() === '')) {
                console.error("事件數據為空");
                alert("事件數據為空，請輸入有效的JSON數據");
                return false;
            }
            
            // 解析JSON數據
            let parsedData;
            try {
                parsedData = typeof eventData === 'string' ? JSON.parse(eventData) : eventData;
                console.log("成功解析JSON數據:", parsedData);
            } catch (jsonError) {
                console.error("JSON解析錯誤:", jsonError);
                alert(`JSON解析錯誤: ${jsonError.message}`);
                return false;
            }
            
            // 分析事件數據，確定新狀態
            const newState = this.determineState(parsedData);
            console.log(`狀態變化: ${this.currentState} -> ${newState}`);
            
            // 更新狀態歷史
            const timestamp = new Date().toLocaleTimeString();
            this.stateHistory.unshift({
                time: time,
                systemTime: timestamp,
                prevState: this.currentState,
                newState: newState,
                event: parsedData
            });
            
            // 更新當前狀態
            this.currentState = newState;
            
            // 觸發狀態變更事件
            this.notifyStateChange();
            
            console.log(`成功處理時間點 ${time} 的事件`);
            return true;
        } catch (error) {
            console.error('處理事件時出錯:', error);
            alert(`處理事件時出錯: ${error.message}`);
            return false;
        }
    },
    
    /**
     * 根據檢測結果確定新狀態
     * @param {Array} detectionData - 檢測結果數據
     * @returns {string} 新狀態
     */
    determineState: function(detectionData) {
        // 檢測是否有人
        const hasPerson = detectionData.some(item => item.class === 'person');
        console.log("檢測到人物:", hasPerson);
        
        // 檢測是否有安全帽
        const hasHelmet = detectionData.some(item => item.class === 'helmet');
        console.log("檢測到安全帽:", hasHelmet);
        
        // 確定新狀態
        if (!hasPerson) {
            return 'NO_PERSON';
        } else if (hasPerson && hasHelmet) {
            return 'SAFE'; // 有人有安全帽，安全狀態
        } else {
            return 'VIOLATION'; // 有人無安全帽，違規狀態
        }
    },
    
    /**
     * 通知狀態變更
     * 當狀態變更時會觸發此方法，可用於通知UI更新
     */
    notifyStateChange: function() {
        // 觸發自定義事件，以便UI可以響應狀態變更
        const event = new CustomEvent('stateChange', {
            detail: {
                currentState: this.currentState,
                stateHistory: this.stateHistory
            }
        });
        document.dispatchEvent(event);
    },
    
    /**
     * 獲取當前狀態
     * @returns {string} 當前狀態
     */
    getCurrentState: function() {
        return this.currentState;
    },
    
    /**
     * 獲取狀態歷史
     * @returns {Array} 狀態歷史記錄
     */
    getStateHistory: function() {
        return this.stateHistory;
    },
    
    /**
     * 獲取當前狀態的顯示文本
     * @returns {Object} 包含狀態文本和CSS類別的對象
     */
    getStateDisplay: function() {
        let stateText, stateClass;
        
        switch (this.currentState) {
            case 'NO_PERSON':
                stateText = '無人';
                stateClass = 'bg-gray-200';
                break;
            case 'SAFE':
                stateText = '安全 (有人且正確佩戴安全帽)';
                stateClass = 'bg-green-200 text-green-800';
                break;
            case 'VIOLATION':
                stateText = '違規 (有人但未佩戴安全帽)';
                stateClass = 'bg-red-200 text-red-800';
                break;
            default:
                stateText = '未知狀態';
                stateClass = 'bg-yellow-200';
        }
        
        return {
            text: stateText,
            class: stateClass
        };
    },
    
    /**
     * 獲取狀態的顯示名稱
     * @param {string} state - 狀態標識符
     * @returns {string} 狀態的顯示名稱
     */
    getStateName: function(state) {
        switch (state) {
            case 'NO_PERSON': return '無人';
            case 'SAFE': return '安全';
            case 'VIOLATION': return '違規';
            default: return '未知';
        }
    },
    
    /**
     * 獲取狀態的顏色類別
     * @param {string} state - 狀態標識符
     * @returns {string} 狀態對應的CSS類別
     */
    getStateColorClass: function(state) {
        switch (state) {
            case 'NO_PERSON': return 'border-gray-400 bg-gray-100 text-gray-800';
            case 'SAFE': return 'border-green-400 bg-green-100 text-green-800';
            case 'VIOLATION': return 'border-red-400 bg-red-100 text-red-800';
            default: return 'border-yellow-400 bg-yellow-100 text-yellow-800';
        }
    }
};
