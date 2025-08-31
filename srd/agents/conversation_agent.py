import json
import logging
from typing import Dict, List, Any, Optional, Annotated, TypedDict
from enum import Enum

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool

from ..llm import TongyiLLMConfig, TongyiLLM
from ..tools import SofaRetrievalTool
from ..prompt.prompt_list import (
    extract_info_prompt, 
    recommendation_prompt, 
    normal_chat_prompt, 
    intent_classification_prompt
)

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """用户意图类型"""
    NORMAL_CHAT = "normal_chat"  # 普通聊天
    PRODUCT_RECOMMENDATION = "product_recommendation"  # 产品推荐
    PRODUCT_DETAIL_INQUIRY = "product_detail_inquiry"  # 产品详细信息咨询
    OTHER = "other"  # 其他意图

class ConversationState(TypedDict):
    """对话状态"""
    messages: Annotated[List[BaseMessage], add_messages]
    intent: Optional[str]
    extracted_conditions: Optional[Dict[str, Any]]
    search_results: Optional[List[Dict]]
    last_user_message: Optional[str]
    uploaded_image_path: Optional[str]  # 新增：上传的图片路径
    recommended_products: Optional[List[Dict]]  # 新增：推荐的产品信息
    product_detail_results: Optional[Dict[str, Any]]  # 新增：产品详细信息结果
    inferred_product_id: Optional[int]  # 新增：从意图识别中推理出的产品ID

