import streamlit as st
import logging
from typing import List, Dict, Generator, Optional
import traceback
import time
import os
import tempfile
from PIL import Image
from srd.agents.conversation_agent import SofaConversationAgent

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title="沙发智能咨询助手",
    page_icon="🛋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        max-width: 80%;
    }
    .user-message {
        background-color: #E3F2FD;
        margin-left: auto;
        border: 1px solid #2196F3;
    }
    .assistant-message {
        background-color: #F5F5F5;
        margin-right: auto;
        border: 1px solid #9E9E9E;
    }
    .intent-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 5px;
        font-size: 0.8rem;
        font-weight: bold;
        margin: 0.2rem;
    }
    .intent-normal {
        background-color: #E8F5E8;
        color: #2E7D32;
    }
    .intent-product {
        background-color: #FFF3E0;
        color: #F57C00;
    }
    .intent-other {
        background-color: #F3E5F5;
        color: #7B1FA2;
    }
    .error-message {
        background-color: #FFEBEE;
        color: #C62828;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #EF5350;
    }
    .streaming-message {
        background-color: #F5F5F5;
        margin-right: auto;
        border: 1px solid #9E9E9E;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        max-width: 80%;
        min-height: 3rem;
    }
    .typing-indicator {
        animation: typing 1.5s infinite;
    }
    @keyframes typing {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    .uploaded-image {
        max-width: 200px;
        max-height: 200px;
        border-radius: 10px;
        margin: 0.5rem 0;
        border: 2px solid #2196F3;
    }
    .image-upload-area {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .product-image {
        max-width: 120px;
        max-height: 120px;
        border-radius: 8px;
        object-fit: cover;
        margin: 0.5rem auto;
        border: 1px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem;
        background-color: #fafafa;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_agent():
    """初始化对话Agent（缓存）"""
    try:
        agent = SofaConversationAgent(table_name="sofa_demo_v2", topk=5)
        return agent, None
    except Exception as e:
        error_msg = f"Agent初始化失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return None, error_msg

def save_uploaded_image(uploaded_file) -> Optional[str]:
    """保存上传的图片并返回路径"""
    if uploaded_file is not None:
        try:
            # 创建临时目录
            temp_dir = os.path.join(os.getcwd(), "temp_images")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 保存文件
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            logger.info(f"🖼️ [调试] 图片已保存: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            return None
    return None

def display_message(role: str, content: str, intent: str = None, image_path: str = None):
    """显示聊天消息"""
    if role == "user":
        # 显示用户消息
        user_content = f"""
        <div class="chat-message user-message">
            <strong>👤 用户:</strong><br>
            {content}
        </div>
        """
        st.markdown(user_content, unsafe_allow_html=True)
        
        # 如果有图片，单独显示图片
        if image_path and os.path.exists(image_path):
            st.image(
                image_path, 
                caption="上传的图片", 
                width=200,
                use_column_width=False
            )
    else:
        intent_class = ""
        intent_text = ""
        if intent:
            if intent == "normal_chat":
                intent_class = "intent-normal"
                intent_text = "💬 普通聊天"
            elif intent == "product_recommendation":
                intent_class = "intent-product"
                intent_text = "🛋️ 产品推荐"
            else:
                intent_class = "intent-other"
                intent_text = "❓ 其他意图"
        
        intent_badge = f'<span class="intent-badge {intent_class}">{intent_text}</span>' if intent else ""
        
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>🤖 助手:</strong> {intent_badge}<br>
            {content}
        </div>
        """, unsafe_allow_html=True)

def stream_response(agent, user_input: str, conversation_history: List[Dict], image_path: Optional[str] = None) -> tuple:
    """流式获取AI回复"""
    try:
        # 创建流式响应的占位符
        message_placeholder = st.empty()
        products_placeholder = st.empty()
        full_response = ""
        intent = "other"
        recommended_products = []
        
        # 显示初始的流式消息框
        with message_placeholder.container():
            st.markdown("""
            <div class="streaming-message">
                <strong>🤖 助手:</strong> <span class="typing-indicator">正在思考...</span><br>
                <span id="streaming-content"></span>
            </div>
            """, unsafe_allow_html=True)
        
        # 获取流式回复
        for chunk in agent.chat_stream(user_input, conversation_history, image_path):
            if chunk["type"] == "intent":
                intent = chunk["content"]
            elif chunk["type"] == "products":
                recommended_products = chunk["content"]
                # 显示推荐产品图片
                if recommended_products:
                    with products_placeholder.container():
                        st.markdown("### 🛋️ 推荐产品")
                        
                        # 使用更紧凑的布局显示产品
                        for i, product in enumerate(recommended_products):
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                # 显示产品图片（如果有URL）
                                if product.get('image_url'):
                                    try:
                                        # 处理图片路径
                                        image_path = product['image_url']
                                        if not image_path.startswith('/') and not image_path.startswith('http'):
                                            # 相对路径，转换为绝对路径
                                            import os
                                            image_path = os.path.join(os.getcwd(), image_path)
                                        
                                        st.image(
                                            image_path,
                                            width=120,
                                            use_container_width=False
                                        )
                                    except Exception as e:
                                        st.write("📷 图片加载失败")
                                        logger.warning(f"无法加载图片 {product['image_url']}: {e}")
                                else:
                                    st.write("📷 暂无图片")
                            
                            with col2:
                                # 显示产品信息
                                st.markdown(f"**{product['name']}**")
                                st.write(f"💰 **价格**: ¥{product['price']}")
                                st.write(f"🧵 **材质**: {product['material']}")
                                st.write(f"🎨 **风格**: {product['style']}")
                                st.write(f"🌈 **颜色**: {product['color']}")
                                
                            st.markdown("---")  # 分隔线
            elif chunk["type"] == "content":
                full_response += chunk["content"]
                
                # 更新显示
                intent_class = ""
                intent_text = ""
                if intent == "normal_chat":
                    intent_class = "intent-normal"
                    intent_text = "💬 普通聊天"
                elif intent == "product_recommendation":
                    intent_class = "intent-product"
                    intent_text = "🛋️ 产品推荐"
                else:
                    intent_class = "intent-other"
                    intent_text = "❓ 其他意图"
                
                intent_badge = f'<span class="intent-badge {intent_class}">{intent_text}</span>'
                
                with message_placeholder.container():
                    st.markdown(f"""
                    <div class="streaming-message">
                        <strong>🤖 助手:</strong> {intent_badge}<br>
                        {full_response}<span class="typing-indicator">▋</span>
                    </div>
                    """, unsafe_allow_html=True)
        
        # 最终显示完整消息（去掉打字指示器）
        with message_placeholder.container():
            display_message("assistant", full_response, intent)
        
        return full_response, intent, None
        
    except Exception as e:
        error_msg = f"流式对话处理失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return None, None, error_msg

def main():
    """主界面"""
    # 页面标题
    st.markdown('<h1 class="main-header">🛋️ 沙发智能咨询助手</h1>', unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        st.markdown("## 💡 功能介绍")
        st.markdown("""
        - 🔍 智能意图识别
        - 🛋️ 个性化产品推荐
        - 💬 多轮对话支持
        - 📊 上下文理解
        - 🎯 精准条件提取
        - ⚡ 实时流式回复
        - 🖼️ 图片搜索支持
        """)
        
        st.markdown("## 🚀 使用指南")
        st.markdown("""
        1. 输入您的需求或上传沙发图片
        2. 系统智能识别意图
        3. 获得专业推荐
        4. 继续深入咨询
        """)
        
        # 图片上传区域
        st.markdown("## 📷 图片上传")
        uploaded_file = st.file_uploader(
            "上传沙发图片，帮助找到相似产品",
            type=['png', 'jpg', 'jpeg'],
            help="支持PNG、JPG、JPEG格式"
        )
        
        # 存储上传的图片路径
        if uploaded_file is not None:
            if 'current_image_path' not in st.session_state or st.session_state.get('current_image_name') != uploaded_file.name:
                image_path = save_uploaded_image(uploaded_file)
                st.session_state.current_image_path = image_path
                st.session_state.current_image_name = uploaded_file.name
                
            # 显示上传的图片
            if st.session_state.get('current_image_path'):
                st.image(
                    st.session_state.current_image_path, 
                    caption="已上传的图片", 
                    width=200
                )
        else:
            # 清除图片状态
            if 'current_image_path' in st.session_state:
                del st.session_state.current_image_path
            if 'current_image_name' in st.session_state:
                del st.session_state.current_image_name
        
        # 清空对话按钮
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            # 清除图片状态
            if 'current_image_path' in st.session_state:
                del st.session_state.current_image_path
            if 'current_image_name' in st.session_state:
                del st.session_state.current_image_name
            st.rerun()
        
        # 显示对话统计
        if 'messages' in st.session_state:
            total_messages = len(st.session_state.messages)
            user_messages = len([m for m in st.session_state.messages if m['role'] == 'user'])
            st.markdown(f"""
            ## 📈 对话统计
            - 总消息数: {total_messages}
            - 用户消息: {user_messages}
            - 助手回复: {total_messages - user_messages}
            """)
    
    # 初始化Agent
    agent, init_error = init_agent()
    if agent is None:
        st.markdown(f"""
        <div class="error-message">
            ⚠️ 系统初始化失败<br>
            错误详情: {init_error}
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 初始化会话状态
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.conversation_history = []
    
    # 显示欢迎消息
    if not st.session_state.messages:
        welcome_msg = """👋 您好！我是您的专业沙发咨询助手。

我可以帮您：
• 🛋️ 推荐合适的沙发产品
• 📝 了解不同材质和风格特点  
• 💰 提供价格和优惠信息
• 🔍 根据您的需求精准筛选

请告诉我您想了解什么吧！"""
        
        display_message("assistant", welcome_msg)
    
    # 显示历史对话
    for message in st.session_state.messages:
        display_message(
            message["role"], 
            message["content"], 
            message.get("intent"),
            message.get("image_path")
        )
    
    # 用户输入框
    if prompt := st.chat_input("请输入您的问题..."):
        # 获取当前上传的图片路径
        current_image_path = st.session_state.get('current_image_path')
        
        # 添加用户消息到历史
        user_message = {
            "role": "user", 
            "content": prompt,
            "image_path": current_image_path
        }
        st.session_state.messages.append(user_message)
        st.session_state.conversation_history.append({
            "role": "user", 
            "content": prompt
        })
        
        # 显示用户消息
        display_message("user", prompt, image_path=current_image_path)
        
        # 流式获取和显示AI回复
        response, intent, error = stream_response(
            agent, 
            prompt, 
            st.session_state.conversation_history[:-1],  # 不包含当前消息
            current_image_path
        )
        
        if error:
            # 显示错误消息
            st.markdown(f"""
            <div class="error-message">
                抱歉，处理您的请求时出现了问题：<br>
                {error}
            </div>
            """, unsafe_allow_html=True)
            
            # 添加错误消息到历史
            error_message = {"role": "assistant", "content": f"抱歉，系统出现了问题：{error}"}
            st.session_state.messages.append(error_message)
            st.session_state.conversation_history.append(error_message)
        else:
            # 添加助手消息到历史
            assistant_message = {
                "role": "assistant", 
                "content": response,
                "intent": intent
            }
            st.session_state.messages.append(assistant_message)
            st.session_state.conversation_history.append({
                "role": "assistant", 
                "content": response
            })

if __name__ == "__main__":
    main()
