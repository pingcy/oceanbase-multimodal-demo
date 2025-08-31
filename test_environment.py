#!/usr/bin/env python3
"""
数据库连接和环境验证脚本
用于在运行完整初始化前验证环境配置是否正确
"""

import os
import pymysql
import dashscope
from dotenv import load_dotenv

def test_environment():
    """测试环境配置"""
    print("🔍 正在验证环境配置...")
    
    # 加载环境变量
    load_dotenv()
    
    # 检查必要的环境变量
    required_vars = {
        'OB_URL': 'OceanBase 数据库地址',
        'OB_USER': 'OceanBase 用户名',
        'OB_DB_NAME': 'OceanBase 数据库名',
        'OB_PWD': 'OceanBase 密码',
        'DASHSCOPE_API_KEY': 'DashScope API 密钥'
    }
    
    missing_vars = []
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"{var} ({desc})")
        else:
            # 隐藏敏感信息
            if 'PWD' in var or 'KEY' in var:
                display_value = f"{value[:8]}***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
    
    if missing_vars:
        print("\n❌ 缺少以下环境变量:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 请检查 .env 文件配置")
        return False
    
    print("\n✅ 所有环境变量配置完整")
    return True

def test_database_connection():
    """测试数据库连接"""
    print("\n🔗 正在测试数据库连接...")
    
    try:
        # 解析数据库连接信息
        db_url = os.getenv('OB_URL', 'localhost:3306')
        if ':' in db_url:
            host, port = db_url.split(':')
            port = int(port)
        else:
            host = db_url
            port = 3306
        
        db_config = {
            'host': host,
            'port': port,
            'user': os.getenv('OB_USER'),
            'password': os.getenv('OB_PWD'),
            'database': os.getenv('OB_DB_NAME'),
            'charset': 'utf8mb4',
            'connect_timeout': 10
        }
        
        print(f"🌐 连接地址: {host}:{port}")
        print(f"👤 用户名: {db_config['user']}")
        print(f"🗄️ 数据库: {db_config['database']}")
        
        # 尝试连接
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        
        # 测试查询
        cursor.execute("SELECT VERSION(), DATABASE(), USER()")
        result = cursor.fetchone()
        
        print("\n✅ 数据库连接成功!")
        print(f"📊 数据库版本: {result[0]}")
        print(f"🗄️ 当前数据库: {result[1]}")
        print(f"👤 当前用户: {result[2]}")
        
        # 检查向量功能支持
        try:
            cursor.execute("SHOW VARIABLES LIKE '%vector%'")
            vector_vars = cursor.fetchall()
            if vector_vars:
                print("🧮 向量功能支持: ✅")
                for var in vector_vars:
                    print(f"   {var[0]} = {var[1]}")
            else:
                print("🧮 向量功能支持: ⚠️ 未检测到向量相关配置")
        except Exception:
            print("🧮 向量功能支持: ⚠️ 无法检测")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        print("\n💡 请检查:")
        print("   1. 数据库地址和端口是否正确")
        print("   2. 用户名和密码是否正确")
        print("   3. 数据库是否存在且可访问")
        print("   4. 网络连接是否正常")
        return False

def test_dashscope_api():
    """测试 DashScope API"""
    print("\n🤖 正在测试 DashScope API...")
    
    try:
        dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')
        
        # 测试文本嵌入API
        response = dashscope.TextEmbedding.call(
            model=dashscope.TextEmbedding.Models.text_embedding_v3,
            input="测试文本"
        )
        
        if response.status_code == 200:
            embedding = response.output['embeddings'][0]['embedding']
            print("✅ DashScope API 连接成功!")
            print(f"🧮 向量维度: {len(embedding)}")
            print(f"📊 API 状态: {response.status_code}")
            return True
        else:
            print(f"❌ DashScope API 调用失败: {response}")
            return False
            
    except Exception as e:
        print(f"❌ DashScope API 测试失败: {e}")
        print("\n💡 请检查:")
        print("   1. DASHSCOPE_API_KEY 是否正确")
        print("   2. API 密钥是否有效且未过期")
        print("   3. 网络是否能访问 DashScope 服务")
        return False

def main():
    """主函数"""
    print("="*60)
    print("🧪 OceanBase 多模态推荐系统 - 环境验证")
    print("="*60)
    
    all_tests_passed = True
    
    # 1. 测试环境变量
    if not test_environment():
        all_tests_passed = False
    
    # 2. 测试数据库连接
    if not test_database_connection():
        all_tests_passed = False
    
    # 3. 测试 DashScope API
    if not test_dashscope_api():
        all_tests_passed = False
    
    print("\n" + "="*60)
    if all_tests_passed:
        print("🎉 所有测试通过! 环境配置正确")
        print("💡 现在可以运行 python init_database.py 初始化数据库")
    else:
        print("❌ 部分测试失败，请修复配置后重试")
        print("💡 请检查 .env 文件配置和网络连接")
    print("="*60)
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    exit(main())
