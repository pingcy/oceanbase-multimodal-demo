# 数据库初始化指南

本目录包含了 OceanBase 多模态产品推荐系统的数据库初始化脚本。

## 📋 脚本说明

### 1. 环境验证脚本 (`test_environment.py`)
- **用途**: 验证环境配置是否正确
- **功能**: 
  - 检查必要的环境变量
  - 测试 OceanBase 数据库连接
  - 验证 DashScope API 可用性
  - 检查向量功能支持

### 2. 数据库初始化脚本 (`init_database.py`)
- **用途**: 完整的数据库初始化
- **功能**:
  - 创建 `sofa_demo_v2` 产品表
  - 创建 `sofa_product_docs` 文档表
  - 创建向量索引
  - 插入测试数据
  - 验证数据完整性

## 🚀 使用步骤

### 第一步：配置环境变量

1. 复制环境配置模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入实际配置：
```bash
# OceanBase 数据库配置
OB_URL="your-oceanbase-cluster-url"
OB_USER="your-username"  
OB_DB_NAME="your-database-name"
OB_PWD="your-password"

# 通义千问 API 配置
DASHSCOPE_API_KEY="your-dashscope-api-key"
```

### 第二步：验证环境

运行环境验证脚本：
```bash
python test_environment.py
```

如果所有测试通过，将看到：
```
🎉 所有测试通过! 环境配置正确
💡 现在可以运行 python init_database.py 初始化数据库
```

### 第三步：初始化数据库

运行数据库初始化脚本：
```bash
python init_database.py
```

脚本将按以下步骤执行：
1. 📊 创建数据表结构
2. 💾 插入测试数据
3. 🔍 验证数据完整性

## 🗄️ 数据表结构

### sofa_demo_v2 (沙发产品主表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 产品ID (主键) |
| name | VARCHAR(255) | 沙发名称 |
| description | LONGTEXT | 产品描述 |
| material | VARCHAR(100) | 材质 |
| style | VARCHAR(100) | 风格 |
| price | DECIMAL(10,2) | 价格 |
| size | VARCHAR(100) | 尺寸规格 |
| color | VARCHAR(100) | 颜色 |
| brand | VARCHAR(100) | 品牌 |
| service_locations | VARCHAR(500) | 服务点位置 |
| features | VARCHAR(500) | 特色功能 |
| dimensions | VARCHAR(100) | 具体尺寸 |
| image_url | VARCHAR(500) | 产品图片URL |
| promotion_policy | JSON | 优惠政策 |
| description_vector | VECTOR(1024) | 描述向量 |
| image_vector | VECTOR(1024) | 图片向量 |

### sofa_product_docs (产品文档表)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 文档ID (主键) |
| product_id | INT | 关联的产品ID |
| chunk_id | VARCHAR(255) | 文档分块唯一标识 |
| chunk_title | VARCHAR(500) | 文档分块标题 |
| chunk_content | LONGTEXT | 文档分块内容 |
| chunk_vector | VECTOR(1024) | 文档分块向量 |

## 📊 测试数据说明

### 产品数据 (5条记录)
1. 北欧简约三人布艺沙发
2. 现代简约真皮沙发
3. 美式复古布艺组合沙发
4. 中式红木沙发
5. 小户型双人布艺沙发

### 文档数据 (5条记录)
为产品ID=1 (北欧简约三人布艺沙发) 提供详细文档：
1. 材质工艺详情
2. 舒适体验设计
3. 保养维护指南
4. 空间搭配建议
5. 售后服务政策

## 🔧 故障排除

### 常见问题

1. **环境变量未配置**
   ```
   ❌ 缺少必要的环境变量: OB_URL, DASHSCOPE_API_KEY
   ```
   **解决方案**: 检查 `.env` 文件是否存在且配置正确

2. **数据库连接失败**
   ```
   ❌ 数据库连接失败: (2003, "Can't connect to MySQL server")
   ```
   **解决方案**: 
   - 检查 OceanBase 地址和端口
   - 验证用户名和密码
   - 确认数据库名称存在

3. **DashScope API 失败**
   ```
   ❌ DashScope API 测试失败: Invalid API key
   ```
   **解决方案**: 检查 API 密钥是否正确且有效

4. **向量索引创建失败**
   ```
   ⚠️ 创建向量索引失败: Unknown storage engine 'vsag'
   ```
   **解决方案**: 确认 OceanBase 版本支持向量功能

### 调试技巧

1. **查看详细日志**: 脚本会输出详细的执行日志
2. **单独测试**: 先运行 `test_environment.py` 验证基础配置
3. **分步执行**: 可以注释掉部分代码分步调试
4. **手动验证**: 使用 MySQL 客户端连接数据库查看结果

## 📱 验证结果

初始化完成后，可以通过以下方式验证：

### 1. 查看表结构
```sql
DESCRIBE sofa_demo_v2;
DESCRIBE sofa_product_docs;
```

### 2. 查看数据条数
```sql
SELECT COUNT(*) FROM sofa_demo_v2;
SELECT COUNT(*) FROM sofa_product_docs;
```

### 3. 测试向量检索
```sql
-- 查看向量数据
SELECT id, name, LENGTH(description_vector) as vector_len 
FROM sofa_demo_v2 LIMIT 3;
```

### 4. 测试应用功能
```bash
# 测试检索工具
python -c "from srd.tools.retrieval_tool import SofaRetrievalTool; tool = SofaRetrievalTool(); print(tool.search_by_text('北欧沙发'))"

# 启动Web界面
streamlit run conversation_ui.py
```

## 💡 后续使用

数据库初始化完成后，您可以：

1. **启动推荐系统**: `streamlit run conversation_ui.py`
2. **开发调试**: 使用各种检索和推荐功能
3. **添加数据**: 通过脚本或手动添加更多产品数据
4. **性能优化**: 根据实际使用情况调整索引和配置

## 🤝 获取帮助

如遇到问题：
1. 查看日志输出的详细错误信息
2. 检查 [OceanBase 向量功能文档](https://www.oceanbase.com/docs)
3. 参考项目 README.md 的故障排除部分
4. 提交 GitHub Issue 获取支持
