#!/usr/bin/env python3
"""
OceanBase 数据库初始化脚本
用于创建沙发推荐系统所需的表结构并插入测试数据

表结构:
1. sofa_demo_v2: 沙发产品主表，包含产品基本信息和向量数据
2. sofa_product_docs: 产品详细文档表，存储产品文档分块和对应向量

作者: OceanBase Demo Team
日期: 2025-08-31
"""

import os
import json
import logging
import time
import pymysql
import dashscope
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm
import numpy as np

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DashScope API 配置
dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')

def text_embedding(query: str) -> List[float]:
    """
    使用通义千问文本嵌入模型生成向量
    
    Args:
        query: 输入文本
        
    Returns:
        1024维的文本向量
    """
    try:
        res = dashscope.TextEmbedding.call(
            model=dashscope.TextEmbedding.Models.text_embedding_v3,
            input=query
        )
        if res.status_code == 200:
            return res.output['embeddings'][0]['embedding']
        else:
            raise ValueError(f'Embedding error: {res}')
    except Exception as e:
        logger.error(f"文本向量化失败: {e}")
        raise

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量的余弦相似度
    
    Args:
        vec1: 向量1
        vec2: 向量2
        
    Returns:
        余弦相似度值 (0-1)
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# 沙发产品测试数据
SAMPLE_SOFA_DATA = [
    {
        "name": "北欧简约三人布艺沙发",
        "description": "采用优质亚麻布料，简约北欧设计风格，适合现代家庭客厅。舒适海绵填充，坚固实木框架。",
        "material": "布艺",
        "style": "北欧",
        "price": 6800,
        "size": "三人",
        "color": "浅灰色",
        "brand": "宜家风尚",
        "service_locations": "北京,上海,广州,深圳,杭州",
        "features": "可拆洗,防污染,环保材质",
        "dimensions": "210cm x 85cm x 85cm",
        "image_url": "https://example.com/images/nordic_sofa_1.jpg",
        "promotion_policy": {"discount": "新客户8.5折", "free_delivery": True, "warranty": "3年质保"}
    },
    {
        "name": "现代简约真皮沙发",
        "description": "头层牛皮制作，现代简约风格，适合商务场所和高端家庭。人体工学设计，舒适度极佳。",
        "material": "真皮",
        "style": "现代简约",
        "price": 15800,
        "size": "三人",
        "color": "黑色",
        "brand": "皮匠世家",
        "service_locations": "北京,上海,广州,深圳,成都,重庆",
        "features": "真皮质感,耐磨损,高端大气",
        "dimensions": "220cm x 90cm x 85cm",
        "image_url": "https://example.com/images/modern_leather_sofa.jpg",
        "promotion_policy": {"discount": "限时9折", "installment": "24期免息", "maintenance": "免费保养2次"}
    },
    {
        "name": "美式复古布艺组合沙发",
        "description": "美式复古风格，深色布艺面料，L型组合设计，适合大户型客厅。铜钉装饰，彰显复古韵味。",
        "material": "布艺",
        "style": "美式",
        "price": 12800,
        "size": "组合",
        "color": "深棕色",
        "brand": "美式经典",
        "service_locations": "北京,上海,广州,深圳,西安,武汉",
        "features": "组合设计,储物功能,复古铜钉",
        "dimensions": "280cm x 180cm x 85cm",
        "image_url": "https://example.com/images/american_vintage_sofa.jpg",
        "promotion_policy": {"gift": "赠送抱枕和地毯", "trade_in": "旧沙发抵扣500元", "warranty": "5年质保"}
    },
    {
        "name": "中式红木沙发",
        "description": "传统中式设计，红木框架，真皮坐垫，适合中式装修风格。手工雕刻工艺，彰显东方韵味。",
        "material": "真皮",
        "style": "中式",
        "price": 28800,
        "size": "三人",
        "color": "棕红色",
        "brand": "东方韵",
        "service_locations": "北京,上海,广州,深圳,天津,南京",
        "features": "红木框架,手工雕刻,传统工艺",
        "dimensions": "200cm x 80cm x 90cm",
        "image_url": "https://example.com/images/chinese_redwood_sofa.jpg",
        "promotion_policy": {"vip": "VIP客户专享95折", "customization": "免费定制服务", "collection": "免费上门收藏鉴定"}
    },
    {
        "name": "小户型双人布艺沙发",
        "description": "专为小户型设计，双人座椅，北欧简约风格。占地面积小，但坐感舒适，适合年轻人的小公寓。",
        "material": "布艺",
        "style": "北欧",
        "price": 3800,
        "size": "双人",
        "color": "米白色",
        "brand": "小空间大设计",
        "service_locations": "北京,上海,广州,深圳,杭州,苏州",
        "features": "小户型专用,轻便移动,高性价比",
        "dimensions": "150cm x 75cm x 80cm",
        "image_url": "https://example.com/images/compact_two_seater.jpg",
        "promotion_policy": {"student": "学生优惠7.5折", "combo": "买沙发送茶几", "return": "7天无理由退换"}
    }
]

