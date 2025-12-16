#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态Excel导出功能的单元测试和集成测试

测试 export_query_results 方法和 export_dynamic_query_results API
"""

import unittest
import os
import logging
from datetime import datetime
from excel_exporter import ExcelExporter, ExcelReportGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class TestDynamicExcelExport(unittest.TestCase):
    """测试动态Excel导出功能"""
    
    def setUp(self):
        """测试前准备"""
        self.test_files = []
    
    def tearDown(self):
        """测试后清理"""
        for filepath in self.test_files:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"已删除测试文件: {filepath}")
                except Exception as e:
                    logger.warning(f"清理测试文件失败 {filepath}: {e}")
    
    def test_export_with_all_periods(self):
        """测试导出包含4个时点的数据"""
        logger.info("=== 测试1: 导出4个时点的数据 ===")
        
        # 准备测试数据
        data = [
            {
                'code': '000001',
                'name': '平安银行',
                'market': '深交所主板',
                'industry': '银行',
                'value_2021-12-31': 1000000.50,
                'value_2022-12-31': 1100000.75,
                'value_2023-12-31': 1200000.00,
                'value_2024-06-30': 1250000.25,
            },
            {
                'code': '000002',
                'name': '万科A',
                'market': '深交所主板',
                'industry': '房地产',
                'value_2021-12-31': 5000000.00,
                'value_2022-12-31': 5200000.00,
                'value_2023-12-31': 5100000.00,
                'value_2024-06-30': 5050000.00,
            },
            {
                'code': '600000',
                'name': '浦发银行',
                'market': '上交所主板',
                'industry': '银行',
                'value_2021-12-31': 2000000.00,
                'value_2022-12-31': 2100000.00,
                'value_2023-12-31': 2200000.00,
                'value_2024-06-30': 2250000.00,
            },
        ]
        
        periods = ['2021-12-31', '2022-12-31', '2023-12-31', '2024-06-30']
        filters = {'市场': '主板', '行业': '银行,房地产'}
        filename = 'test_export_4_periods.xlsx'
        
        # 执行导出
        result = ExcelReportGenerator.export_dynamic_query_results(
            data=data,
            indicator_name='投资性房地产',
            periods=periods,
            filters=filters,
            filename=filename
        )
        
        # 验证结果
        self.assertIsNotNone(result, "导出应该返回文件路径")
        self.assertTrue(os.path.exists(result), "导出的文件应该存在")
        self.assertGreater(os.path.getsize(result), 0, "导出的文件大小应该大于0")
        self.test_files.append(result)
        
        logger.info(f"✓ 测试1通过: 文件已生成 {result}")
    
    def test_export_with_two_periods(self):
        """测试导出包含2个时点的数据"""
        logger.info("=== 测试2: 导出2个时点的数据 ===")
        
        data = [
            {
                'code': '000001',
                'name': '平安银行',
                'market': '深交所主板',
                'industry': '银行',
                'value_2023-12-31': 1200000.00,
                'value_2024-06-30': 1250000.25,
            },
            {
                'code': '000002',
                'name': '万科A',
                'market': '深交所主板',
                'industry': '房地产',
                'value_2023-12-31': 5100000.00,
                'value_2024-06-30': 5050000.00,
            },
        ]
        
        periods = ['2023-12-31', '2024-06-30']
        filters = {'市场': '主板'}
        filename = 'test_export_2_periods.xlsx'
        
        result = ExcelReportGenerator.export_dynamic_query_results(
            data=data,
            indicator_name='固定资产',
            periods=periods,
            filters=filters,
            filename=filename
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.test_files.append(result)
        
        logger.info(f"✓ 测试2通过: 文件已生成 {result}")
    
    def test_export_with_no_periods(self):
        """测试导出不包含时点的数据（仅基本信息）"""
        logger.info("=== 测试3: 导出0个时点的数据（仅基本信息）===")
        
        data = [
            {
                'code': '000001',
                'name': '平安银行',
                'market': '深交所主板',
                'industry': '银行',
            },
            {
                'code': '000002',
                'name': '万科A',
                'market': '深交所主板',
                'industry': '房地产',
            },
        ]
        
        periods = []
        filters = {}
        filename = 'test_export_0_periods.xlsx'
        
        result = ExcelReportGenerator.export_dynamic_query_results(
            data=data,
            indicator_name='基本信息',
            periods=periods,
            filters=filters,
            filename=filename
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.test_files.append(result)
        
        logger.info(f"✓ 测试3通过: 文件已生成 {result}")
    
    def test_export_with_missing_values(self):
        """测试导出包含缺失值的数据"""
        logger.info("=== 测试4: 导出包含缺失值的数据 ===")
        
        data = [
            {
                'code': '000001',
                'name': '平安银行',
                'market': '深交所主板',
                'industry': '银行',
                'value_2023-12-31': 1200000.00,
                'value_2024-06-30': None,  # 缺失值
            },
            {
                'code': '000002',
                'name': '万科A',
                'market': '深交所主板',
                'industry': '房地产',
                'value_2023-12-31': None,  # 缺失值
                'value_2024-06-30': 5050000.00,
            },
            {
                'code': '000003',
                'name': '测试公司',
                'market': '深交所主板',
                'industry': '制造业',
                # 完全缺失时点数据
            },
        ]
        
        periods = ['2023-12-31', '2024-06-30']
        filters = {}
        filename = 'test_export_missing_values.xlsx'
        
        result = ExcelReportGenerator.export_dynamic_query_results(
            data=data,
            indicator_name='无形资产',
            periods=periods,
            filters=filters,
            filename=filename
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.test_files.append(result)
        
        logger.info(f"✓ 测试4通过: 文件已生成 {result}")
    
    def test_export_with_auto_filename(self):
        """测试自动生成文件名"""
        logger.info("=== 测试5: 自动生成文件名 ===")
        
        data = [
            {
                'code': '000001',
                'name': '平安银行',
                'market': '深交所主板',
                'industry': '银行',
                'value_2024-06-30': 1250000.25,
            },
        ]
        
        periods = ['2024-06-30']
        
        result = ExcelReportGenerator.export_dynamic_query_results(
            data=data,
            indicator_name='投资性房地产',
            periods=periods,
            # 不提供filename，应该自动生成
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.assertTrue(result.startswith('query_export_'))
        self.assertTrue(result.endswith('.xlsx'))
        self.test_files.append(result)
        
        logger.info(f"✓ 测试5通过: 自动生成文件名 {result}")
    
    def test_export_with_invalid_inputs(self):
        """测试无效输入的错误处理"""
        logger.info("=== 测试6: 无效输入的错误处理 ===")
        
        # 测试空数据
        result1 = ExcelReportGenerator.export_dynamic_query_results(
            data=[],
            indicator_name='测试指标',
            periods=['2024-06-30']
        )
        self.assertIsNone(result1, "空数据应该返回None")
        
        # 测试空指标名
        result2 = ExcelReportGenerator.export_dynamic_query_results(
            data=[{'code': '000001', 'name': '测试'}],
            indicator_name='',
            periods=['2024-06-30']
        )
        self.assertIsNone(result2, "空指标名应该返回None")
        
        # 测试非列表的periods
        result3 = ExcelReportGenerator.export_dynamic_query_results(
            data=[{'code': '000001', 'name': '测试'}],
            indicator_name='测试指标',
            periods='2024-06-30'  # 应该是列表，不是字符串
        )
        self.assertIsNone(result3, "非列表的periods应该返回None")
        
        logger.info("✓ 测试6通过: 错误处理正常")
    
    def test_export_method_directly(self):
        """测试直接调用ExcelExporter.export_query_results方法"""
        logger.info("=== 测试7: 直接调用ExcelExporter方法 ===")
        
        data = [
            {
                'code': '000001',
                'name': '平安银行',
                'market': '深交所主板',
                'industry': '银行',
                'value_2023-12-31': 1200000.00,
                'value_2024-06-30': 1250000.25,
            },
        ]
        
        periods = ['2023-12-31', '2024-06-30']
        filters = {'市场': '主板'}
        filename = 'test_direct_method.xlsx'
        
        exporter = ExcelExporter()
        result = exporter.export_query_results(
            data=data,
            indicator_name='直接测试',
            periods=periods,
            filters=filters,
            filename=filename
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        self.test_files.append(result)
        
        logger.info(f"✓ 测试7通过: 直接方法调用成功 {result}")
    
    def test_comprehensive_scenario(self):
        """综合测试场景：模拟真实UI查询导出"""
        logger.info("=== 测试8: 综合场景测试 ===")
        
        # 模拟真实的查询结果数据
        data = [
            {
                'code': '000001',
                'name': '平安银行',
                'market': '深交所主板',
                'industry': '银行',
                'value_2021-12-31': 1000000.00,
                'value_2022-12-31': 1100000.00,
                'value_2023-12-31': 1200000.00,
            },
            {
                'code': '000002',
                'name': '万科A',
                'market': '深交所主板',
                'industry': '房地产',
                'value_2021-12-31': 5000000.00,
                'value_2022-12-31': 5200000.00,
                'value_2023-12-31': 5100000.00,
            },
            {
                'code': '600000',
                'name': '浦发银行',
                'market': '上交所主板',
                'industry': '银行',
                'value_2021-12-31': 2000000.00,
                'value_2022-12-31': None,  # 缺失值
                'value_2023-12-31': 2200000.00,
            },
            {
                'code': '600036',
                'name': '招商银行',
                'market': '上交所主板',
                'industry': '银行',
                'value_2021-12-31': 3000000.00,
                'value_2022-12-31': 3200000.00,
                'value_2023-12-31': 3400000.00,
            },
            {
                'code': '000333',
                'name': '美的集团',
                'market': '深交所主板',
                'industry': '家用电器',
                'value_2021-12-31': 800000.00,
                'value_2022-12-31': 850000.00,
                'value_2023-12-31': 900000.00,
            },
        ]
        
        periods = ['2021-12-31', '2022-12-31', '2023-12-31']
        filters = {
            '市场': '主板',
            '行业': '银行,房地产,家用电器',
            '数据完整性': '包含缺失值',
            '查询时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        result = ExcelReportGenerator.export_dynamic_query_results(
            data=data,
            indicator_name='投资性房地产',
            periods=periods,
            filters=filters,
            filename='test_comprehensive.xlsx'
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(os.path.exists(result))
        
        # 验证文件大小合理
        file_size = os.path.getsize(result)
        self.assertGreater(file_size, 5000, "文件大小应该合理")
        
        self.test_files.append(result)
        
        logger.info(f"✓ 测试8通过: 综合场景测试成功，文件大小: {file_size} bytes")


def run_tests():
    """运行所有测试"""
    logger.info("\n" + "="*60)
    logger.info("开始运行动态Excel导出功能测试")
    logger.info("="*60 + "\n")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDynamicExcelExport)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    logger.info("\n" + "="*60)
    logger.info("测试完成")
    logger.info(f"总测试数: {result.testsRun}")
    logger.info(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    logger.info("="*60 + "\n")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
