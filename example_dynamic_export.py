#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态Excel导出功能使用示例

演示如何使用新的动态导出API
"""

import logging
from datetime import datetime
from excel_exporter import ExcelReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_simple_export():
    """示例1: 简单的2个时点导出"""
    logger.info("\n" + "="*60)
    logger.info("示例1: 简单的2个时点导出")
    logger.info("="*60)
    
    # 模拟UI查询结果
    data = [
        {
            'code': '000001',
            'name': '平安银行',
            'market': '深交所主板',
            'industry': '银行',
            'value_2023-12-31': 1234567.89,
            'value_2024-06-30': 1345678.90,
        },
        {
            'code': '000002',
            'name': '万科A',
            'market': '深交所主板',
            'industry': '房地产',
            'value_2023-12-31': 5234567.12,
            'value_2024-06-30': 5134567.34,
        },
        {
            'code': '600000',
            'name': '浦发银行',
            'market': '上交所主板',
            'industry': '银行',
            'value_2023-12-31': 2234567.56,
            'value_2024-06-30': 2334567.78,
        },
    ]
    
    # 调用导出
    result = ExcelReportGenerator.export_dynamic_query_results(
        data=data,
        indicator_name='投资性房地产',
        periods=['2023-12-31', '2024-06-30'],
        filters={'市场': '主板', '行业': '银行,房地产'},
        filename='example_1_simple_export.xlsx'
    )
    
    if result:
        logger.info(f"✓ 示例1成功: {result}")
    else:
        logger.error("✗ 示例1失败")
    
    return result


def example_2_multi_period_comparison():
    """示例2: 4个时点的多年度对比"""
    logger.info("\n" + "="*60)
    logger.info("示例2: 4个时点的多年度对比")
    logger.info("="*60)
    
    # 模拟4年数据
    data = [
        {
            'code': '000001',
            'name': '平安银行',
            'market': '深交所主板',
            'industry': '银行',
            'value_2021-12-31': 1000000.00,
            'value_2022-12-31': 1100000.00,
            'value_2023-12-31': 1200000.00,
            'value_2024-06-30': 1250000.00,
        },
        {
            'code': '000333',
            'name': '美的集团',
            'market': '深交所主板',
            'industry': '家用电器',
            'value_2021-12-31': 800000.00,
            'value_2022-12-31': 850000.00,
            'value_2023-12-31': 900000.00,
            'value_2024-06-30': 950000.00,
        },
        {
            'code': '600036',
            'name': '招商银行',
            'market': '上交所主板',
            'industry': '银行',
            'value_2021-12-31': 3000000.00,
            'value_2022-12-31': 3200000.00,
            'value_2023-12-31': 3400000.00,
            'value_2024-06-30': 3600000.00,
        },
    ]
    
    result = ExcelReportGenerator.export_dynamic_query_results(
        data=data,
        indicator_name='固定资产',
        periods=['2021-12-31', '2022-12-31', '2023-12-31', '2024-06-30'],
        filters={
            '市场': '主板',
            '行业': '银行,家用电器',
            '查询类型': '多年度对比分析'
        },
        filename='example_2_multi_period.xlsx'
    )
    
    if result:
        logger.info(f"✓ 示例2成功: {result}")
    else:
        logger.error("✗ 示例2失败")
    
    return result


def example_3_with_missing_values():
    """示例3: 包含缺失值的数据"""
    logger.info("\n" + "="*60)
    logger.info("示例3: 包含缺失值的数据")
    logger.info("="*60)
    
    data = [
        {
            'code': '000001',
            'name': '平安银行',
            'market': '深交所主板',
            'industry': '银行',
            'value_2023-12-31': 1234567.89,
            'value_2024-06-30': None,  # 缺失值
        },
        {
            'code': '000002',
            'name': '万科A',
            'market': '深交所主板',
            'industry': '房地产',
            'value_2023-12-31': None,  # 缺失值
            'value_2024-06-30': 5134567.34,
        },
        {
            'code': '000003',
            'name': '测试公司',
            'market': '深交所创业板',
            'industry': '科技',
            # 完全缺失时点数据
        },
    ]
    
    result = ExcelReportGenerator.export_dynamic_query_results(
        data=data,
        indicator_name='无形资产',
        periods=['2023-12-31', '2024-06-30'],
        filters={'数据完整性': '包含缺失值'},
        filename='example_3_missing_values.xlsx'
    )
    
    if result:
        logger.info(f"✓ 示例3成功: {result}")
    else:
        logger.error("✗ 示例3失败")
    
    return result


def example_4_auto_filename():
    """示例4: 自动生成文件名"""
    logger.info("\n" + "="*60)
    logger.info("示例4: 自动生成文件名")
    logger.info("="*60)
    
    data = [
        {
            'code': '600519',
            'name': '贵州茅台',
            'market': '上交所主板',
            'industry': '食品饮料',
            'value_2024-06-30': 9876543.21,
        },
    ]
    
    # 不提供filename，将自动生成
    result = ExcelReportGenerator.export_dynamic_query_results(
        data=data,
        indicator_name='存货',
        periods=['2024-06-30']
    )
    
    if result:
        logger.info(f"✓ 示例4成功: {result} (自动生成)")
    else:
        logger.error("✗ 示例4失败")
    
    return result


def example_5_comprehensive_query():
    """示例5: 综合查询场景（模拟真实UI操作）"""
    logger.info("\n" + "="*60)
    logger.info("示例5: 综合查询场景（模拟真实UI操作）")
    logger.info("="*60)
    
    # 模拟用户在UI上的完整操作
    # 1. 选择指标: 投资性房地产
    # 2. 选择时点: 3个时点
    # 3. 设置过滤: 主板市场、银行和房地产行业
    # 4. 查询并导出
    
    data = [
        {
            'code': '000001',
            'name': '平安银行',
            'market': '深交所主板',
            'industry': '银行',
            'value_2022-12-31': 1100000.00,
            'value_2023-12-31': 1200000.00,
            'value_2024-06-30': 1250000.00,
        },
        {
            'code': '000002',
            'name': '万科A',
            'market': '深交所主板',
            'industry': '房地产',
            'value_2022-12-31': 5200000.00,
            'value_2023-12-31': 5100000.00,
            'value_2024-06-30': 5050000.00,
        },
        {
            'code': '600000',
            'name': '浦发银行',
            'market': '上交所主板',
            'industry': '银行',
            'value_2022-12-31': 2100000.00,
            'value_2023-12-31': 2200000.00,
            'value_2024-06-30': 2250000.00,
        },
        {
            'code': '600036',
            'name': '招商银行',
            'market': '上交所主板',
            'industry': '银行',
            'value_2022-12-31': 3200000.00,
            'value_2023-12-31': 3400000.00,
            'value_2024-06-30': 3600000.00,
        },
        {
            'code': '000858',
            'name': '五粮液',
            'market': '深交所主板',
            'industry': '食品饮料',
            'value_2022-12-31': 450000.00,
            'value_2023-12-31': 480000.00,
            'value_2024-06-30': 500000.00,
        },
    ]
    
    # 记录详细的查询条件
    filters = {
        '市场': '主板（深交所、上交所）',
        '行业': '银行, 房地产, 食品饮料',
        '数据完整性': '完整（所有时点均有数据）',
        '查询时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '查询用户': 'UI系统',
        '备注': '综合查询示例'
    }
    
    result = ExcelReportGenerator.export_dynamic_query_results(
        data=data,
        indicator_name='投资性房地产',
        periods=['2022-12-31', '2023-12-31', '2024-06-30'],
        filters=filters,
        filename='example_5_comprehensive.xlsx'
    )
    
    if result:
        logger.info(f"✓ 示例5成功: {result}")
        logger.info(f"  - 记录数: {len(data)}")
        logger.info(f"  - 时点数: 3")
        logger.info(f"  - 总列数: 4 (基本字段) + 3 (时点) = 7")
    else:
        logger.error("✗ 示例5失败")
    
    return result


def run_all_examples():
    """运行所有示例"""
    logger.info("\n" + "="*60)
    logger.info("开始运行动态Excel导出功能示例")
    logger.info("="*60)
    
    results = []
    
    # 运行所有示例
    results.append(("示例1: 简单2时点导出", example_1_simple_export()))
    results.append(("示例2: 4时点多年度对比", example_2_multi_period_comparison()))
    results.append(("示例3: 包含缺失值", example_3_with_missing_values()))
    results.append(("示例4: 自动生成文件名", example_4_auto_filename()))
    results.append(("示例5: 综合查询场景", example_5_comprehensive_query()))
    
    # 汇总结果
    logger.info("\n" + "="*60)
    logger.info("所有示例执行完成")
    logger.info("="*60)
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for name, result in results:
        status = "✓ 成功" if result else "✗ 失败"
        logger.info(f"{status}: {name}")
    
    logger.info("")
    logger.info(f"成功: {success_count}/{total_count}")
    logger.info(f"失败: {total_count - success_count}/{total_count}")
    logger.info("="*60 + "\n")
    
    return success_count == total_count


if __name__ == '__main__':
    success = run_all_examples()
    exit(0 if success else 1)
