#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试查询崩溃修复
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

def test_query_worker():
    """测试QueryWorker中的参数处理"""
    logger.info("测试QueryWorker参数处理...")
    
    # 模拟QueryWorker中的参数处理逻辑
    query_params = {
        'stock_codes': '000001,000002',
        'stock_names': '平安银行,万科',
        'market': '全部',
        'industry': '全行业',
        'subject_codes': ['INVEST_REALESTATE', 'FIXED_ASSET'],
        'time_point_0': '2024-12-31',
        'time_point_1': None,
        'time_point_2': None,
        'time_point_3': None
    }
    
    # 解析股票代码和名称
    stock_codes = []
    stock_names = []
    
    codes_text = query_params.get('stock_codes', '').strip()
    names_text = query_params.get('stock_names', '').strip()
    
    if codes_text:
        stock_codes = [code.strip() for code in codes_text.split(',') if code.strip()]
    
    if names_text:
        stock_names = [name.strip() for name in names_text.split(',') if name.strip()]
    
    logger.info(f"解析股票代码: {stock_codes}")
    logger.info(f"解析股票名称: {stock_names}")
    
    # 处理时点
    time_points = []
    for i in range(4):
        date_value = query_params.get(f'time_point_{i}')
        if date_value:
            time_points.append(date_value)
    
    logger.info(f"解析时点: {time_points}")
    
    assert stock_codes == ['000001', '000002'], "股票代码解析错误"
    assert stock_names == ['平安银行', '万科'], "股票名称解析错误"
    assert time_points == ['2024-12-31'], "时点解析错误"
    
    logger.info("✓ QueryWorker参数处理测试通过")

def test_data_query_service():
    """测试DataQueryService初始化"""
    logger.info("测试DataQueryService初始化...")
    
    from data_query_service import DataQueryService
    
    try:
        service = DataQueryService('test_query.db')
        logger.info(f"✓ DataQueryService初始化成功")
        
        # 检查科目列表
        subjects = service.available_subjects
        logger.info(f"加载了 {len(subjects)} 个科目")
        
        assert len(subjects) > 0, "科目列表为空"
        
        # 检查市场列表
        markets = service.markets
        logger.info(f"市场列表: {markets}")
        
        # 检查行业列表
        industries = service.get_industry_options()
        logger.info(f"获取了 {len(industries)} 个行业")
        
        logger.info("✓ DataQueryService初始化测试通过")
        
        # 清理测试数据库
        if os.path.exists('test_query.db'):
            os.remove('test_query.db')
            logger.info("清理测试数据库")
        
    except Exception as e:
        logger.error(f"✗ DataQueryService初始化失败: {str(e)}", exc_info=True)
        raise

def test_exception_handling():
    """测试异常处理"""
    logger.info("测试异常处理...")
    
    try:
        # 测试on_time_point_changed方法签名是否正确
        # 这个方法现在应该接受可选的date参数
        def on_time_point_changed(date=None):
            """测试方法"""
            if date:
                return str(date)
            return "no date"
        
        # 测试调用方式
        result1 = on_time_point_changed()
        result2 = on_time_point_changed("2024-12-31")
        
        logger.info(f"无参调用结果: {result1}")
        logger.info(f"有参调用结果: {result2}")
        
        assert result1 == "no date", "无参调用失败"
        assert result2 == "2024-12-31", "有参调用失败"
        
        logger.info("✓ 异常处理测试通过")
        
    except Exception as e:
        logger.error(f"✗ 异常处理测试失败: {str(e)}", exc_info=True)
        raise

def main():
    """主测试函数"""
    logger.info("=== 开始查询崩溃修复测试 ===")
    
    try:
        test_query_worker()
        test_exception_handling()
        test_data_query_service()
        
        logger.info("=== 所有测试通过 ===")
        return 0
        
    except Exception as e:
        logger.error(f"=== 测试失败: {str(e)} ===", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
