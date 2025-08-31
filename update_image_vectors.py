#!/usr/bin/env python3
"""
更新沙发产品的图片向量
使用真实产品图片生成image_vector并更新数据库
"""

import os
import sys
import json
from pathlib import Path
import dotenv
from tqdm import tqdm
import time

# 加载环境变量
dotenv.load_dotenv()

# 添加模块路径
sys.path.append(str(Path(__file__).parent))

from srd.tools.retrieval_tool import SofaRetrievalTool

class ImageVectorUpdater:
    def __init__(self, table_name: str = "sofa_demo_v2"):
        self.table_name = table_name
        self.tool = SofaRetrievalTool(
            table_name=table_name,
            topk=1,
            echo=False
        )
        self.images_dir = Path("images")
        
    def check_images(self):
        """检查图片文件是否存在"""
        print("🔍 检查图片文件...")
        missing_images = []
        
        for i in range(1, 11):
            image_path = self.images_dir / f"{i}.png"
            if not image_path.exists():
                missing_images.append(str(image_path))
            else:
                print(f"✅ 找到图片: {image_path}")
        
        if missing_images:
            print(f"❌ 缺少图片文件: {missing_images}")
            return False
        
        print("✅ 所有图片文件检查完成")
        return True
    
    def get_current_products(self):
        """获取当前数据库中的产品信息"""
        print("📋 获取产品信息...")
        
        query = f"SELECT id, name FROM {self.table_name} ORDER BY id"
        results = self.tool.client.perform_raw_text_sql(query)
        
        products = []
        if hasattr(results, 'fetchall'):
            rows = results.fetchall()
            for row in rows:
                products.append({
                    'id': row[0],
                    'name': row[1]
                })
        
        print(f"📊 找到 {len(products)} 个产品:")
        for product in products:
            print(f"   ID {product['id']}: {product['name']}")
            
        return products
    
    def update_image_vector(self, product_id: int, image_path: Path):
        """更新单个产品的图片向量"""
        try:
            print(f"\n🖼️  处理产品 ID {product_id}: {image_path}")
            
            # 生成图片向量
            print("   生成图片向量...")
            image_vector = self.tool.image_embedding(str(image_path))
            
            if image_vector is None:
                print(f"   ❌ 图片向量生成失败")
                return False
            
            print(f"   ✅ 图片向量生成成功 (维度: {len(image_vector)})")
            
            # 更新数据库
            print("   更新数据库...")
            update_query = f"""
                UPDATE {self.table_name} 
                SET image_vector = '{image_vector}' 
                WHERE id = {product_id}
            """
            
            self.tool.client.perform_raw_text_sql(update_query)
            print(f"   ✅ 数据库更新成功")
            
            return True
            
        except Exception as e:
            print(f"   ❌ 更新失败: {e}")
            return False
    
    def update_all_image_vectors(self):
        """更新所有产品的图片向量"""
        print("\n" + "="*60)
        print("🚀 开始更新所有产品的图片向量")
        print("="*60)
        
        # 检查图片文件
        if not self.check_images():
            return False
        
        # 获取产品信息
        products = self.get_current_products()
        
        if not products:
            print("❌ 没有找到任何产品")
            return False
        
        # 更新统计
        success_count = 0
        failed_count = 0
        
        print(f"\n🔄 开始更新 {len(products)} 个产品的图片向量...")
        
        # 使用进度条处理每个产品
        for product in tqdm(products, desc="更新图片向量"):
            product_id = product['id']
            image_path = self.images_dir / f"{product_id}.png"
            
            if not image_path.exists():
                print(f"\n❌ 产品 ID {product_id} 的图片不存在: {image_path}")
                failed_count += 1
                continue
            
            # 更新图片向量
            if self.update_image_vector(product_id, image_path):
                success_count += 1
                # 添加延迟避免API限流
                time.sleep(1)
            else:
                failed_count += 1
        
        # 输出结果统计
        print("\n" + "="*60)
        print("📊 更新结果统计")
        print("="*60)
        print(f"✅ 成功更新: {success_count} 个产品")
        print(f"❌ 更新失败: {failed_count} 个产品")
        print(f"📈 成功率: {success_count/(success_count+failed_count)*100:.1f}%")
        
        return success_count > 0
    
    def verify_updates(self):
        """验证更新结果"""
        print("\n" + "="*60)
        print("🔍 验证更新结果")
        print("="*60)
        
        # 检查image_vector字段是否已更新
        query = f"""
            SELECT id, name, 
                   CASE WHEN image_vector IS NOT NULL THEN 'Yes' ELSE 'No' END as has_image_vector
            FROM {self.table_name} 
            ORDER BY id
        """
        
        results = self.tool.client.perform_raw_text_sql(query)
        
        if hasattr(results, 'fetchall'):
            rows = results.fetchall()
            print("📋 产品图片向量状态:")
            for row in rows:
                status_icon = "✅" if row[2] == 'Yes' else "❌"
                print(f"   {status_icon} ID {row[0]}: {row[1]} - 图片向量: {row[2]}")
        
        # 测试图片搜索功能
        print("\n🧪 测试图片搜索功能...")
        try:
            test_image_path = self.images_dir / "1.png"
            if test_image_path.exists():
                results = self.tool.search_by_image(str(test_image_path))
                print(f"✅ 图片搜索测试成功，找到 {len(results)} 个相似产品")
                if results:
                    print(f"   最相似产品: {results[0]['name']} (相似度: {results[0]['similarity']:.4f})")
            else:
                print("❌ 测试图片不存在")
        except Exception as e:
            print(f"❌ 图片搜索测试失败: {e}")

def main():
    """主函数"""
    print("🖼️  沙发产品图片向量更新工具")
    print("使用真实产品图片生成并更新image_vector字段")
    
    # 检查环境变量
    required_env_vars = ["OB_URL", "OB_USER", "OB_DB_NAME", "DASHSCOPE_API_KEY"]
    for var in required_env_vars:
        if not os.getenv(var):
            print(f"❌ 缺少环境变量: {var}")
            return
    
    updater = ImageVectorUpdater()
    
    try:
        # 执行更新
        success = updater.update_all_image_vectors()
        
        if success:
            # 验证结果
            updater.verify_updates()
            print("\n🎉 图片向量更新完成！")
        else:
            print("\n❌ 图片向量更新失败")
            
    except Exception as e:
        print(f"\n💥 程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
