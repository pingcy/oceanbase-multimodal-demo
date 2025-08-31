import os
import re
import json
import logging
from typing import Dict, List, Any, Optional
from pyobvector import ObVecClient
from .tool import Tool
from sqlalchemy import Table, func, and_, text
import dashscope
from http import HTTPStatus
import dotenv
from PIL import Image
import base64
import io

DEFAULT_MATERIAL_NAME = "material"
DEFAULT_STYLE_NAME = "style"
DEFAULT_PRICE_MIN_NAME = "price_min"
DEFAULT_PRICE_MAX_NAME = "price_max"
DEFAULT_COLOR_NAME = "color"
DEFAULT_BRAND_NAME = "brand"
DEFAULT_SIZE_NAME = "size"

logger = logging.getLogger(__name__)
dotenv.load_dotenv()

class SofaRetrievalTool(Tool):
    def __init__(
        self,
        table_name: str,
        topk: int,
        echo: bool = False,
        material_name: str = DEFAULT_MATERIAL_NAME,
        style_name: str = DEFAULT_STYLE_NAME,
        price_min_name: str = DEFAULT_PRICE_MIN_NAME,
        price_max_name: str = DEFAULT_PRICE_MAX_NAME,
        color_name: str = DEFAULT_COLOR_NAME,
        brand_name: str = DEFAULT_BRAND_NAME,
        size_name: str = DEFAULT_SIZE_NAME,
        **kwargs,
    ):
        self.table_name = table_name
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
                echo=echo, **kwargs
            )
        else:
            self.client = ObVecClient(
                uri=uri,
                user=user,
                password=pwd,
                db_name=db_name,
                echo=echo, **kwargs
            )
        self.topk = topk
        self.material_name = material_name
        self.style_name = style_name
        self.price_min_name = price_min_name
        self.price_max_name = price_max_name
        self.color_name = color_name
        self.brand_name = brand_name
        self.size_name = size_name
        self.embed_api_key = os.getenv("DASHSCOPE_API_KEY")
        if self.embed_api_key is None:
            raise ValueError("embed_api_key is None")
    
    @classmethod
    def text_embedding(cls, query: str):
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

    @classmethod
    def image_embedding(cls, image_path: str):
        """图像嵌入"""
        try:
            # 使用多模态嵌入模型 - 直接传递文件路径
            res = dashscope.MultiModalEmbedding.call(
                model="multimodal-embedding-v1",
                input=[{
                    'image': image_path
                }],
                api_key=os.getenv("DASHSCOPE_API_KEY"),
            )
            if res.status_code == HTTPStatus.OK:
                return res.output['embeddings'][0]['embedding']
            else:
                raise ValueError(f"image embedding error: {res}")
        except Exception as e:
            logger.error(f"Failed to process image {image_path}: {e}")
            raise

    @classmethod
    def parse_price_range(cls, price_str: str) -> tuple:
        """解析价格范围字符串"""
        if not price_str:
            return None, None
        
        # 提取数字
        numbers = re.findall(r'\d+', price_str)
        if len(numbers) == 1:
            price = int(numbers[0])
            return price * 0.8, price * 1.2  # 允许20%的浮动
        elif len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        else:
            return None, None

    def search_by_text(self, query: str, filters: Dict[str, Any] = None) -> List[Dict]:
        """基于文本的搜索"""
        embedding = self.text_embedding(query)
        return self._vector_search(embedding, filters, search_type='text')
    
    def search_by_image(self, image_path: str, filters: Dict[str, Any] = None) -> List[Dict]:
        """基于图像的搜索"""
        embedding = self.image_embedding(image_path)
        return self._vector_search(embedding, filters, search_type='image')
    
    def search_hybrid(self, text_query: str = None, image_path: str = None, 
                     filters: Dict[str, Any] = None, text_weight: float = 0.3) -> List[Dict]:
        """混合搜索：文本 + 图像"""
        if not text_query and not image_path:
            raise ValueError("At least one of text_query or image_path must be provided")
        
        if text_query and image_path:
            # 获取文本和图像嵌入
            text_emb = self.text_embedding(text_query)
            image_emb = self.image_embedding(image_path)
            return self._vector_search_hybrid(text_emb, image_emb, filters, text_weight)
        elif text_query:
            return self.search_by_text(text_query, filters)
        else:
            return self.search_by_image(image_path, filters)

    def _vector_search(self, embedding: List[float], filters: Dict[str, Any] = None, search_type: str = 'text') -> List[Dict]:
        """执行向量搜索"""
        try:
            # 根据搜索类型选择向量字段
            vector_column = 'description_vector' if search_type == 'text' else 'image_vector'
            
            # 构建基础查询语句
            base_query = f"""
                SELECT id, name, description, material, style, price, size, color, 
                       brand, service_locations, features, dimensions, promotion_policy, image_url,
                       cosine_distance({vector_column}, '{embedding}') as similarity
                FROM {self.table_name}
            """
            
            # 添加过滤条件
            conditions = []
            
            if filters:
                # 材质过滤
                if filters.get(self.material_name):
                    conditions.append(f"material LIKE '%{filters[self.material_name]}%'")
                
                # 风格过滤
                if filters.get(self.style_name):
                    conditions.append(f"style LIKE '%{filters[self.style_name]}%'")
                
                # 价格范围过滤
                price_min = filters.get(self.price_min_name)
                price_max = filters.get(self.price_max_name)
                
                if price_min is not None and price_max is not None:
                    conditions.append(f"price BETWEEN {price_min} AND {price_max}")
                elif price_min is not None:
                    conditions.append(f"price >= {price_min}")
                elif price_max is not None:
                    conditions.append(f"price <= {price_max}")
                
                # 颜色过滤
                if filters.get(self.color_name):
                    conditions.append(f"color LIKE '%{filters[self.color_name]}%'")
                
                # 品牌过滤
                if filters.get(self.brand_name):
                    conditions.append(f"brand LIKE '%{filters[self.brand_name]}%'")
                
                # 尺寸过滤
                if filters.get(self.size_name):
                    conditions.append(f"size LIKE '%{filters[self.size_name]}%'")
            
            # 组合查询语句
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += f" ORDER BY similarity ASC LIMIT {self.topk}"
            
            # 执行查询
            results = self.client.perform_raw_text_sql(base_query)
            
            # 转换结果
            return self._parse_search_results(results)
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _vector_search_hybrid(self, text_embedding: List[float], image_embedding: List[float], 
                             filters: Dict[str, Any] = None, text_weight: float = 0.3) -> List[Dict]:
        """执行混合向量搜索：同时使用文本和图像向量"""
        try:
            # 构建混合相似度查询语句
            base_query = f"""
                SELECT id, name, description, material, style, price, size, color, 
                       brand, service_locations, features, dimensions, promotion_policy, image_url,
                       cosine_distance(description_vector, '{text_embedding}') as text_similarity,
                       cosine_distance(image_vector, '{image_embedding}') as image_similarity,
                       ({text_weight} * cosine_distance(description_vector, '{text_embedding}') + 
                        {1 - text_weight} * cosine_distance(image_vector, '{image_embedding}')) as combined_similarity
                FROM {self.table_name}
            """
            
            # 添加过滤条件
            conditions = []
            
            if filters:
                # 材质过滤
                if filters.get(self.material_name):
                    conditions.append(f"material LIKE '%{filters[self.material_name]}%'")
                
                # 风格过滤
                if filters.get(self.style_name):
                    conditions.append(f"style LIKE '%{filters[self.style_name]}%'")
                
                # 价格范围过滤
                price_min = filters.get(self.price_min_name)
                price_max = filters.get(self.price_max_name)
                
                if price_min is not None and price_max is not None:
                    conditions.append(f"price BETWEEN {price_min} AND {price_max}")
                elif price_min is not None:
                    conditions.append(f"price >= {price_min}")
                elif price_max is not None:
                    conditions.append(f"price <= {price_max}")
                
                # 颜色过滤
                if filters.get(self.color_name):
                    conditions.append(f"color LIKE '%{filters[self.color_name]}%'")
                
                # 品牌过滤
                if filters.get(self.brand_name):
                    conditions.append(f"brand LIKE '%{filters[self.brand_name]}%'")
                
                # 尺寸过滤
                if filters.get(self.size_name):
                    conditions.append(f"size LIKE '%{filters[self.size_name]}%'")
            
            # 组合查询语句
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            # 按组合相似度排序
            base_query += f" ORDER BY combined_similarity ASC LIMIT {self.topk}"
            
            # 执行查询
            results = self.client.perform_raw_text_sql(base_query)
            
            # 转换结果（包含额外的相似度信息）
            return self._parse_hybrid_search_results(results)
            
        except Exception as e:
            logger.error(f"Hybrid vector search failed: {e}")
            return []

    def _parse_search_results(self, results) -> List[Dict]:
        """解析普通搜索结果"""
        sofa_list = []
        if hasattr(results, 'fetchall'):
            rows = results.fetchall()
            for row in rows:
                sofa_dict = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'material': row[3],
                    'style': row[4],
                    'price': row[5],
                    'size': row[6],
                    'color': row[7],
                    'brand': row[8],
                    'service_locations': row[9],
                    'features': row[10],
                    'dimensions': row[11],
                    'promotion_policy': row[12],
                    'image_url': row[13],
                    'similarity': row[14],
                }
                sofa_list.append(sofa_dict)
        return sofa_list

    def _parse_hybrid_search_results(self, results) -> List[Dict]:
        """解析混合搜索结果"""
        sofa_list = []
        if hasattr(results, 'fetchall'):
            rows = results.fetchall()
            for row in rows:
                sofa_dict = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'material': row[3],
                    'style': row[4],
                    'price': row[5],
                    'size': row[6],
                    'color': row[7],
                    'brand': row[8],
                    'service_locations': row[9],
                    'features': row[10],
                    'dimensions': row[11],
                    'promotion_policy': row[12],
                    'image_url': row[13],
                    'text_similarity': row[14],
                    'image_similarity': row[15],
                    'combined_similarity': row[16],
                    'similarity': row[16],  # 使用组合相似度作为主要相似度
                }
                sofa_list.append(sofa_dict)
        return sofa_list

    def call(self, **kwargs) -> List[Dict]:
        """工具调用接口"""
        search_type = kwargs.get('search_type', 'text')
        filters = kwargs.get('filters', {})
        
        if search_type == 'text':
            query = kwargs.get('query', '')
            return self.search_by_text(query, filters)
        elif search_type == 'image':
            image_path = kwargs.get('image_path', '')
            return self.search_by_image(image_path, filters)
        elif search_type == 'hybrid':
            text_query = kwargs.get('query', '')
            image_path = kwargs.get('image_path', '')
            text_weight = kwargs.get('text_weight', 0.7)
            return self.search_hybrid(text_query, image_path, filters, text_weight)
        else:
            raise ValueError(f"Unsupported search_type: {search_type}")