class SofaConversationAgent:
    """基于 LangGraph 的沙发咨询对话 Agent"""
    
    def __init__(self, table_name: str = "sofa_demo_v2", topk: int = 5):
        # 初始化 LLM
        self.llm_config = TongyiLLMConfig(llm_name='qwen-plus')
        self.llm = TongyiLLM(config=self.llm_config)
        
        # 初始化检索工具
        self.retrieval_tool = SofaRetrievalTool(table_name=table_name, topk=topk)
        
        # 创建工具列表
        self.tools = [
            self._create_extract_tool(), 
            self._create_retrieve_tool(),
            self._create_product_detail_tool()
        ]
        
        # 构建工作流图
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
    
    def _create_extract_tool(self):
        """创建信息提取工具"""
        @tool
        def extract_conditions(user_message: str) -> Dict[str, Any]:
            """
            从用户消息中提取沙发产品的筛选条件
            
            Args:
                user_message: 用户输入的消息
                
            Returns:
                包含提取条件的字典
            """
            try:
                # 调试信息：打印输入的文本
                logger.info(f"🔍 [调试] 提取条件 - 输入文本: {user_message}")
                
                prompt = extract_info_prompt.format(user_info=user_message)
                response = self.llm.chat(prompt)
                
                if response.status_code == 200:
                    response_text = response.output.text
                    
                    # 处理可能的代码块包装
                    if response_text.startswith("```json"):
                        # 移除代码块标记
                        response_text = response_text.replace("```json", "").replace("```", "").strip()
                    elif response_text.startswith("```"):
                        # 移除普通代码块标记
                        response_text = response_text.replace("```", "").strip()
                    
                    result = json.loads(response_text)
                    # 过滤掉 null 值
                    filtered_result = {k: v for k, v in result.items() if v is not None}
                    
                    # 调试信息：打印过滤的结构化信息
                    logger.info(f"📊 [调试] 提取条件 - 结构化输出: {json.dumps(filtered_result, ensure_ascii=False, indent=2)}")
                    
                    return filtered_result
                else:
                    logger.error(f"条件提取失败: {response}")
                    return {}
            except Exception as e:
                logger.error(f"条件提取异常: {e}")
                return {}
        
        return extract_conditions
    
    def _create_retrieve_tool(self):
        """创建产品检索工具"""
        @tool
        def retrieve_products(
            search_type: str = "text",
            query: str = "",
            image_path: Optional[str] = None,
            filters: Optional[Dict[str, Any]] = None
        ) -> List[Dict]:
            """
            检索沙发产品
            
            Args:
                search_type: 搜索类型 ("text", "image", "hybrid")
                query: 文本查询
                image_path: 图片路径
                filters: 筛选条件
                
            Returns:
                检索到的产品列表
            """
            try:
                # 调试信息：打印检索参数
                logger.info(f"🔍 [调试] 产品检索 - 搜索类型: {search_type}")
                logger.info(f"🔍 [调试] 产品检索 - 文本查询: {query}")
                logger.info(f"🔍 [调试] 产品检索 - 图片路径: {image_path}")
                logger.info(f"🔍 [调试] 产品检索 - 过滤条件: {json.dumps(filters, ensure_ascii=False, indent=2) if filters else 'None'}")
                
                if search_type == "text":
                    results = self.retrieval_tool.search_by_text(query, filters)
                elif search_type == "image":
                    results = self.retrieval_tool.search_by_image(image_path, filters)
                elif search_type == "hybrid":
                    results = self.retrieval_tool.search_hybrid(query, image_path, filters)
                else:
                    logger.error(f"不支持的搜索类型: {search_type}")
                    return []
                
                # 调试信息：打印检索结果
                logger.info(f"📊 [调试] 产品检索 - 检索到 {len(results)} 个产品")
                if results:
                    logger.info(f"📊 [调试] 产品检索 - 前3个结果的相似度: {[r.get('similarity', 0) for r in results[:3]]}")
                
                return results
            except Exception as e:
                logger.error(f"产品检索异常: {e}")
                return []
        
        return retrieve_products
    
    def _create_product_detail_tool(self):
        """创建产品详细信息检索工具"""
        @tool
        def retrieve_product_details(
            product_id: int = None,
            query_text: str = ""
        ) -> Dict[str, Any]:
            """
            检索产品的详细信息，包括基本信息和文档分块
            
            Args:
                product_id: 产品ID，如果为None则尝试从推荐产品中获取
                query_text: 用户查询的自然语言文本
                
            Returns:
                包含产品基本信息和相关文档分块的字典
            """
            try:
                import pymysql
                import json
                import os
                import dashscope
                import numpy as np
                from dotenv import load_dotenv
                
                # 加载环境变量
                load_dotenv()
                dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')
                
                def text_embedding(query: str):
                    '''获取文本向量'''
                    res = dashscope.TextEmbedding.call(
                        model=dashscope.TextEmbedding.Models.text_embedding_v3,
                        input=query
                    )
                    if res.status_code == 200:
                        return [eb['embedding'] for eb in res.output['embeddings']][0]
                    else:
                        raise ValueError(f'embedding error: {res}')
                
                def cosine_similarity(vec1, vec2):
                    '''计算余弦相似度'''
                    vec1 = np.array(vec1)
                    vec2 = np.array(vec2)
                    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                
                # 数据库连接配置
                db_config = {
                    'host': os.getenv('OB_URL'),
                    'port': 3306,
                    'user': os.getenv('OB_USER'),
                    'password': os.getenv('OB_PWD'),
                    'database': os.getenv('OB_DB_NAME'),
                    'charset': 'utf8mb4'
                }
                
                connection = pymysql.connect(**db_config)
                cursor = connection.cursor()
                
                # 如果没有指定product_id，默认使用产品ID 1（或从上下文中获取）
                if product_id is None:
                    product_id = 1  # 目前只有产品1有详细文档
                
                logger.info(f"🔍 [调试] 产品详细信息检索 - 产品ID: {product_id}")
                logger.info(f"🔍 [调试] 产品详细信息检索 - 查询文本: {query_text}")
                
                # 使用单一SQL查询获取产品信息和所有文档分块
                cursor.execute('''
                    SELECT 
                        sd.id, sd.name, sd.description, sd.material, sd.style, sd.price, 
                        sd.size, sd.color, sd.brand, sd.features, sd.dimensions, 
                        sd.promotion_policy, sd.image_url,
                        spd.chunk_id, spd.chunk_title, spd.chunk_content, spd.chunk_vector
                    FROM sofa_demo_v2 sd
                    LEFT JOIN sofa_product_docs spd ON sd.id = spd.product_id  
                    WHERE sd.id = %s
                ''', (product_id,))
                
                rows = cursor.fetchall()
                
                if not rows:
                    return {"error": f"未找到产品ID为{product_id}的产品"}
                
                # 处理查询结果 - 第一行包含产品基本信息
                first_row = rows[0]
                basic_info = {
                    "id": first_row[0],
                    "name": first_row[1],
                    "description": first_row[2],
                    "material": first_row[3],
                    "style": first_row[4],
                    "price": first_row[5],
                    "size": first_row[6],
                    "color": first_row[7],
                    "brand": first_row[8],
                    "features": first_row[9],
                    "dimensions": first_row[10],
                    "promotion_policy": json.loads(first_row[11]) if first_row[11] else {},
                    "image_url": first_row[12]
                }
                
                # 如果有查询文本，进行语义检索
                relevant_chunks = []
                if query_text.strip():
                    # 生成查询向量
                    query_embedding = text_embedding(query_text)
                    
                    # 计算所有分块的相似度
                    chunk_similarities = []
                    for row in rows:
                        chunk_id, chunk_title, chunk_content, chunk_vector_json = row[13:17]
                        if chunk_id and chunk_vector_json:  # 确保有分块数据
                            try:
                                chunk_vector = json.loads(chunk_vector_json)
                                similarity = cosine_similarity(query_embedding, chunk_vector)
                                chunk_similarities.append({
                                    "chunk_id": chunk_id,
                                    "chunk_title": chunk_title,
                                    "chunk_content": chunk_content,
                                    "similarity": similarity
                                })
                            except (json.JSONDecodeError, ValueError) as e:
                                logger.warning(f"解析分块向量失败: {e}")
                                continue
                    
                    # 按相似度排序并取前3个
                    chunk_similarities.sort(key=lambda x: x["similarity"], reverse=True)
                    relevant_chunks = chunk_similarities[:3]
                    
                    logger.info(f"📊 [调试] 产品详细信息检索 - 找到 {len(relevant_chunks)} 个相关分块")
                    for i, chunk in enumerate(relevant_chunks):
                        logger.info(f"📊 [调试] 分块{i+1}: {chunk['chunk_title']} (相似度: {chunk['similarity']:.4f})")
                
                cursor.close()
                connection.close()
                
                return {
                    "product_basic_info": basic_info,
                    "relevant_chunks": relevant_chunks,
                    "query_text": query_text
                }
                
            except Exception as e:
                logger.error(f"产品详细信息检索异常: {e}")
                return {"error": f"检索失败: {str(e)}"}
        
        return retrieve_product_details
    
    def _identify_intent(self, state: ConversationState) -> tuple:
        """使用 LLM 识别用户意图，返回 (intent, product_id)"""
        if not state["messages"]:
            return IntentType.OTHER.value, None
        
        last_message = state["messages"][-1]
        if not isinstance(last_message, HumanMessage):
            return IntentType.OTHER.value, None
        
        user_input = last_message.content
        if not user_input:
            return IntentType.OTHER.value, None
        
        # 构建对话上下文，包含推荐产品信息
        context_messages = state["messages"][-4:] if len(state["messages"]) > 4 else state["messages"][:-1]
        conversation_context = ""
        
        if context_messages:
            context_lines = []
            for msg in context_messages:
                msg_content = msg.content if msg.content else ""
                if isinstance(msg, HumanMessage):
                    context_lines.append(f"用户: {msg_content}")
                elif isinstance(msg, AIMessage):
                    context_lines.append(f"助手: {msg_content[:200]}...")  # 增加截断长度以包含更多产品信息
            conversation_context = "\n".join(context_lines)
        else:
            conversation_context = "无历史对话"
        
        # 添加推荐产品信息到上下文
        recommended_products = state.get("recommended_products", [])
        if recommended_products:
            product_info_lines = ["\n=== 最近推荐的产品信息 ==="]
            for i, product in enumerate(recommended_products, 1):
                product_info_lines.append(f"产品{i}: ID={product.get('id')}, 名称={product.get('name')}")
            conversation_context += "\n".join(product_info_lines)
        
        # 构建意图分类 prompt
        prompt = intent_classification_prompt.format(
            user_input=user_input,
            conversation_context=conversation_context
        )
        
        try:
            response = self.llm.chat(prompt)
            
            if response.status_code == 200:
                response_text = response.output.text
                
                # 处理可能的代码块包装
                if response_text.startswith("```json"):
                    response_text = response_text.replace("```json", "").replace("```", "").strip()
                elif response_text.startswith("```"):
                    response_text = response_text.replace("```", "").strip()
                
                # 解析 JSON 响应
                result = json.loads(response_text)
                intent = result.get("intent", IntentType.OTHER.value)
                confidence = result.get("confidence", 0.0)
                reason = result.get("reason", "")
                product_id = result.get("product_id", None)
                
                logger.info(f"LLM 意图识别结果: {intent} (置信度: {confidence:.2f}, 理由: {reason}, 产品ID: {product_id})")
                
                # 验证意图类型是否有效
                valid_intents = [
                    IntentType.NORMAL_CHAT.value, 
                    IntentType.PRODUCT_RECOMMENDATION.value, 
                    IntentType.PRODUCT_DETAIL_INQUIRY.value,
                    IntentType.OTHER.value
                ]
                
                # 如果意图是product_detail_inquiry但没有产品ID，则改为product_recommendation
                if intent == IntentType.PRODUCT_DETAIL_INQUIRY.value and not product_id:
                    logger.warning(f"产品详细信息咨询但无法推理产品ID，改为产品推荐意图")
                    intent = IntentType.PRODUCT_RECOMMENDATION.value
                    product_id = None
                
                if intent in valid_intents:
                    # 如果意图是product_detail_inquiry但没有产品ID，则改为product_recommendation
                    if intent == IntentType.PRODUCT_DETAIL_INQUIRY.value and not product_id:
                        logger.warning(f"产品详细信息咨询但无法推理产品ID，改为产品推荐意图")
                        return IntentType.PRODUCT_RECOMMENDATION.value, None
                    
                    return intent, product_id
                else:
                    logger.warning(f"无效的意图类型: {intent}, 默认为 other")
                    return IntentType.OTHER.value, None
            else:
                logger.error(f"LLM 意图识别失败: {response}")
                return IntentType.OTHER.value, None
                
        except json.JSONDecodeError as e:
            logger.error(f"意图分类 JSON 解析失败: {e}")
            return IntentType.OTHER.value, None
        except Exception as e:
            logger.error(f"意图识别异常: {e}")
            return IntentType.OTHER.value, None
    
    def _analyze_intent(self, state: ConversationState) -> ConversationState:
        """分析用户意图节点"""
        intent, product_id = self._identify_intent(state)
        state["intent"] = intent
        state["inferred_product_id"] = product_id
        
        # 保存最后一条用户消息
        if state["messages"]:
            last_message = state["messages"][-1]
            if isinstance(last_message, HumanMessage):
                state["last_user_message"] = last_message.content
        
        logger.info(f"识别到的意图: {intent}, 推理的产品ID: {product_id}")
        return state
    
    def _normal_chat(self, state: ConversationState) -> ConversationState:
        """处理普通聊天节点"""
        user_message = state["last_user_message"] or ""
        
        prompt = normal_chat_prompt.format(user_content=user_message)
        response = self.llm.chat(prompt)
        
        if response.status_code == 200:
            ai_message = AIMessage(content=response.output.text)
            state["messages"].append(ai_message)
        else:
            error_message = AIMessage(content="抱歉，我暂时无法处理您的请求，请稍后再试。")
            state["messages"].append(error_message)
        
        return state
    
    def _extract_conditions(self, state: ConversationState) -> ConversationState:
        """提取产品条件节点"""
        user_message = state["last_user_message"] or ""
        
        # 调用提取工具
        extract_tool = self.tools[0]  # extract_conditions
        conditions = extract_tool.invoke({"user_message": user_message})
        
        state["extracted_conditions"] = conditions
        logger.info(f"提取的条件: {conditions}")
        return state
    
    def _retrieve_product_details(self, state: ConversationState) -> ConversationState:
        """检索产品详细信息节点"""
        user_message = state["last_user_message"] or ""
        product_id = state.get("inferred_product_id")
        
        # 如果没有推理出产品ID，设置错误信息并返回
        if not product_id:
            error_message = {
                "error": "无法确定要查询的具体产品，请明确指定产品ID或产品名称"
            }
            state["product_detail_results"] = error_message
            logger.warning("没有推理出产品ID，无法检索产品详细信息")
            return state
        
        # 调用产品详细信息检索工具
        detail_tool = self.tools[2]  # retrieve_product_details
        detail_results = detail_tool.invoke({
            "product_id": product_id,
            "query_text": user_message
        })
        
        state["product_detail_results"] = detail_results
        logger.info(f"检索产品ID {product_id} 的详细信息完成")
        return state
    
    def _respond_product_details(self, state: ConversationState) -> ConversationState:
        """生成产品详细信息回复节点"""
        detail_results = state.get("product_detail_results", {})
        user_message = state["last_user_message"] or ""
        
        if "error" in detail_results:
            error_message = AIMessage(content=f"抱歉，{detail_results['error']}，请稍后再试。")
            state["messages"].append(error_message)
            return state
        
        # 格式化产品详细信息回复
        basic_info = detail_results.get("product_basic_info", {})
        relevant_chunks = detail_results.get("relevant_chunks", [])
        
        # 构建回复内容
        response_parts = []
        
        # 1. 产品基本信息
        response_parts.append(f"## 📋 {basic_info.get('name', '产品')} - 详细信息")
        response_parts.append("")
        response_parts.append(f"**🏷️ 基本信息:**")
        response_parts.append(f"- **材质**: {basic_info.get('material', '未知')}")
        response_parts.append(f"- **风格**: {basic_info.get('style', '未知')}")
        response_parts.append(f"- **价格**: ¥{basic_info.get('price', '未知')}")
        response_parts.append(f"- **尺寸**: {basic_info.get('size', '未知')}")
        response_parts.append(f"- **颜色**: {basic_info.get('color', '未知')}")
        response_parts.append(f"- **品牌**: {basic_info.get('brand', '未知')}")
        response_parts.append("")
        
        # 2. 如果有相关的文档分块，添加详细信息
        if relevant_chunks:
            response_parts.append(f"**📖 针对您的咨询「{user_message}」，为您提供以下详细信息:**")
            response_parts.append("")
            
            for i, chunk in enumerate(relevant_chunks, 1):
                response_parts.append(f"### {i}. {chunk['chunk_title']}")
                response_parts.append("")
                
                # 提取chunk内容的关键部分（前500个字符）
                content = chunk['chunk_content']
                if len(content) > 500:
                    content = content[:500] + "..."
                
                response_parts.append(content)
                response_parts.append("")
                response_parts.append(f"*（相关度: {chunk['similarity']:.2%}）*")
                response_parts.append("")
                response_parts.append("---")
                response_parts.append("")
        
        # 3. 添加进一步咨询提示
        response_parts.append("**💡 如需了解更多信息，您可以询问:**")
        response_parts.append("- 产品的材质工艺详情")
        response_parts.append("- 尺寸规格和空间搭配建议") 
        response_parts.append("- 保养维护方法")
        response_parts.append("- 售后服务政策")
        response_parts.append("- 舒适体验和功能特性")
        
        response_text = "\n".join(response_parts)
        ai_message = AIMessage(content=response_text)
        state["messages"].append(ai_message)
        
        return state
    
    def _has_conditions(self, state: ConversationState) -> str:
        """判断是否有筛选条件"""
        conditions = state.get("extracted_conditions", {})
        image_path = state.get("uploaded_image_path")
        
        # 如果有图片，即使没有文本条件也认为有条件，因为图片本身就是条件
        if image_path:
            logger.info(f"🖼️ [调试] 检测到上传图片，将进行图片检索: {image_path}")
            return "has_conditions"
        
        # 检查是否有文本提取的条件
        if conditions and any(conditions.values()):
            logger.info(f"📝 [调试] 检测到文本条件，将进行文本检索: {conditions}")
            return "has_conditions"
        else:
            logger.info(f"❓ [调试] 未检测到任何条件，将引导用户")
            return "no_conditions"
    
    def _guide_user(self, state: ConversationState) -> ConversationState:
        """引导用户提供更多信息节点"""
        user_message = state["last_user_message"] or ""
        
        guide_message = """我很乐意为您推荐合适的沙发产品！为了给您更精准的推荐，您可以告诉我：

1. 您偏好的材质（如布艺、真皮等）
2. 喜欢的风格（如现代简约、北欧、美式等）
3. 预算范围（如5000-10000元）
4. 尺寸需求（如单人、双人、三人沙发）
5. 所在地区（用于售后服务）

您也可以上传一张喜欢的沙发图片，我可以为您找到相似风格的产品。

请告诉我您的具体需求吧！"""
        
        ai_message = AIMessage(content=guide_message)
        state["messages"].append(ai_message)
        return state
    
    def _retrieve_products(self, state: ConversationState) -> ConversationState:
        """检索产品节点"""
        conditions = state.get("extracted_conditions", {})
        user_message = state["last_user_message"] or ""
        image_path = state.get("uploaded_image_path")
        
        # 从提取的条件中获取搜索查询文本
        search_query = conditions.get("search_query", "") or user_message
        
        # 根据是否有图片选择搜索类型
        if image_path:
            search_type = "hybrid" if search_query.strip() else "image"
            logger.info(f"🖼️ [调试] 使用图片检索，搜索类型: {search_type}")
        else:
            search_type = "text"
            logger.info(f"📝 [调试] 使用文本检索")
        
        # 移除 search_query 字段避免传递给数据库过滤
        filters = {k: v for k, v in conditions.items() if k != "search_query"}
        
        # 调用检索工具
        retrieve_tool = self.tools[1]  # retrieve_products
        results = retrieve_tool.invoke({
            "search_type": search_type,
            "query": search_query,
            "image_path": image_path,
            "filters": filters
        })
        
        state["search_results"] = results
        logger.info(f"检索到 {len(results)} 个产品")
        return state
    
    def _recommend_products(self, state: ConversationState) -> ConversationState:
        """推荐产品节点"""
        results = state.get("search_results", [])
        user_message = state["last_user_message"] or ""
        
        # 格式化产品信息
        if results:
            products_info = []
            for i, product in enumerate(results[:3], 1):  # 最多推荐3个产品
                product_str = f"""产品{i}（ID: {product['id']}）：{product['name']}
- 材质：{product['material']}
- 风格：{product['style']}
- 价格：{product['price']}元
- 尺寸：{product['size']}
- 颜色：{product['color']}
- 品牌：{product['brand']}
- 特色功能：{product['features']}
- 具体尺寸：{product['dimensions']}
- 优惠政策：{json.dumps(product['promotion_policy'], ensure_ascii=False)}
- 相似度评分：{product['similarity']:.4f}
"""
                products_info.append(product_str)
            
            option_products = "\n\n".join(products_info)
        else:
            option_products = "未找到符合条件的产品"
        
        # 生成推荐回复
        prompt = recommendation_prompt.format(
            option_products=option_products,
            user_content=user_message
        )
        response = self.llm.chat(prompt)
        
        if response.status_code == 200:
            ai_message = AIMessage(content=response.output.text)
        else:
            ai_message = AIMessage(content="抱歉，推荐系统暂时出现问题，请稍后再试。")
        
        state["messages"].append(ai_message)
        
        # 保存推荐产品信息到状态中，供前端显示图片使用
        state["recommended_products"] = results[:3] if results else []
        
        return state
    
    def _route_intent(self, state: ConversationState) -> str:
        """路由用户意图"""
        intent = state.get("intent", IntentType.OTHER.value)
        
        if intent == IntentType.NORMAL_CHAT.value:
            return "normal_chat"
        elif intent == IntentType.PRODUCT_RECOMMENDATION.value:
            return "product_recommendation"
        elif intent == IntentType.PRODUCT_DETAIL_INQUIRY.value:
            return "product_detail_inquiry"
        else:
            return "other"
    
    def _handle_other(self, state: ConversationState) -> ConversationState:
        """处理其他意图节点"""
        user_message = state["last_user_message"] or ""
        
        response_text = """我是您的专业沙发产品咨询助手。我可以帮您：

1. 🛋️ 推荐合适的沙发产品
2. 📝 了解不同材质和风格的特点
3. 💰 提供价格和优惠信息
4. 📍 查询售后服务点
5. 🔍 根据图片找相似产品

请告诉我您想了解什么，我会尽力为您提供专业的建议！"""
        
        ai_message = AIMessage(content=response_text)
        state["messages"].append(ai_message)
        return state
    
    def _build_workflow(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        workflow = StateGraph(ConversationState)
        
        # 添加节点
        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("normal_chat", self._normal_chat)
        workflow.add_node("extract_conditions", self._extract_conditions)
        workflow.add_node("guide_user", self._guide_user)
        workflow.add_node("retrieve_products", self._retrieve_products)
        workflow.add_node("recommend_products", self._recommend_products)
        workflow.add_node("retrieve_product_details", self._retrieve_product_details)
        workflow.add_node("respond_product_details", self._respond_product_details)
        workflow.add_node("handle_other", self._handle_other)
        
        # 设置入口点
        workflow.set_entry_point("analyze_intent")
        
        # 添加条件路由
        workflow.add_conditional_edges(
            "analyze_intent",
            self._route_intent,
            {
                "normal_chat": "normal_chat",
                "product_recommendation": "extract_conditions",
                "product_detail_inquiry": "retrieve_product_details",
                "other": "handle_other"
            }
        )
        
        workflow.add_conditional_edges(
            "extract_conditions",
            self._has_conditions,
            {
                "has_conditions": "retrieve_products",
                "no_conditions": "guide_user"
            }
        )
        
        workflow.add_edge("retrieve_products", "recommend_products")
        workflow.add_edge("retrieve_product_details", "respond_product_details")
        
        # 设置终点
        workflow.add_edge("normal_chat", END)
        workflow.add_edge("guide_user", END)
        workflow.add_edge("recommend_products", END)
        workflow.add_edge("respond_product_details", END)
        workflow.add_edge("handle_other", END)
        
        return workflow

    def chat(self, user_input: str, conversation_history: Optional[List[Dict]] = None, image_path: Optional[str] = None) -> str:
        """
        与用户进行对话
        
        Args:
            user_input: 用户输入
            conversation_history: 历史对话记录
            image_path: 上传的图片路径
            
        Returns:
            助手回复
        """
        # 构建初始状态
        messages = []
        
        # 添加历史对话
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        # 添加当前用户输入
        messages.append(HumanMessage(content=user_input))
        
        initial_state = ConversationState(
            messages=messages,
            intent=None,
            extracted_conditions=None,
            search_results=None,
            last_user_message=user_input,
            uploaded_image_path=image_path,
            recommended_products=None,
            product_detail_results=None,
            inferred_product_id=None
        )
        
        # 运行工作流
        try:
            result = self.app.invoke(initial_state)
            
            # 获取最后一条助手消息
            for message in reversed(result["messages"]):
                if isinstance(message, AIMessage):
                    return message.content
            
            return "抱歉，我暂时无法处理您的请求。"
            
        except Exception as e:
            logger.error(f"对话处理异常: {e}")
            return "抱歉，系统出现了问题，请稍后再试。"
    
    def chat_stream(self, user_input: str, conversation_history: Optional[List[Dict]] = None, image_path: Optional[str] = None):
        """
        流式对话接口，逐字符返回AI回复
        
        Args:
            user_input: 用户输入
            conversation_history: 历史对话记录
            image_path: 上传的图片路径
            
        Yields:
            逐字符的AI回复和意图信息
        """
        # 构建初始状态
        messages = []
        
        # 添加历史对话
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        # 添加当前用户输入
        messages.append(HumanMessage(content=user_input))
        
        initial_state = ConversationState(
            messages=messages,
            intent=None,
            extracted_conditions=None,
            search_results=None,
            last_user_message=user_input,
            uploaded_image_path=image_path,
            recommended_products=None,
            product_detail_results=None,
            inferred_product_id=None
        )
        
        try:
            # 运行工作流获取完整回复
            result = self.app.invoke(initial_state)
            intent = result.get("intent", "other")
            recommended_products = result.get("recommended_products", [])
            
            # 获取最后一条助手消息
            full_response = ""
            for message in reversed(result["messages"]):
                if isinstance(message, AIMessage):
                    full_response = message.content
                    break
            
            if not full_response:
                full_response = "抱歉，我暂时无法处理您的请求。"
            
            # 先返回意图信息
            yield {"type": "intent", "content": intent}
            
            # 如果有推荐产品，先返回产品信息
            if recommended_products:
                yield {"type": "products", "content": recommended_products}
            
            # 逐字符流式输出
            import time
            for char in full_response:
                yield {"type": "content", "content": char}
                time.sleep(0.02)  # 控制输出速度，可调整
                
        except Exception as e:
            logger.error(f"流式对话处理异常: {e}")
            error_msg = "抱歉，系统出现了问题，请稍后再试。"
            yield {"type": "intent", "content": "other"}
            for char in error_msg:
                yield {"type": "content", "content": char}
                time.sleep(0.02)
    
    def get_conversation_state(self, user_input: str, conversation_history: Optional[List[Dict]] = None, image_path: Optional[str] = None) -> Dict:
        """
        获取完整的对话状态（用于调试）
        
        Args:
            user_input: 用户输入
            conversation_history: 历史对话记录
            image_path: 上传的图片路径
            
        Returns:
            完整的对话状态
        """
        # 构建初始状态
        messages = []
        
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=user_input))
        
        initial_state = ConversationState(
            messages=messages,
            intent=None,
            extracted_conditions=None,
            search_results=None,
            last_user_message=user_input,
            uploaded_image_path=image_path,
            recommended_products=None,
            product_detail_results=None,
            inferred_product_id=None
        )
        
        result = self.app.invoke(initial_state)
        return result
