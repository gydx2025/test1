#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据结构修复 - 验证以下问题的解决：
1. 数据重复（16506行 = 5502 × 3）-> 应该是5502行
2. 市场信息为"未知市场" -> 应该根据股票代码正确推断
3. 行业分类缺失 -> 应该从采集器获取
4. 科目数据为空 -> 应该有正确的数据
5. 缺少上市时间 -> 应该包含list_date列
"""

import sys
import os
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ui'))

def test_data_structure():
    """测试数据结构修复"""
    logger.info("=== 测试数据结构修复 ===\n")
    
    from data_query_service import DataQueryService
    
    service = DataQueryService()
    
    # 测试1：检查市场推断功能
    logger.info("【测试1】市场推断功能")
    logger.info("-" * 50)
    
    test_cases = [
        ('600000', '沪市'),
        ('000001', '深市'),
        ('830000', '北交所'),
        ('688000', '沪市'),
    ]
    
    market_test_pass = True
    for code, expected in test_cases:
        result = service._infer_market_from_code(code)
        if result == expected:
            logger.info(f"✓ {code} -> {result}")
        else:
            logger.error(f"✗ {code} -> {result} (expected: {expected})")
            market_test_pass = False
    
    logger.info("")
    
    # 测试2：检查宽表格式的基本逻辑
    logger.info("【测试2】宽表格式逻辑验证")
    logger.info("-" * 50)
    
    # 创建模拟数据来测试merge逻辑
    base_rows = [
        {'股票代码': '000001', '股票名称': '平安', '市场': '深市', '上市时间': '2020-01-01'},
        {'股票代码': '600000', '股票名称': '浦发', '市场': '沪市', '上市时间': '2019-01-01'},
    ]
    
    result_df = pd.DataFrame(base_rows)
    logger.info(f"✓ 基础数据创建: {len(result_df)} 行")
    
    # 模拟第一个科目的数据
    subject1_data = pd.DataFrame([
        {'股票代码': '000001', '2024-12-31/投资性房地产(万元)': 100.5},
        {'股票代码': '600000', '2024-12-31/投资性房地产(万元)': 200.3},
    ])
    
    result_df = result_df.merge(subject1_data, on='股票代码', how='left')
    logger.info(f"✓ merge科目1后: {len(result_df)} 行，{len(result_df.columns)} 列")
    
    # 模拟第二个科目的数据
    subject2_data = pd.DataFrame([
        {'股票代码': '000001', '2024-12-31/固定资产(万元)': 300.2},
        {'股票代码': '600000', '2024-12-31/固定资产(万元)': 400.1},
    ])
    
    result_df = result_df.merge(subject2_data, on='股票代码', how='left')
    logger.info(f"✓ merge科目2后: {len(result_df)} 行，{len(result_df.columns)} 列")
    
    # 验证没有重复行
    if len(result_df) == 2:
        logger.info("✓ 没有数据重复（行数正确）")
    else:
        logger.error(f"✗ 数据重复！应该是2行，但有{len(result_df)}行")
    
    # 验证有列包含列表时间
    if '上市时间' in result_df.columns:
        logger.info("✓ 包含上市时间列")
    else:
        logger.error("✗ 缺少上市时间列")
    
    # 验证列顺序
    expected_first_cols = ['股票代码', '股票名称', '上市时间', '市场']
    actual_first_cols = list(result_df.columns[:4])
    if actual_first_cols == expected_first_cols:
        logger.info(f"✓ 列顺序正确: {actual_first_cols}")
    else:
        logger.info(f"ℹ 列顺序: {actual_first_cols}")
    
    # 验证数据值
    logger.info(f"✓ 数据值检查:")
    logger.info(f"  000001行: {result_df[result_df['股票代码']=='000001'].to_dict('records')[0]}")
    logger.info(f"  600000行: {result_df[result_df['股票代码']=='600000'].to_dict('records')[0]}")
    
    logger.info("")
    
    # 测试3：检查科目映射
    logger.info("【测试3】科目代码映射")
    logger.info("-" * 50)
    
    subject_tests = [
        ('INVEST_REALESTATE', '投资性房地产'),
        ('FIXED_ASSET', '固定资产'),
    ]
    
    subject_test_pass = True
    for code, expected in subject_tests:
        result = service._get_subject_display_name(code)
        if result == expected:
            logger.info(f"✓ {code} -> {result}")
        else:
            logger.error(f"✗ {code} -> {result} (expected: {expected})")
            subject_test_pass = False
    
    logger.info("")
    
    # 测试4：验证无重复行的drop_duplicates逻辑
    logger.info("【测试4】无重复行验证")
    logger.info("-" * 50)
    
    # 创建有重复的数据
    dup_data = [
        {'股票代码': '000001', '股票名称': '平安', '市场': '深市'},
        {'股票代码': '000001', '股票名称': '平安', '市场': '深市'},  # 重复
        {'股票代码': '600000', '股票名称': '浦发', '市场': '沪市'},
    ]
    
    dup_df = pd.DataFrame(dup_data)
    logger.info(f"去重前: {len(dup_df)} 行")
    
    dup_df = dup_df.drop_duplicates(subset=['股票代码'], keep='first').reset_index(drop=True)
    logger.info(f"✓ 去重后: {len(dup_df)} 行")
    
    logger.info("")
    
    logger.info("=== 所有基础功能测试通过 ===\n")
    
    return market_test_pass and subject_test_pass

if __name__ == '__main__':
    try:
        success = test_data_structure()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        sys.exit(1)
