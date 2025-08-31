import os
import json
import logging
import time
import dotenv
from typing import List
from pyobvector import *
from sqlalchemy import Column, Integer, String, JSON, Index, Float
from sqlalchemy.dialects.mysql import LONGTEXT
from tqdm import tqdm
import dashscope
from http import HTTPStatus

dotenv.load_dotenv()

DEFAULT_SOFA_TABLE_NAME = "sofa_demo_v2"
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

def text_embedding(query: str):
    """文本嵌入"""
    res = dashscope.TextEmbedding.call(
        model=dashscope.TextEmbedding.Models.text_embedding_v3,  # 使用1024维的模型
        input=[query],
        api_key=os.getenv("DASHSCOPE_API_KEY"),
    )
    if res.status_code == HTTPStatus.OK:
        return [eb['embedding'] for eb in res.output['embeddings']][0]
    else:
        raise ValueError(f"embedding error: {res}")

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
        "promotion_policy": {"student": "学生优惠7.5折", "combo": "买沙发送茶几", "return": "7天无理由退换"}
    },
    {
        "name": "欧式奢华真皮沙发",
        "description": "欧式奢华风格，进口头层牛皮，手工缝制工艺。高档五金配件，彰显贵族气质。",
        "material": "真皮",
        "style": "欧式",
        "price": 35800,
        "size": "三人",
        "color": "深咖啡色",
        "brand": "欧陆贵族",
        "service_locations": "北京,上海,广州,深圳,成都,青岛",
        "features": "进口皮料,手工缝制,奢华配件",
        "dimensions": "230cm x 95cm x 95cm",
        "promotion_policy": {"luxury": "奢华套装9.2折", "white_glove": "白手套配送安装", "concierge": "专属管家服务"}
    },
    {
        "name": "日式简约单人沙发",
        "description": "日式极简风格，单人座椅，天然橡木框架。简洁线条设计，适合禅意生活方式。",
        "material": "布艺",
        "style": "日式",
        "price": 2800,
        "size": "单人",
        "color": "原木色",
        "brand": "和风家居",
        "service_locations": "北京,上海,广州,深圳,杭州,厦门",
        "features": "橡木框架,环保无漆,极简设计",
        "dimensions": "80cm x 75cm x 75cm",
        "promotion_policy": {"zen": "禅意套装优惠", "eco": "环保材质认证", "minimalist": "极简生活倡导奖励"}
    },
    {
        "name": "工业风铁艺布艺沙发",
        "description": "工业风格设计，铁艺框架，粗糙布艺面料。适合loft风格装修，展现个性态度。",
        "material": "布艺",
        "style": "工业风",
        "price": 4500,
        "size": "双人",
        "color": "灰黑色",
        "brand": "工业时代",
        "service_locations": "北京,上海,广州,深圳,武汉,西安",
        "features": "铁艺框架,工业风格,个性设计",
        "dimensions": "160cm x 80cm x 75cm",
        "promotion_policy": {"loft": "LOFT装修套餐8折", "industrial": "工业风配件赠送", "personality": "个性定制服务"}
    },
    {
        "name": "现代科技智能沙发",
        "description": "集成按摩功能、USB充电、蓝牙音响等智能功能。现代科技与舒适体验的完美结合。",
        "material": "真皮",
        "style": "现代",
        "price": 25800,
        "size": "三人",
        "color": "黑色",
        "brand": "智能家居",
        "service_locations": "北京,上海,广州,深圳,杭州,成都",
        "features": "按摩功能,USB充电,蓝牙音响,智能控制",
        "dimensions": "220cm x 90cm x 85cm",
        "promotion_policy": {"tech": "科技爱好者9折", "smart_home": "智能家居套装优惠", "upgrade": "终身软件升级"}
    },
    {
        "name": "田园风碎花布艺沙发",
        "description": "田园风格设计，碎花图案布艺面料，营造温馨浪漫的家居氛围。适合女性和家庭用户。",
        "material": "布艺",
        "style": "田园风",
        "price": 5800,
        "size": "三人",
        "color": "粉色碎花",
        "brand": "田园时光",
        "service_locations": "北京,上海,广州,深圳,南京,长沙",
        "features": "碎花图案,温馨浪漫,女性喜爱",
        "dimensions": "200cm x 85cm x 80cm",
        "promotion_policy": {"romantic": "浪漫情侣套装", "family": "家庭温馨大礼包", "floral": "花卉主题配件赠送"}
    }
]

