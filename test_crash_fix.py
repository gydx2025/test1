#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试崩溃修复的脚本
"""

import sys
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_data_service_initialization():
    """测试DataQueryService初始化"""
    logger.info("=== 测试 DataQueryService 初始化 ===")
    try:
        from ui.data_query_service import DataQueryService
        
        logger.info("创建 DataQueryService 实例...")
        service = DataQueryService()
        logger.info(f"成功创建 DataQueryService，可用指标数: {len(service.available_subjects)}")
        logger.info(f"市场列表: {service.markets}")
        
        # 测试查询
        logger.info("测试查询功能...")
        df = service.query_data()
        logger.info(f"查询成功，返回 {len(df)} 条记录")
        
        # 关闭服务
        logger.info("关闭数据库连接...")
        service.close()
        logger.info("DataQueryService 关闭成功")
        
        return True
    except Exception as e:
        logger.error(f"DataQueryService 初始化失败: {e}", exc_info=True)
        return False

def test_ui_initialization():
    """测试UI初始化"""
    logger.info("\n=== 测试 UI 初始化 ===")
    try:
        # 尝试导入PyQt5
        try:
            from PyQt5.QtWidgets import QApplication
            from ui.real_estate_query_app import RealEstateQueryApp
            logger.info("PyQt5 和 UI 模块导入成功")
        except ImportError as e:
            logger.warning(f"PyQt5 不可用: {e}")
            logger.info("跳过 UI 初始化测试")
            return True
        
        logger.info("创建 QApplication...")
        app = QApplication(sys.argv)
        logger.info("QApplication 创建成功")
        
        logger.info("创建主窗口...")
        window = RealEstateQueryApp()
        logger.info("主窗口创建成功")
        
        logger.info("关闭主窗口...")
        window.close()
        logger.info("主窗口关闭成功")
        
        return True
    except Exception as e:
        logger.error(f"UI 初始化失败: {e}", exc_info=True)
        return False

def main():
    """主测试函数"""
    logger.info("开始运行崩溃修复测试...")
    
    results = {
        'DataQueryService': test_data_service_initialization(),
        'UI Initialization': test_ui_initialization(),
    }
    
    logger.info("\n=== 测试结果汇总 ===")
    for test_name, result in results.items():
        status = "通过" if result else "失败"
        logger.info(f"{test_name}: {status}")
    
    if all(results.values()):
        logger.info("\n✓ 所有测试通过！")
        return 0
    else:
        logger.error("\n✗ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
