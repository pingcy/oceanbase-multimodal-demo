#!/usr/bin/env python3
"""
更新 sofa_demo_v2 表中的 promotion_policy 字段为统一的JSON格式
"""

import os
import pymysql
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 统一的优惠政策数据设计
PROMOTION_POLICIES = {
    1: {  # 北欧简约三人布艺沙发
        "discount": 8.5,
        "target": "新客户",
        "comment": "新客户专享优惠，打造温馨北欧风格家居",
        "services": ["免费配送", "3年质保"],
        "gifts": [],
        "special_offers": []
    },
    2: {  # 现代简约真皮沙发
        "discount": 9.0,
        "target": "所有客户",
        "comment": "限时优惠，高端真皮材质",
        "services": ["免费保养2次"],
        "gifts": [],
        "special_offers": ["24期免息分期"]
    },
    3: {  # 美式复古布艺组合沙发
        "discount": 10.0,
        "target": "所有客户",
        "comment": "经典美式风格，组合购买更优惠",
        "services": ["5年质保"],
        "gifts": ["抱枕", "地毯"],
        "special_offers": ["旧沙发抵扣500元"]
    },
    4: {  # 中式红木沙发
        "discount": 9.5,
        "target": "VIP客户",
        "comment": "传统工艺，匠心制作",
        "services": ["免费定制服务", "免费上门收藏鉴定"],
        "gifts": [],
        "special_offers": []
    },
    5: {  # 小户型双人布艺沙发
        "discount": 7.5,
        "target": "学生",
        "comment": "学生专享超值优惠，小户型首选",
        "services": ["7天无理由退换"],
        "gifts": ["茶几"],
        "special_offers": []
    },
    6: {  # 欧式奢华真皮沙发
        "discount": 9.2,
        "target": "高端客户",
        "comment": "奢华品质，尊享服务",
        "services": ["白手套配送安装", "专属管家服务"],
        "gifts": [],
        "special_offers": []
    },
    7: {  # 日式简约单人沙发
        "discount": 9.0,
        "target": "极简主义者",
        "comment": "禅意生活，环保材质认证",
        "services": ["环保材质认证"],
        "gifts": [],
        "special_offers": ["极简生活倡导奖励"]
    },
    8: {  # 工业风铁艺布艺沙发
        "discount": 8.0,
        "target": "设计师",
        "comment": "工业风格，个性定制",
        "services": ["个性定制服务"],
        "gifts": ["工业风配件"],
        "special_offers": ["LOFT装修套餐优惠"]
    },
    9: {  # 现代科技智能沙发
        "discount": 9.0,
        "target": "科技爱好者",
        "comment": "智能科技，未来生活体验",
        "services": ["终身软件升级"],
        "gifts": [],
        "special_offers": ["智能家居套装优惠"]
    },
    10: {  # 田园风碎花布艺沙发
        "discount": 8.8,
        "target": "情侣/家庭",
        "comment": "温馨田园风，营造浪漫家居氛围",
        "services": [],
        "gifts": ["花卉主题配件"],
        "special_offers": ["家庭温馨大礼包"]
    }
}

def update_promotion_policies():
    """更新优惠政策数据"""
    
    # 数据库连接配置
    db_config = {
        'host': os.getenv('OB_URL'),
        'port': 3306,
        'user': os.getenv('OB_USER'),
        'password': os.getenv('OB_PWD'),
        'database': os.getenv('OB_DB_NAME'),
        'charset': 'utf8mb4'
    }
    
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        
        print("开始更新 promotion_policy 字段...")
        print("=" * 60)
        
        # 更新每个产品的优惠政策
        for product_id, policy_data in PROMOTION_POLICIES.items():
            # 将字典转换为JSON字符串
            policy_json = json.dumps(policy_data, ensure_ascii=False, indent=2)
            
            # 执行更新
            update_sql = """
                UPDATE sofa_demo_v2 
                SET promotion_policy = %s 
                WHERE id = %s
            """
            
            cursor.execute(update_sql, (policy_json, product_id))
            
            print(f"✓ 产品ID {product_id} 更新完成")
            print(f"  新的优惠政策: {policy_data}")
            print("-" * 40)
        
        # 提交事务
        connection.commit()
        print("\n🎉 所有优惠政策更新完成！")
        
        # 验证更新结果
        print("\n验证更新结果:")
        print("=" * 60)
        cursor.execute("SELECT id, name, promotion_policy FROM sofa_demo_v2 ORDER BY id")
        rows = cursor.fetchall()
        
        for row in rows:
            print(f"ID {row[0]} ({row[1]}):")
            try:
                policy_data = json.loads(row[2])
                print(f"  折扣: {policy_data.get('discount')}折")
                print(f"  目标群体: {policy_data.get('target')}")
                print(f"  说明: {policy_data.get('comment')}")
                if policy_data.get('services'):
                    print(f"  服务: {', '.join(policy_data.get('services'))}")
                if policy_data.get('gifts'):
                    print(f"  赠品: {', '.join(policy_data.get('gifts'))}")
                if policy_data.get('special_offers'):
                    print(f"  特殊优惠: {', '.join(policy_data.get('special_offers'))}")
            except Exception as e:
                print(f"  解析错误: {e}")
            print()
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        if 'connection' in locals():
            connection.rollback()
            cursor.close()
            connection.close()

if __name__ == "__main__":
    update_promotion_policies()
