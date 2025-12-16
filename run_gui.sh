#!/bin/bash
# A股数据收集器 - PyQt5 图形界面启动器

echo "========================================="
echo "  A股非经营性房地产数据收集器 GUI v3.0"
echo "========================================="
echo ""

# 检查依赖
echo "检查依赖包..."
if ! python3 -c "import PyQt5" 2>/dev/null; then
    echo "未检测到 PyQt5，正在安装依赖..."
    pip install -r requirements.txt
else
    echo "✓ 依赖包已就绪"
fi

echo ""
echo "正在启动图形界面..."
python3 astock_real_estate_collector_gui.py

echo ""
echo "程序已退出"
