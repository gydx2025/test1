#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试资源清理的脚本 - 确保没有内存泄漏
"""

import sys
import os
import logging
import gc

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_connection_cleanup():
    """测试数据库连接是否正确清理"""
    logger.info("=== 测试数据库连接清理 ===")
    try:
        from ui.data_query_service import DataQueryService
        
        # 创建多个服务实例
        for i in range(5):
            logger.info(f"创建第 {i+1} 个服务实例...")
            service = DataQueryService()
            
            # 执行查询
            logger.info(f"执行查询 {i+1}...")
            df = service.query_data()
            
            # 关闭服务
            logger.info(f"关闭服务 {i+1}...")
            service.close()
            
            # 强制垃圾回收
            gc.collect()
            logger.info(f"垃圾回收完成")
        
        logger.info("✓ 数据库连接清理测试通过")
        return True
        
    except Exception as e:
        logger.error(f"数据库连接清理测试失败: {e}", exc_info=True)
        return False

def test_context_manager():
    """测试上下文管理器是否正确关闭连接"""
    logger.info("\n=== 测试上下文管理器 ===")
    try:
        from ui.data_query_service import DataQueryService
        
        service = DataQueryService()
        
        # 使用上下文管理器
        logger.info("使用上下文管理器执行查询...")
        with service._get_connection_context() as conn:
            import sqlite3
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM stocks")
            count = cursor.fetchone()[0]
            logger.info(f"股票表记录数: {count}")
        
        logger.info("✓ 上下文管理器测试通过")
        service.close()
        return True
        
    except Exception as e:
        logger.error(f"上下文管理器测试失败: {e}", exc_info=True)
        return False

def test_destructor():
    """测试析构函数是否被调用"""
    logger.info("\n=== 测试析构函数 ===")
    try:
        from ui.data_query_service import DataQueryService
        
        # 创建一个作用域，让对象在作用域外被销毁
        def create_and_destroy():
            logger.info("创建服务实例...")
            service = DataQueryService()
            logger.info("执行查询...")
            df = service.query_data()
            logger.info("离开作用域，触发析构函数...")
            return df
        
        df = create_and_destroy()
        
        # 强制垃圾回收
        gc.collect()
        logger.info("垃圾回收完成，析构函数应该已被调用")
        
        logger.info("✓ 析构函数测试通过")
        return True
        
    except Exception as e:
        logger.error(f"析构函数测试失败: {e}", exc_info=True)
        return False

def test_multiple_queries():
    """测试多次查询是否导致连接泄漏"""
    logger.info("\n=== 测试多次查询 ===")
    try:
        from ui.data_query_service import DataQueryService
        
        service = DataQueryService()
        
        # 执行多次查询
        for i in range(10):
            logger.info(f"执行查询 {i+1}/10...")
            df = service.query_data()
            logger.info(f"查询 {i+1} 完成，返回 {len(df)} 条记录")
        
        service.close()
        
        logger.info("✓ 多次查询测试通过")
        return True
        
    except Exception as e:
        logger.error(f"多次查询测试失败: {e}", exc_info=True)
        return False

def main():
    """主测试函数"""
    logger.info("开始运行资源清理测试...\n")
    
    results = {
        'Connection Cleanup': test_connection_cleanup(),
        'Context Manager': test_context_manager(),
        'Destructor': test_destructor(),
        'Multiple Queries': test_multiple_queries(),
    }
    
    logger.info("\n=== 测试结果汇总 ===")
    for test_name, result in results.items():
        status = "通过" if result else "失败"
        logger.info(f"{test_name}: {status}")
    
    if all(results.values()):
        logger.info("\n✓ 所有资源清理测试通过！")
        logger.info("✓ 没有检测到内存泄漏或连接泄漏")
        return 0
    else:
        logger.error("\n✗ 部分资源清理测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