# 产品详细文档数据（为产品ID=1提供详细文档分块）
SAMPLE_PRODUCT_DOCS = [
    {
        "product_id": 1,
        "chunk_id": "nordic_sofa_material",
        "chunk_title": "材质工艺详情",
        "chunk_content": """
        北欧简约三人布艺沙发采用进口亚麻布料，具有天然的纹理和触感。面料经过防污处理，易于清洁和维护。
        
        主要材质特点：
        - 面料：100%亚麻纤维，透气性好，四季适用
        - 填充：高密度海绵+羽绒填充，回弹性强，久坐不变形
        - 框架：北欧松木实木框架，坚固耐用，承重能力强
        - 连接：传统榫卯工艺结合现代五金件，确保结构稳定
        
        工艺细节：
        - 所有拼接处采用双线缝制，增强耐用性
        - 面料可拆卸设计，便于清洗和更换
        - 环保水性漆处理，无甲醛释放
        """
    },
    {
        "product_id": 1,
        "chunk_id": "nordic_sofa_comfort",
        "chunk_title": "舒适体验设计",
        "chunk_content": """
        北欧简约沙发在设计时充分考虑了人体工程学原理，为用户提供极致的舒适体验。
        
        舒适性特点：
        - 座椅高度：45cm，符合亚洲人身材比例
        - 座椅深度：55cm，适合各种坐姿需求
        - 靠背角度：105°倾斜角，缓解脊椎压力
        - 扶手高度：65cm，提供良好的手臂支撑
        
        功能特性：
        - 坐垫可翻转使用，延长使用寿命
        - 靠背支撑力可调节，适应不同体重用户
        - 防滑底脚设计，确保沙发稳定性
        - 圆角设计，避免磕碰，适合有儿童的家庭
        """
    },
    {
        "product_id": 1,
        "chunk_id": "nordic_sofa_maintenance",
        "chunk_title": "保养维护指南",
        "chunk_content": """
        正确的保养维护可以延长北欧布艺沙发的使用寿命，保持最佳状态。
        
        日常保养：
        - 每周用吸尘器清理表面灰尘和毛发
        - 避免阳光直射，防止面料褪色
        - 定期翻转坐垫，保持形状均匀
        - 保持室内湿度在40%-60%，防止面料干裂
        
        清洁方法：
        - 可拆卸面料：30°温水机洗，自然晾干
        - 局部污渍：中性清洁剂+温水轻拭
        - 深度清洁：建议每季度专业清洗一次
        - 木质框架：用微湿布擦拭，避免使用化学清洁剂
        
        注意事项：
        - 避免尖锐物体划伤面料
        - 宠物指甲可能对面料造成损害
        - 不要在沙发上跳跃，以免损坏内部结构
        """
    },
    {
        "product_id": 1,
        "chunk_id": "nordic_sofa_space_matching",
        "chunk_title": "空间搭配建议",
        "chunk_content": """
        北欧简约沙发适合多种家居风格，合理的空间搭配可以营造理想的居住氛围。
        
        适合空间：
        - 客厅面积：15-25平方米最佳
        - 层高要求：2.7米以上，营造开阔感
        - 光线条件：朝南或朝东，充足的自然光线
        
        搭配建议：
        - 茶几：选择简约玻璃或原木茶几，尺寸120x60cm
        - 地毯：北欧几何图案地毯，尺寸200x140cm
        - 墙面：白色或浅灰色，突出沙发的质感
        - 照明：暖白光LED吊灯+落地阅读灯
        
        色彩搭配：
        - 主色调：浅灰+白色+原木色
        - 点缀色：可适当加入薄荷绿或天空蓝
        - 避免：过于鲜艳的颜色，破坏北欧简约风格
        
        配件推荐：
        - 抱枕：亚麻材质，几何或条纹图案
        - 毯子：羊毛或棉质，纯色或简单图案
        - 绿植：龟背竹、橡皮树等大型绿植
        """
    },
    {
        "product_id": 1,
        "chunk_id": "nordic_sofa_warranty_service",
        "chunk_title": "售后服务政策",
        "chunk_content": """
        我们为北欧简约三人布艺沙发提供全面的售后服务保障，确保您的购买无忧。
        
        质保政策：
        - 整体质保：3年免费质保
        - 框架质保：10年结构性问题免费维修
        - 面料质保：1年内非人为损坏免费更换
        - 填充材料：2年内下沉超过3cm免费更换
        
        服务内容：
        - 免费配送：市内免费配送安装
        - 安装服务：专业师傅上门安装，提供使用指导
        - 维修服务：质保期内免费上门维修
        - 清洁服务：首年免费上门深度清洁1次
        
        服务网点：
        - 北京：朝阳区、海淀区、丰台区设有服务点
        - 上海：浦东新区、静安区、徐汇区设有服务点
        - 广州：天河区、越秀区设有服务点
        - 深圳：南山区、福田区设有服务点
        - 杭州：西湖区、上城区设有服务点
        
        联系方式：
        - 客服热线：400-888-8888
        - 在线客服：工作日9:00-18:00
        - 官方微信：扫码关注获取实时服务
        """
    }
]

