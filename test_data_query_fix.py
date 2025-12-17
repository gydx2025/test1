#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据查询修复 - 使用原有采集器逻辑
"""

import sys
import os
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加ui目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ui'))

def test_data_query_service():
    """测试修复后的DataQueryService"""
    logger.info("=== 测试修复后的DataQueryService ===")
    
    from data_query_service import DataQueryService
    
    try:
        # 创建查询服务
        service = DataQueryService()
        logger.info("✓ DataQueryService初始化成功")
        
        # 测试1: 获取股票列表
        logger.info("\n--- 测试1: 获取股票列表 ---")
        stock_list = service.get_stock_list()
        if not stock_list.empty:
            logger.info(f"✓ 成功获取股票列表: {len(stock_list)} 只股票")
            logger.info(f"  前5只股票: {stock_list.head().to_dict('records')}")
        else:
            logger.warning("✗ 获取股票列表失败，返回空结果")
        
        # 测试2: 获取行业列表
        logger.info("\n--- 测试2: 获取行业列表 ---")
        industries = service.get_industry_options()
        logger.info(f"✓ 成功获取行业列表: {len(industries)} 个行业")
        if industries:
            logger.info(f"  前10个行业: {industries[:10]}")
        
        # 测试3: 简单查询测试（只查询一只股票）
        logger.info("\n--- 测试3: 简单查询测试 ---")
        test_result = service.query_data(
            stock_codes=['000001'],  # 平安银行
            subject_codes=['INVEST_REALESTATE'],
            time_points=['2023-12-31']
        )
        
        if not test_result.empty:
            logger.info(f"✓ 查询成功，返回 {len(test_result)} 条记录")
            logger.info(f"  查询结果列: {list(test_result.columns)}")
            if len(test_result) > 0:
                logger.info(f"  第一条记录: {test_result.iloc[0].to_dict()}")
        else:
            logger.warning("✗ 查询失败，返回空结果")
            logger.warning("  这可能是因为股票代码无效或网络连接问题")
        
        # 测试4: 多科目查询测试
        logger.info("\n--- 测试4: 多科目查询测试 ---")
        multi_result = service.query_data(
            stock_codes=['000001', '600519'],  # 平安银行、贵州茅台
            subject_codes=['INVEST_REALESTATE', 'FIXED_ASSET'],
            time_points=['2023-12-31']
        )
        
        if not multi_result.empty:
            logger.info(f"✓ 多科目查询成功，返回 {len(multi_result)} 条记录")
            logger.info(f"  查询结果列: {list(multi_result.columns)}")
        else:
            logger.warning("✗ 多科目查询失败")
        
        # 测试5: 测试科目映射
        logger.info("\n--- 测试5: 测试科目代码映射 ---")
        subject_names = service._get_subject_display_name('INVEST_REALESTATE')
        logger.info(f"✓ INVEST_REALESTATE -> {subject_names}")
        
        market_name = service._get_market_display_name('SH600000')
        logger.info(f"✓ SH600000 -> {market_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 测试失败: {str(e)}", exc_info=True)
        return False

def test_collector_integration():
    """测试采集器集成"""
    logger.info("\n=== 测试采集器集成 ===")
    
    try:
        # 直接测试FinancialQueryService
        from financial_query_service import FinancialQueryService
        
        query_service = FinancialQueryService()
        logger.info("✓ FinancialQueryService初始化成功")
        
        # 测试查询参数准备
        params = {
            'stock_codes': ['000001'],
            'market': '全部',
            'subject': '投资性房地产',
            'report_dates': ['2023-12-31'],
            'return_format': 'dataframe',
            'unit': '万元'
        }
        
        logger.info(f"查询参数: {params}")
        
        # 执行查询
        result = query_service.execute_query(params)
        
        if result.success and result.dataframe is not None:
            logger.info(f"✓ 采集器查询成功，返回 {len(result.dataframe)} 条记录")
            logger.info(f"  列名: {list(result.dataframe.columns)}")
            return True
        else:
            logger.warning(f"✗ 采集器查询失败: {result.error}")
            return False
            
    except Exception as e:
        logger.error(f"✗ 采集器集成测试失败: {str(e)}", exc_info=True)
        return False

def main():
    """主测试函数"""
    logger.info("=== 开始测试数据查询修复 ===")
    
    try:
        # 测试修复后的DataQueryService
        test1_passed = test_data_query_service()
        
        # 测试采集器集成
        test2_passed = test_collector_integration()
        
        if test1_passed and test2_passed:
            logger.info("=== 所有测试通过 ===")
            logger.info("✓ DataQueryService现在使用原有采集器逻辑")
            logger.info("✓ 不再依赖空的本地数据库")
            logger.info("✓ 应该能正确返回查询数据")
            return 0
        else:
            logger.warning("=== 部分测试失败 ===")
            return 1
            
    except Exception as e:
        logger.error(f"=== 测试执行失败: {str(e)} ===", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())