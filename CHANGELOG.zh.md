# 更新日誌  

所有專案的顯著變更都會記錄在此文件中。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
並且本專案遵循 [語意化版本](https://semver.org/lang/zh-TW/)。

## [0.2.0] - 2025-05-15  

### 核心功能
- 推出穩定版本的 Pydantic 至 immutables.Map 的整合機制
- 完整實現 Action 池化機制，提高頻繁使用相同 Action 的效能
- 實現不可變狀態容器基礎設施，自動將可變資料轉換為不可變形式
- 完整支援 ReactiveX (RxPy) 響應式資料流

### 新增功能
- 新增 `to_immutable`、`to_dict` 和 `to_pydantic` 工具函數，方便在 Pydantic 模型與 immutables.Map 之間轉換
- 新增 `update_in` 和 `batch_update` 工具函數，用於高效率的深層更新和批量更新
- 新增豐富的中介軟體集合：
  - `LoggerMiddleware`：記錄狀態變化
  - `ThunkMiddleware`：支援 dispatch 函數
  - `AwaitableMiddleware`：支援 dispatch 協程
  - `ErrorMiddleware`：統一錯誤處理
  - `ImmutableEnforceMiddleware`：強制不可變性
  - `PersistMiddleware`：狀態持久化
  - `DevToolsMiddleware`：開發者工具支援
  - `PerformanceMonitorMiddleware`：效能監控
  - `DebounceMiddleware`：防抖處理
  - `BatchMiddleware`：批量處理
  - `AnalyticsMiddleware`：使用者行為分析

### 改進
- 使用 `immutables.Map` 實現全面不可變的 Action 物件
- Action 物件池化機制顯著減少記憶體使用和創建開銷
- 改進 Effect 註冊和管理機制，支援模組級別的生命週期管理
- 優化選擇器的記憶功能，支援深度比較和 TTL 快取策略
- 改進錯誤處理系統，提供結構化的錯誤報告

### 架構設計
- 嚴格遵循 NgRx/Redux 架構模式，統一狀態管理流程
- 模組化設計
- 完整的中介軟體架構，支援可擴展的工作流程
- `.pyi` 存根檔案提供高精度類型提示

### 開發者體驗
- 提供多種開箱即用的中介軟體，減少重複開發
- 詳細的中文文檔和註解，方便中文社群使用
- 完整的範例專案，包括計數器和偵測示範
- 更簡潔的 API 設計，減少樣板程式碼
### 修復
- 修復特定情境下的不可變性保證問題

### 棄用
- 移除 `*.ipy` 檔案，這些檔案不再需要， `.py` 檔案已經提供 Type Hint與詳細註釋

## [0.1.8] - 2025-04-19  
  
### 新增功能  
- 新增 `StoreModule` 類別，提供靜態方法用於動態註冊/註銷特性模組  
  
### 改進  
- 改進 Action 創建器的類型註解，支援更完善的系統  
- 改進 Effect 註冊機制，提供更好的錯誤處理和日誌記錄  
- 優化中介軟體管道處理流程，提高效能  
- 改進文檔和範例，增加中文說明  
  
### 修復  
- 修復中介軟體在處理特定 action 時的錯誤  
- 修復 Effect 註冊過程中的潛在記憶體洩漏問題  
  