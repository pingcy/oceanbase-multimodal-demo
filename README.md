# OceanBase 多模态产品推荐系统

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OceanBase](https://img.shields.io/badge/OceanBase-Vector%20Database-green.svg)](https://www.oceanbase.com/)

🚀 **演示 OceanBase 向量数据库与多模态混合检索能力的Demo**

基于 OceanBase 向量数据库的智能产品推荐系统，展示自然语言 + 图像的混合检索能力。

## ✨ 主要功能

- **🗄️ 向量存储**: OceanBase 多模态向量数据存储和索引
- **🔍 混合检索**: 文本 + 图像的跨模态相似度搜索  
- **🤖 智能推荐**: 基于 AI 的个性化产品推荐
- **💬 对话交互**: 自然语言对话式查询界面

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/pingcy/oceanbase-multimodal-demo.git
cd oceanbase-multimodal-demo

# 安装依赖
uv venv
source .venv/bin/activate  
uv pip install -e .
```

### 2. 配置环境

复制并编辑环境配置：

```bash
cp .env.example .env
```

配置 OceanBase 和 API 信息：
```bash
# OceanBase 向量数据库配置
OB_URL="your-oceanbase-url"
OB_USER="your-username"  
OB_DB_NAME="your-database-name"
OB_PWD="your-password"

# 通义千问 API 配置
DASHSCOPE_API_KEY="your-dashscope-api-key"
```

### 3. 验证环境

```bash
# 验证配置是否正确
python test_environment.py
```

### 4. 初始化数据库

```bash
# 创建表结构并插入测试数据
python init_database.py
```

⚠️ **注意**: 初始化脚本包含演示用的测试数据，请根据实际需求修改 `init_database.py` 中的数据内容。

### 5. 启动系统

```bash
# Web 界面方式
streamlit run conversation_ui.py

# 命令行方式  
python conversation_ui.py
```

## 📊 数据说明

系统包含两个主要数据表：

- **sofa_demo_v2**: 产品主表，存储产品信息和向量数据
- **sofa_product_docs**: 产品文档表，支持详细信息的语义检索

测试数据包含 5 个沙发产品样本，可根据实际业务需求修改为其他类型产品。

详细的数据库初始化说明请参考：[DATABASE_INIT.md](DATABASE_INIT.md)

## 🔧 系统要求

- Python 3.10+
- OceanBase 数据库（支持向量功能）
- 通义千问 API 访问权限

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

💡 这是一个 OceanBase 向量数据库能力的演示项目，展示了多模态AI应用的技术实现。
