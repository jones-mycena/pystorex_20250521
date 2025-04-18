"""
utils.py - 定義輔助函數
"""

from typing import Tuple

def generate_person_id(bbox) -> str:
    """
    根據人員邊界框生成唯一ID (簡化版，實際應用中應使用更複雜的識別算法)
    
    Args:
        bbox: 人員邊界框 [x, y, width, height, confidence]
    
    Returns:
        人員ID字符串
    """
    # 簡化實現：使用位置作為ID的一部分
    # 實際應用中應使用更穩健的特徵或跟蹤算法
    return f"person_{int(bbox[0])}_{int(bbox[1])}"

def create_sample_data():
    """創建10個模擬場景數據，包含所有重要情境"""
    
    # 一些固定的人員和安全帽位置
    person1 = [100, 200, 80, 200, 0.95]  # [x, y, width, height, confidence]
    person2 = [300, 220, 85, 210, 0.92]
    helmet1 = [110, 170, 70, 50, 0.88]    # 正確位置，與person1頭部重疊
    helmet2 = [320, 190, 75, 55, 0.85]    # 正確位置，與person2頭部重疊
    
    # 進入禁區的人員
    person1_restricted = [100, 100, 80, 150, 0.95]  # 在禁區1內，底部中心點(140, 250)
    person2_restricted = [450, 350, 85, 150, 0.92]  # 在禁區2內，底部中心點(492.5, 500)
    
    samples = [
        # 1. 一開始畫面沒人
        {
            "persons": [],
            "helmets": []
        },
        
        # 2. 出現兩人，都沒有戴安全帽
        {
            "persons": [person1, person2],
            "helmets": []
        },
        
        # 3. 這兩人繼續沒戴安全帽，第一人進入禁區
        {
            "persons": [person1_restricted, person2],
            "helmets": []
        },
        
        # 4. 第一人在禁區內戴好安全帽，第二人還是沒戴
        {
            "persons": [person1_restricted, person2],
            "helmets": [helmet1]
        },
        
        # 5. 第二人也進入另一個禁區，但仍未戴安全帽
        {
            "persons": [person1_restricted, person2_restricted],
            "helmets": [helmet1]
        },
        
        # 6. 第二人在禁區中也戴好安全帽
        {
            "persons": [person1_restricted, person2_restricted],
            "helmets": [helmet1, helmet2]
        },
        
        # 7. 第一人消失（離開畫面）
        {
            "persons": [person2_restricted],
            "helmets": [helmet2]
        },
        
        # 8. 第二人離開禁區，但仍戴著安全帽
        {
            "persons": [person2],
            "helmets": [helmet2]
        },
        
        # 9. 第二人也消失（離開畫面）
        {
            "persons": [],
            "helmets": []
        },
        
        # 10. 畫面持續無人
        {
            "persons": [],
            "helmets": []
        }
    ]
    
    return samples