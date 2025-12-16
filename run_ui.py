#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股非经营性房地产资产查询系统启动脚本
"""

import sys
import os
import logging

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    try:
        logger.info("开始启动A股非经营性房地产资产查询系统...")
        
        # 尝试导入PyQt5 UI
        logger.info("正在导入PyQt5...")
        from PyQt5.QtWidgets import QApplication
        logger.info("PyQt5导入成功")
        
        logger.info("正在导入UI模块...")
        from ui.real_estate_query_app import RealEstateQueryApp
        logger.info("UI模块导入成功")
        
        print("正在启动A股非经营性房地产资产查询系统...")
        
        # 创建QApplication
        logger.info("创建QApplication...")
        app = QApplication(sys.argv)
        logger.info("QApplication创建成功")
        
        # 设置应用程序信息
        app.setApplicationName("A股非经营性房地产资产查询系统")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("DataQuery System")
        
        # 创建主窗口
        logger.info("创建主窗口...")
        window = RealEstateQueryApp()
        logger.info("主窗口创建成功")
        
        logger.info("显示主窗口...")
        window.show()
        logger.info("主窗口显示成功")
        
        print("UI启动成功！")
        print("使用说明:")
        print("1. 选择财务指标或手动输入")
        print("2. 选择查询时点（最多4个）")
        print("3. 输入股票代码/名称进行筛选")
        print("4. 点击查询按钮开始查询")
        print("5. 查询完成后可导出Excel")
        
        # 启动事件循环
        logger.info("进入事件循环...")
        sys.exit(app.exec_())
        
    except ImportError as e:
        print(f"导入PyQt5失败: {e}")
        print("\n请确保已安装PyQt5:")
        print("pip install PyQt5")
        print("\n或者使用系统包管理器:")
        print("sudo apt install python3-pyqt5")
        
        # 提供命令行模式
        print("\n正在启动命令行模式...")
        run_command_line_mode()
        
    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)
        print(f"启动失败: {e}")
        sys.exit(1)

def run_command_line_mode():
    """命令行模式运行"""
    from ui.data_query_service import DataQueryService
    service = DataQueryService()
    
    print("\n=== A股非经营性房地产资产查询系统（命令行模式） ===")
    print(f"数据库路径: {service.db_path}")
    print(f"可用指标: {len(service.available_subjects)} 个")
    print(f"可用市场: {', '.join(service.markets)}")
    
    while True:
        print("\n请选择操作:")
        print("1. 查询所有数据")
        print("2. 按市场查询")
        print("3. 按股票代码查询")
        print("4. 显示可用指标列表")
        print("5. 导出数据到Excel")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-5): ").strip()
        
        if choice == "0":
            print("再见！")
            break
        elif choice == "1":
            try:
                df = service.query_data()
                print(f"\n查询结果: {len(df)} 条记录")
                if not df.empty:
                    print(df.head())
            except Exception as e:
                print(f"查询失败: {e}")
                
        elif choice == "2":
            market = input("请输入市场 (沪市/深市/北市): ").strip()
            try:
                df = service.query_data(market=market)
                print(f"\n{market}查询结果: {len(df)} 条记录")
                if not df.empty:
                    print(df.head())
            except Exception as e:
                print(f"查询失败: {e}")
                
        elif choice == "3":
            code = input("请输入股票代码: ").strip()
            try:
                df = service.query_data(stock_codes=[code])
                print(f"\n股票{code}查询结果: {len(df)} 条记录")
                if not df.empty:
                    print(df.head())
            except Exception as e:
                print(f"查询失败: {e}")
                
        elif choice == "4":
            print("\n可用财务指标:")
            for i, subject in enumerate(service.available_subjects, 1):
                print(f"{i:2d}. {subject['name']} ({subject['code']})")
                
        elif choice == "5":
            try:
                df = service.query_data()
                if df.empty:
                    print("没有数据可导出")
                else:
                    file_path = input("请输入导出文件路径: ").strip()
                    if service.export_to_excel(df, file_path):
                        print(f"数据已导出到: {file_path}")
                    else:
                        print("导出失败")
            except Exception as e:
                print(f"导出失败: {e}")
        else:
            print("无效选择，请重试")

if __name__ == "__main__":
    main()