#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 A股房地产资产查询界面 - 模块入口
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if __name__ == '__main__':
    # 直接运行模块时启动应用
    from run_ui import main
    main()