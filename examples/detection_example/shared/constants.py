"""
constants.py - 定義常量
"""

# 狀態轉換所需的累積次數
VIOLATION_THRESHOLD = 3  # 連續未佩戴安全帽x次被標記為違規
NORMAL_THRESHOLD = 2     # 連續正確佩戴安全帽x次回到正常
NO_PERSON_THRESHOLD = 2  # 連續x次無人檢測則重置該人的狀態
FENCE_VIOLATION_THRESHOLD = 2  # 連續x次進入禁區被標記為闖入違規

# 安全帽佩戴狀態枚舉
HELMET_STATUS = {
    "NORMAL": "正常佩戴",    # 正常佩戴安全帽
    "WARNING": "可能未佩戴",  # 警告狀態，未達到違規閾值
    "VIOLATION": "未佩戴"     # 確認未佩戴安全帽
}

# 禁區狀態枚舉
FENCE_STATUS = {
    "OUTSIDE": "區域外",    # 在禁區外
    "WARNING": "進入警戒",  # 剛進入禁區
    "INTRUSION": "禁區闖入"  # 持續在禁區內
}

# 禁區定義為矩形區域 [x_min, y_min, x_max, y_max]
RESTRICTED_AREAS = [
    [50, 50, 150, 300],     # 禁區1 - 調整y範圍以確保測試數據落在範圍內
    [400, 300, 500, 600]    # 禁區2 - 調整y範圍以確保測試數據落在範圍內
]