class DatabaseInitializer:
    """数据库初始化器"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.db_config = {
            'host': os.getenv('OB_URL', 'localhost').split(':')[0],
            'port': int(os.getenv('OB_URL', 'localhost:3306').split(':')[1]) if ':' in os.getenv('OB_URL', 'localhost:3306') else 3306,
            'user': os.getenv('OB_USER', 'root'),
            'password': os.getenv('OB_PWD', ''),
            'database': os.getenv('OB_DB_NAME', 'test'),
            'charset': 'utf8mb4'
        }
        
        # 验证环境变量
        self._validate_environment()
        
        # 测试数据库连接
        self._test_connection()
    
    def _validate_environment(self):
        """验证必要的环境变量"""
        required_vars = ['OB_URL', 'OB_USER', 'OB_DB_NAME', 'DASHSCOPE_API_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"缺少必要的环境变量: {', '.join(missing_vars)}")
        
        logger.info("✅ 环境变量验证通过")
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            connection = pymysql.connect(**self.db_config)
            connection.close()
            logger.info("✅ 数据库连接测试成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise
    
    def create_sofa_demo_table(self):
        """创建沙发产品主表 sofa_demo_v2"""
        connection = pymysql.connect(**self.db_config)
        cursor = connection.cursor()
        
        try:
            # 删除已存在的表
            cursor.execute("DROP TABLE IF EXISTS sofa_demo_v2")
            logger.info("🗑️ 删除已存在的 sofa_demo_v2 表")
            
            # 创建表结构
            create_table_sql = """
            CREATE TABLE sofa_demo_v2 (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '产品ID',
                name VARCHAR(255) NOT NULL COMMENT '沙发名称',
                description LONGTEXT COMMENT '产品描述',
                material VARCHAR(100) COMMENT '材质',
                style VARCHAR(100) COMMENT '风格',
                price DECIMAL(10,2) COMMENT '价格',
                size VARCHAR(100) COMMENT '尺寸规格',
                color VARCHAR(100) COMMENT '颜色',
                brand VARCHAR(100) COMMENT '品牌',
                service_locations VARCHAR(500) COMMENT '服务点位置',
                features VARCHAR(500) COMMENT '特色功能',
                dimensions VARCHAR(100) COMMENT '具体尺寸',
                image_url VARCHAR(500) COMMENT '产品图片URL',
                promotion_policy JSON COMMENT '优惠政策',
                description_vector VECTOR(1024) COMMENT '描述向量',
                image_vector VECTOR(1024) COMMENT '图片向量',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='沙发产品信息表'
            """
            
            cursor.execute(create_table_sql)
            logger.info("✅ 创建 sofa_demo_v2 表成功")
            
            # 创建向量索引
            try:
                cursor.execute("""
                    CREATE VECTOR INDEX idx_sofa_demo_v2_description_vector 
                    ON sofa_demo_v2(description_vector) 
                    WITH distance=cosine, type=hnsw, lib=vsag
                """)
                logger.info("✅ 创建描述向量索引成功")
            except Exception as e:
                logger.warning(f"⚠️ 创建描述向量索引失败: {e}")
            
            try:
                cursor.execute("""
                    CREATE VECTOR INDEX idx_sofa_demo_v2_image_vector 
                    ON sofa_demo_v2(image_vector) 
                    WITH distance=cosine, type=hnsw, lib=vsag
                """)
                logger.info("✅ 创建图片向量索引成功")
            except Exception as e:
                logger.warning(f"⚠️ 创建图片向量索引失败: {e}")
            
            connection.commit()
            
        except Exception as e:
            connection.rollback()
            logger.error(f"❌ 创建 sofa_demo_v2 表失败: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def create_product_docs_table(self):
        """创建产品文档表 sofa_product_docs"""
        connection = pymysql.connect(**self.db_config)
        cursor = connection.cursor()
        
        try:
            # 删除已存在的表
            cursor.execute("DROP TABLE IF EXISTS sofa_product_docs")
            logger.info("🗑️ 删除已存在的 sofa_product_docs 表")
            
            # 创建表结构
            create_table_sql = """
            CREATE TABLE sofa_product_docs (
                id INT AUTO_INCREMENT PRIMARY KEY COMMENT '文档ID',
                product_id INT NOT NULL COMMENT '关联的产品ID',
                chunk_id VARCHAR(255) NOT NULL COMMENT '文档分块唯一标识',
                chunk_title VARCHAR(500) NOT NULL COMMENT '文档分块标题',
                chunk_content LONGTEXT NOT NULL COMMENT '文档分块内容',
                chunk_vector VECTOR(1024) COMMENT '文档分块向量',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_product_id (product_id),
                UNIQUE KEY uk_product_chunk (product_id, chunk_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='产品详细文档表'
            """
            
            cursor.execute(create_table_sql)
            logger.info("✅ 创建 sofa_product_docs 表成功")
            
            # 创建向量索引
            try:
                cursor.execute("""
                    CREATE VECTOR INDEX idx_sofa_product_docs_chunk_vector 
                    ON sofa_product_docs(chunk_vector) 
                    WITH distance=cosine, type=hnsw, lib=vsag
                """)
                logger.info("✅ 创建文档向量索引成功")
            except Exception as e:
                logger.warning(f"⚠️ 创建文档向量索引失败: {e}")
            
            connection.commit()
            
        except Exception as e:
            connection.rollback()
            logger.error(f"❌ 创建 sofa_product_docs 表失败: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def insert_sofa_data(self):
        """插入沙发产品数据"""
        connection = pymysql.connect(**self.db_config)
        cursor = connection.cursor()
        
        try:
            logger.info("🚀 开始插入沙发产品数据...")
            
            for sofa_data in tqdm(SAMPLE_SOFA_DATA, desc="插入沙发数据"):
                try:
                    # 生成描述向量
                    full_description = f"{sofa_data['name']} {sofa_data['description']} {sofa_data['material']} {sofa_data['style']} {sofa_data['features']}"
                    description_vector = text_embedding(full_description)
                    
                    # 生成图片向量（这里使用描述向量模拟，实际应用中应该用真实图片）
                    image_description = f"图片展示 {sofa_data['name']} {sofa_data['color']} {sofa_data['style']}风格沙发"
                    image_vector = text_embedding(image_description)
                    
                    # 插入数据
                    insert_sql = """
                    INSERT INTO sofa_demo_v2 (
                        name, description, material, style, price, size, color, brand,
                        service_locations, features, dimensions, image_url, promotion_policy,
                        description_vector, image_vector
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """
                    
                    cursor.execute(insert_sql, (
                        sofa_data['name'],
                        sofa_data['description'],
                        sofa_data['material'],
                        sofa_data['style'],
                        sofa_data['price'],
                        sofa_data['size'],
                        sofa_data['color'],
                        sofa_data['brand'],
                        sofa_data['service_locations'],
                        sofa_data['features'],
                        sofa_data['dimensions'],
                        sofa_data['image_url'],
                        json.dumps(sofa_data['promotion_policy'], ensure_ascii=False),
                        json.dumps(description_vector),
                        json.dumps(image_vector)
                    ))
                    
                    # 适当延时避免API限制
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"插入沙发数据失败 {sofa_data['name']}: {e}")
                    continue
            
            connection.commit()
            logger.info(f"✅ 成功插入 {len(SAMPLE_SOFA_DATA)} 条沙发产品数据")
            
        except Exception as e:
            connection.rollback()
            logger.error(f"❌ 插入沙发数据失败: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def insert_product_docs_data(self):
        """插入产品文档数据"""
        connection = pymysql.connect(**self.db_config)
        cursor = connection.cursor()
        
        try:
            logger.info("📚 开始插入产品文档数据...")
            
            for doc_data in tqdm(SAMPLE_PRODUCT_DOCS, desc="插入文档数据"):
                try:
                    # 生成文档内容向量
                    content_for_embedding = f"{doc_data['chunk_title']} {doc_data['chunk_content']}"
                    chunk_vector = text_embedding(content_for_embedding)
                    
                    # 插入数据
                    insert_sql = """
                    INSERT INTO sofa_product_docs (
                        product_id, chunk_id, chunk_title, chunk_content, chunk_vector
                    ) VALUES (%s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_sql, (
                        doc_data['product_id'],
                        doc_data['chunk_id'],
                        doc_data['chunk_title'],
                        doc_data['chunk_content'],
                        json.dumps(chunk_vector)
                    ))
                    
                    # 适当延时避免API限制
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"插入文档数据失败 {doc_data['chunk_id']}: {e}")
                    continue
            
            connection.commit()
            logger.info(f"✅ 成功插入 {len(SAMPLE_PRODUCT_DOCS)} 条产品文档数据")
            
        except Exception as e:
            connection.rollback()
            logger.error(f"❌ 插入产品文档数据失败: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def verify_data(self):
        """验证数据插入结果"""
        connection = pymysql.connect(**self.db_config)
        cursor = connection.cursor()
        
        try:
            logger.info("🔍 开始验证数据插入结果...")
            
            # 验证沙发产品表
            cursor.execute("SELECT COUNT(*) FROM sofa_demo_v2")
            sofa_count = cursor.fetchone()[0]
            logger.info(f"📊 sofa_demo_v2 表共有 {sofa_count} 条记录")
            
            # 显示部分沙发数据
            cursor.execute("SELECT id, name, material, style, price FROM sofa_demo_v2 LIMIT 3")
            sofa_samples = cursor.fetchall()
            logger.info("📋 沙发产品样本数据:")
            for sample in sofa_samples:
                logger.info(f"  - ID:{sample[0]} | {sample[1]} | {sample[2]} | {sample[3]} | ¥{sample[4]}")
            
            # 验证产品文档表
            cursor.execute("SELECT COUNT(*) FROM sofa_product_docs")
            docs_count = cursor.fetchone()[0]
            logger.info(f"📊 sofa_product_docs 表共有 {docs_count} 条记录")
            
            # 显示部分文档数据
            cursor.execute("SELECT product_id, chunk_id, chunk_title FROM sofa_product_docs LIMIT 3")
            docs_samples = cursor.fetchall()
            logger.info("📋 产品文档样本数据:")
            for sample in docs_samples:
                logger.info(f"  - 产品ID:{sample[0]} | {sample[1]} | {sample[2]}")
            
            # 验证向量数据
            cursor.execute("SELECT id, LENGTH(description_vector) as desc_len, LENGTH(image_vector) as img_len FROM sofa_demo_v2 LIMIT 1")
            vector_sample = cursor.fetchone()
            if vector_sample:
                logger.info(f"🧮 向量数据验证: ID={vector_sample[0]}, 描述向量长度={vector_sample[1]}, 图片向量长度={vector_sample[2]}")
            
            logger.info("✅ 数据验证完成！数据库初始化成功！")
            
        except Exception as e:
            logger.error(f"❌ 数据验证失败: {e}")
            raise
        finally:
            cursor.close()
            connection.close()
    
    def run_full_initialization(self):
        """运行完整的数据库初始化流程"""
        logger.info("🚀 开始 OceanBase 数据库完整初始化...")
        
        start_time = time.time()
        
        try:
            # 1. 创建表结构
            logger.info("\n" + "="*50)
            logger.info("📊 第1步: 创建数据表结构")
            logger.info("="*50)
            self.create_sofa_demo_table()
            self.create_product_docs_table()
            
            # 2. 插入测试数据
            logger.info("\n" + "="*50)
            logger.info("💾 第2步: 插入测试数据")
            logger.info("="*50)
            self.insert_sofa_data()
            self.insert_product_docs_data()
            
            # 3. 验证数据
            logger.info("\n" + "="*50)
            logger.info("🔍 第3步: 验证数据完整性")
            logger.info("="*50)
            self.verify_data()
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info("\n" + "="*50)
            logger.info("🎉 数据库初始化完成!")
            logger.info(f"⏱️ 总耗时: {duration:.2f} 秒")
            logger.info("="*50)
            
            # 显示后续使用指南
            self._show_usage_guide()
            
        except Exception as e:
            logger.error(f"\n❌ 数据库初始化失败: {e}")
            logger.error("请检查环境配置和网络连接后重试")
            raise
    
    def _show_usage_guide(self):
        """显示使用指南"""
        logger.info("\n📖 使用指南:")
        logger.info("="*50)
        logger.info("1. 🛋️ 产品推荐: python conversation_ui.py")
        logger.info("2. 🔧 数据处理: python srd/data/sofa_data_preprocessor.py")
        logger.info("3. 🧪 功能测试: python -c \"from srd.tools.retrieval_tool import SofaRetrievalTool; tool = SofaRetrievalTool(); print(tool.search_by_text('北欧沙发'))\"")
        logger.info("4. 📊 数据查询: 使用任意 MySQL 客户端连接数据库查看数据")
        logger.info("\n📋 数据表说明:")
        logger.info("- sofa_demo_v2: 沙发产品主表（包含向量数据）")
        logger.info("- sofa_product_docs: 产品详细文档表（支持语义检索）")
        logger.info("="*50)

def main():
    """主函数"""
    try:
        # 显示欢迎信息
        logger.info("="*60)
        logger.info("🌊 OceanBase 多模态产品推荐系统 - 数据库初始化")
        logger.info("="*60)
        logger.info("📝 此脚本将创建并初始化以下数据表:")
        logger.info("  1. sofa_demo_v2 - 沙发产品信息表")
        logger.info("  2. sofa_product_docs - 产品详细文档表")
        logger.info("⚠️  注意: 此操作将删除现有数据，请确认后继续")
        logger.info("="*60)
        
        # 确认执行
        confirm = input("\n🤔 是否继续执行数据库初始化？(y/N): ").lower().strip()
        if confirm not in ['y', 'yes']:
            logger.info("❌ 用户取消操作")
            return
        
        # 执行初始化
        initializer = DatabaseInitializer()
        initializer.run_full_initialization()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 用户中断操作")
    except Exception as e:
        logger.error(f"\n💥 初始化失败: {e}")
        logger.error("🔧 请检查 .env 文件配置和网络连接")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
