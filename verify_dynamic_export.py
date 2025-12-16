#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态Excel导出功能验证脚本

快速验证所有功能是否正常工作
"""

import sys
import logging
from excel_exporter import ExcelExporter, ExcelReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def verify_imports():
    """验证导入"""
    logger.info("1. 验证模块导入...")
    try:
        from excel_exporter import ExcelExporter, ExcelReportGenerator
        logger.info("   ✓ 导入成功")
        return True
    except Exception as e:
        logger.error(f"   ✗ 导入失败: {e}")
        return False


def verify_class_methods():
    """验证类方法存在"""
    logger.info("2. 验证类方法...")
    try:
        exporter = ExcelExporter()
        assert hasattr(exporter, 'export_query_results'), "缺少 export_query_results 方法"
        assert hasattr(exporter, '_add_query_metadata_sheet'), "缺少 _add_query_metadata_sheet 方法"
        assert hasattr(ExcelReportGenerator, 'export_dynamic_query_results'), "缺少 export_dynamic_query_results 方法"
        logger.info("   ✓ 所有方法存在")
        return True
    except Exception as e:
        logger.error(f"   ✗ 方法验证失败: {e}")
        return False


def verify_basic_export():
    """验证基本导出功能"""
    logger.info("3. 验证基本导出功能...")
    try:
        data = [
            {
                'code': '000001',
                'name': '平安银行',
                'market': '深交所主板',
                'industry': '银行',
                'value_2023-12-31': 1000000.00,
            }
        ]
        
        result = ExcelReportGenerator.export_dynamic_query_results(
            data=data,
            indicator_name='测试指标',
            periods=['2023-12-31'],
            filters={'测试': 'true'},
            filename='verify_test.xlsx'
        )
        
        if result:
            logger.info(f"   ✓ 导出成功: {result}")
            # 清理测试文件
            import os
            if os.path.exists(result):
                os.remove(result)
                logger.info("   ✓ 测试文件已清理")
            return True
        else:
            logger.error("   ✗ 导出返回None")
            return False
    except Exception as e:
        logger.error(f"   ✗ 导出失败: {e}")
        return False


def verify_error_handling():
    """验证错误处理"""
    logger.info("4. 验证错误处理...")
    try:
        # 测试空数据
        result1 = ExcelReportGenerator.export_dynamic_query_results(
            data=[],
            indicator_name='测试',
            periods=['2023-12-31']
        )
        assert result1 is None, "空数据应该返回None"
        
        # 测试空指标名
        result2 = ExcelReportGenerator.export_dynamic_query_results(
            data=[{'code': '000001'}],
            indicator_name='',
            periods=['2023-12-31']
        )
        assert result2 is None, "空指标名应该返回None"
        
        logger.info("   ✓ 错误处理正常")
        return True
    except Exception as e:
        logger.error(f"   ✗ 错误处理验证失败: {e}")
        return False


def verify_multi_period_support():
    """验证多时点支持"""
    logger.info("5. 验证多时点支持...")
    try:
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
            }
        ]
        
        # 测试4个时点
        result = ExcelReportGenerator.export_dynamic_query_results(
            data=data,
            indicator_name='测试指标',
            periods=['2021-12-31', '2022-12-31', '2023-12-31', '2024-06-30'],
            filename='verify_multi_period.xlsx'
        )
        
        if result:
            logger.info(f"   ✓ 4时点导出成功")
            import os
            if os.path.exists(result):
                os.remove(result)
            return True
        else:
            logger.error("   ✗ 4时点导出失败")
            return False
    except Exception as e:
        logger.error(f"   ✗ 多时点验证失败: {e}")
        return False


def main():
    """主验证流程"""
    logger.info("\n" + "="*60)
    logger.info("动态Excel导出功能验证")
    logger.info("="*60 + "\n")
    
    results = []
    
    results.append(("模块导入", verify_imports()))
    results.append(("类方法", verify_class_methods()))
    results.append(("基本导出", verify_basic_export()))
    results.append(("错误处理", verify_error_handling()))
    results.append(("多时点支持", verify_multi_period_support()))
    
    logger.info("\n" + "="*60)
    logger.info("验证结果")
    logger.info("="*60)
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{status}: {name}")
    
    logger.info("")
    logger.info(f"总计: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        logger.info("\n🎉 所有验证通过！动态Excel导出功能正常工作。")
        logger.info("="*60 + "\n")
        return True
    else:
        logger.error(f"\n❌ {total_count - success_count} 项验证失败。")
        logger.info("="*60 + "\n")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
