#!/bin/bash

# 沙发推荐系统启动脚本

echo "🛋️  启动沙发推荐系统..."

# 检查环境配置
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 配置文件"
    echo "💡 请先运行 './install.sh' 进行安装"
    exit 1
fi

# 检查是否安装了依赖
if [ ! -d ".venv" ] && [ ! -f "poetry.lock" ]; then
    echo "❌ 未安装依赖"
    echo "💡 请先运行 './install.sh' 进行安装"
    exit 1
fi

# 启动系统
echo "🚀 启动中..."
poetry run python cli.py