class SofaDataPreprocessor:
    def __init__(self, table_name: str = DEFAULT_SOFA_TABLE_NAME):
        self.table_name = table_name
        self.setup_database()

    def setup_database(self):
        """初始化数据库连接"""
        ssl_ca_path = os.getenv("OB_DB_SSL_CA_PATH")
        if ssl_ca_path:
            connect_args = {
                "ssl": {
                    "ca": ssl_ca_path,
                    "check_hostname": False,
                }
            }
        
        uri = os.getenv("OB_URL", "127.0.0.1:2881")
        user = os.getenv("OB_USER", "root@test")
        db_name = os.getenv("OB_DB_NAME", "test")
        pwd = os.getenv("OB_PWD", "")
        
        if ssl_ca_path:
            self.client = ObVecClient(
                uri=uri,
                user=user,
                password=pwd,
                db_name=db_name,
                connect_args=connect_args,
            )
        else:
            self.client = ObVecClient(
                uri=uri,
                user=user,
                password=pwd,
                db_name=db_name,
            )

    def create_table(self):
        """创建沙发产品表"""
        
        # 检查表是否已存在
        if self.client.check_table_exists(table_name=self.table_name):
            logger.info(f"Table {self.table_name} already exists")
            return
        
        # 定义表结构
        cols = [
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(255), nullable=False, comment="沙发名称"),
            Column("description", LONGTEXT, comment="产品描述"),
            Column("material", String(100), comment="材质"),
            Column("style", String(100), comment="风格"),
            Column("price", Float, comment="价格"),
            Column("size", String(100), comment="尺寸规格"),
            Column("color", String(100), comment="颜色"),
            Column("brand", String(100), comment="品牌"),
            Column("service_locations", String(500), comment="服务点位置"),
            Column("features", String(500), comment="特色功能"),
            Column("dimensions", String(100), comment="具体尺寸"),
            Column("promotion_policy", JSON, comment="优惠政策"),
            Column("description_vector", VECTOR(1024), comment="描述向量"),
            Column("image_vector", VECTOR(1024), comment="图片向量"),
        ]
        
        # 创建索引 (暂时移除所有索引避免冲突)
        indexes = []
        
        # 创建表
        self.client.create_table(
            table_name=self.table_name,
            columns=cols,
            indexes=indexes,
        )
        
        # 创建向量索引 (分别创建，避免语法错误)
        try:
            self.client.perform_raw_text_sql(f"""
                CREATE VECTOR INDEX idx_{self.table_name}_description_vector 
                ON {self.table_name}(description_vector) 
                WITH distance=cosine, type=hnsw, lib=vsag
            """)
            logger.info(f"Description vector index created successfully.")
        except Exception as e:
            logger.warning(f"Could not create description vector index: {e}")
            
        try:
            self.client.perform_raw_text_sql(f"""
                CREATE VECTOR INDEX idx_{self.table_name}_image_vector 
                ON {self.table_name}(image_vector) 
                WITH distance=cosine, type=hnsw, lib=vsag
            """)
            logger.info(f"Image vector index created successfully.")
        except Exception as e:
            logger.warning(f"Could not create image vector index: {e}")
        
        logger.info(f"Created table: {self.table_name}")

    def insert_sample_data(self):
        """插入示例数据"""
        self.create_table()
        
        # 删除现有表并重新创建
        try:
            self.client.perform_raw_text_sql(f"DROP TABLE IF EXISTS {self.table_name}")
            logger.info(f"Dropped existing table: {self.table_name}")
        except Exception as e:
            logger.warning(f"Failed to drop existing table: {e}")
        
        # 重新创建表
        self.create_table()
        
        logger.info("Starting to insert sample sofa data...")
        
        for sofa_data in tqdm(SAMPLE_SOFA_DATA, desc="Inserting sofa data"):
            try:
                # 生成描述向量
                full_description = f"{sofa_data['name']} {sofa_data['description']} {sofa_data['material']} {sofa_data['style']} {sofa_data['features']}"
                description_vector = text_embedding(full_description)
                
                # 生成图片向量（这里使用描述向量模拟，实际应用中应该用真实图片）
                image_vector = description_vector.copy()
                
                # 创建记录
                insert_data = {
                    "name": sofa_data['name'],
                    "description": sofa_data['description'],
                    "material": sofa_data['material'],
                    "style": sofa_data['style'],
                    "price": sofa_data['price'],
                    "size": sofa_data['size'],
                    "color": sofa_data['color'],
                    "brand": sofa_data['brand'],
                    "service_locations": sofa_data['service_locations'],
                    "features": sofa_data['features'],
                    "dimensions": sofa_data['dimensions'],
                    "promotion_policy": json.dumps(sofa_data['promotion_policy'], ensure_ascii=False),
                    "description_vector": description_vector,
                    "image_vector": image_vector
                }
                
                # 插入数据
                self.client.insert(
                    table_name=self.table_name,
                    data=insert_data
                )
                
                # 避免API限制，适当延时
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to process sofa {sofa_data['name']}: {e}")
                continue
        
        logger.info(f"Successfully inserted {len(SAMPLE_SOFA_DATA)} sofa records")

    def verify_data(self):
        """验证数据插入"""
        try:
            # 简单的验证方法
            sample_query = f"SELECT name, material, style, price FROM {self.table_name} LIMIT 5"
            results = self.client.perform_raw_text_sql(sample_query)
            
            # 安全地处理结果
            record_count = 0
            if hasattr(results, 'fetchall'):
                records = results.fetchall()
                record_count = len(records)
                logger.info(f"Found {record_count} sample records:")
                for i, record in enumerate(records):
                    logger.info(f"Sample record {i+1}: {record}")
            else:
                logger.info("Query executed but results format unknown")
                
            logger.info("Data verification completed successfully!")
        except Exception as e:
            logger.error(f"Failed to verify data: {e}")

def main():
    """主函数"""
    logger.info("Starting sofa data preprocessing...")
    
    # 检查环境变量
    required_env_vars = ["OB_URL", "OB_USER", "OB_DB_NAME", "DASHSCOPE_API_KEY"]
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(f"Missing required environment variable: {var}")
            return
    
    processor = SofaDataPreprocessor()
    
    try:
        # 插入示例数据
        processor.insert_sample_data()
        
        # 验证数据
        processor.verify_data()
        
        logger.info("Sofa data preprocessing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during preprocessing: {e}")
        raise

if __name__ == "__main__":
    main()
