#!/bin/bash
# A股数据收集脚本启动器

echo "正在安装依赖包..."
pip install -r requirements.txt

echo "运行A股非经营性房地产资产数据收集脚本..."
python3 astock_real_estate_collector.py

echo "执行完成！"