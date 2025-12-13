#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新增模块测试脚本

测试所有新增的数据处理模块是否能正常运行
"""

import logging
import sys
import os
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_data_validator():
    """测试数据验证模块"""
    logger.info("=" * 70)
    logger.info("🧪 测试数据验证模块 (DataValidator)")
    logger.info("=" * 70)
    
    from data_validator import DataValidator, DataCleaner
    
    validator = DataValidator()
    cleaner = DataCleaner(validator)
    
    # 测试股票代码验证
    logger.info("\n📋 测试股票代码验证:")
    test_codes = ['600000', '000001', '300001', '920000', 'invalid']
    for code in test_codes:
        valid, error = validator.validate_stock_code(code)
        status = "✅" if valid else "❌"
        logger.info(f"  {status} {code}: {error if error else '有效'}")
    
    # 测试公司名称验证
    logger.info("\n📋 测试公司名称验证:")
    test_names = ['中国银行', 'ABC', '', '名称<>无效']
    for name in test_names:
        valid, error = validator.validate_stock_name(name)
        status = "✅" if valid else "❌"
        logger.info(f"  {status} '{name}': {error if error else '有效'}")
    
    # 测试数据清洗
    logger.info("\n📋 测试数据清洗:")
    raw_code = 'sh600000'
    clean_code = cleaner.clean_stock_code(raw_code)
    logger.info(f"  清洗前: {raw_code}")
    logger.info(f"  清洗后: {clean_code}")
    
    logger.info("\n✅ 数据验证模块测试完成\n")


def test_local_storage():
    """测试本地存储模块"""
    logger.info("=" * 70)
    logger.info("🧪 测试本地存储模块 (LocalDatabase)")
    logger.info("=" * 70)
    
    from local_storage import LocalDatabase, CacheManager, CSVBackupManager
    
    # 测试缓存管理
    logger.info("\n📋 测试缓存管理:")
    cache = CacheManager('test_cache')
    
    test_data = {'code': '600000', 'name': '中国银行'}
    cache.save_cache('test', test_data)
    logger.info("  ✅ 缓存已保存")
    
    loaded = cache.load_cache('test')
    if loaded and loaded.get('code') == '600000':
        logger.info("  ✅ 缓存已加载")
    else:
        logger.error("  ❌ 缓存加载失败")
    
    # 测试CSV备份
    logger.info("\n📋 测试CSV备份:")
    test_records = [
        {'code': '600000', 'name': '中国银行'},
        {'code': '000001', 'name': '平安银行'},
    ]
    
    csv_file = 'test_backup.csv'
    CSVBackupManager.backup_to_csv(test_records, csv_file)
    logger.info(f"  ✅ CSV已保存: {csv_file}")
    
    restored = CSVBackupManager.restore_from_csv(csv_file)
    if len(restored) == 2:
        logger.info(f"  ✅ CSV已恢复: {len(restored)}条记录")
    else:
        logger.error("  ❌ CSV恢复失败")
    
    # 清理
    import shutil
    if os.path.exists('test_cache'):
        shutil.rmtree('test_cache')
    if os.path.exists(csv_file):
        os.remove(csv_file)
    
    logger.info("\n✅ 本地存储模块测试完成\n")


def test_quality_monitor():
    """测试质量监控模块"""
    logger.info("=" * 70)
    logger.info("🧪 测试质量监控模块 (DataQualityMonitor)")
    logger.info("=" * 70)
    
    from quality_monitor import DataQualityScore, DataQualityMonitor
    
    scorer = DataQualityScore()
    monitor = DataQualityMonitor()
    
    # 模拟数据统计
    test_stats = {
        'total_stocks': 5434,
        'valid_records': 5434,
        'total_records': 5434,
        'validation_errors': 0,
        'stocks_with_industry': 5200,
        'stocks_with_2023_data': 4900,
        'stocks_with_2024_data': 5100,
        'collection_date': '2024-12-13'
    }
    
    logger.info("\n📋 测试质量评分计算:")
    quality_report = scorer.calculate_overall_score(test_stats)
    
    logger.info(f"  综合评分: {quality_report['overall_score']:.1f}/100")
    logger.info(f"  评级: {quality_report['grade']}")
    
    for metric, data in quality_report['metrics'].items():
        logger.info(f"  {metric}: {data['score']:.1f}/100")
    
    logger.info("\n📋 测试监控报告生成:")
    monitoring_result = monitor.monitor(test_stats)
    report_text = monitor.generate_report(monitoring_result)
    logger.info("\n生成的报告摘要:")
    for line in report_text.split('\n')[0:10]:
        logger.info(f"  {line}")
    
    logger.info("\n✅ 质量监控模块测试完成\n")


def test_checkpoint_manager():
    """测试断点续传模块"""
    logger.info("=" * 70)
    logger.info("🧪 测试断点续传模块 (CheckpointManager)")
    logger.info("=" * 70)
    
    from checkpoint_manager import CheckpointManager, VersionManager
    
    checkpoint_mgr = CheckpointManager('test_checkpoints')
    version_mgr = VersionManager('test_version_history.json')
    
    # 测试检查点保存
    logger.info("\n📋 测试检查点保存:")
    progress = {'current_page': 5, 'processed': 500}
    checkpoint_mgr.save_checkpoint('test_stage', progress)
    logger.info("  ✅ 检查点已保存")
    
    # 测试检查点加载
    logger.info("\n📋 测试检查点加载:")
    latest = checkpoint_mgr.get_latest_checkpoint('test_stage')
    if latest and latest['progress']['current_page'] == 5:
        logger.info("  ✅ 检查点已加载")
    else:
        logger.error("  ❌ 检查点加载失败")
    
    # 测试版本管理
    logger.info("\n📋 测试版本管理:")
    version_mgr.record_version('v3.0.0', {
        'total_stocks': 5434,
        'data_completeness': 0.98,
        'notes': '测试版本'
    })
    logger.info("  ✅ 版本已记录")
    
    history = version_mgr.get_version_history()
    if len(history) > 0:
        logger.info(f"  ✅ 版本历史已获取: {len(history)}条记录")
    
    # 清理
    import shutil
    if os.path.exists('test_checkpoints'):
        shutil.rmtree('test_checkpoints')
    if os.path.exists('test_version_history.json'):
        os.remove('test_version_history.json')
    
    logger.info("\n✅ 断点续传模块测试完成\n")


def test_excel_exporter():
    """测试Excel导出模块"""
    logger.info("=" * 70)
    logger.info("🧪 测试Excel导出模块 (ExcelExporter)")
    logger.info("=" * 70)
    
    from excel_exporter import ExcelExporter, ExcelReportGenerator
    
    # 准备测试数据
    test_stocks = [
        {'code': '600000', 'name': '中国银行', 'market': '上海', 'list_date': '2001-01-01'},
        {'code': '000001', 'name': '平安银行', 'market': '深圳', 'list_date': '1991-04-03'},
    ]
    
    test_industries = {
        '600000': {'l1': '金融业', 'l2': '银行业', 'l3': '商业银行', 'source': 'sina'},
        '000001': {'l1': '金融业', 'l2': '银行业', 'l3': '商业银行', 'source': 'sina'},
    }
    
    test_financial = [
        {
            'code': '600000',
            'name': '中国银行',
            'industry': test_industries['600000'],
            'non_op_real_estate_2023': 1000000,
            'non_op_real_estate_2024': 1200000,
        },
        {
            'code': '000001',
            'name': '平安银行',
            'industry': test_industries['000001'],
            'non_op_real_estate_2023': 500000,
            'non_op_real_estate_2024': 600000,
        },
    ]
    
    test_report = {
        'total_stocks': 2,
        'stocks_with_industry': 2,
        'stocks_with_2023_data': 2,
        'stocks_with_2024_data': 2,
        'data_completeness': 1.0,
        'quality_report': {
            'overall_score': 95,
            'grade': 'A（很好）'
        }
    }
    
    test_metadata = {
        'collection_date': '2024-12-13',
        'collection_time': datetime.now().isoformat(),
        'version': 'v3.0.0',
        'sources': 'Multi-source',
        'duration': '1.5小时',
        'notes': '测试数据'
    }
    
    # 测试Excel生成
    logger.info("\n📋 测试Excel报告生成:")
    output_file = 'test_output.xlsx'
    
    result = ExcelReportGenerator.generate_complete_report(
        stocks=test_stocks,
        industries=test_industries,
        financial_data=test_financial,
        report=test_report,
        metadata=test_metadata,
        filename=output_file
    )
    
    if result and os.path.exists(output_file):
        file_size = os.path.getsize(output_file)
        logger.info(f"  ✅ Excel文件已生成: {output_file} ({file_size}字节)")
        os.remove(output_file)
    else:
        logger.error("  ❌ Excel文件生成失败")
    
    logger.info("\n✅ Excel导出模块测试完成\n")


def test_data_processing_pipeline():
    """测试数据处理流程模块"""
    logger.info("=" * 70)
    logger.info("🧪 测试数据处理流程模块 (DataProcessingPipeline)")
    logger.info("=" * 70)
    
    from data_processing_pipeline import DataProcessingPipeline, ProcessingOrchestrator
    
    pipeline = DataProcessingPipeline(enable_local_db=False, enable_checkpoint=False)
    
    # 测试数据验证
    logger.info("\n📋 测试数据验证:")
    test_stocks = [
        {'code': '600000', 'name': '中国银行'},
        {'code': '000001', 'name': '平安银行'},
        {'code': 'invalid', 'name': '无效股票'},
    ]
    
    valid_stocks, validation_report = pipeline.validate_stocks(test_stocks)
    logger.info(f"  验证结果: {validation_report['valid']}有效, {validation_report['invalid']}无效")
    
    # 测试数据清洗
    logger.info("\n📋 测试数据清洗:")
    test_financial = [
        {
            'code': '600000',
            'name': '中国银行',
            'non_op_real_estate_2023': 1000000,
            'non_op_real_estate_2024': 1200000,
        },
    ]
    
    cleaned_data, cleaning_report = pipeline.clean_records(test_financial)
    logger.info(f"  清洗结果: 输入{cleaning_report['total_input']}, 输出{cleaning_report['total_output']}")
    
    # 测试统计生成
    logger.info("\n📋 测试统计生成:")
    stats = pipeline.generate_data_statistics(valid_stocks, cleaned_data, {})
    logger.info(f"  总股票数: {stats['total_stocks']}")
    logger.info(f"  总记录数: {stats['total_records']}")
    
    logger.info("\n✅ 数据处理流程模块测试完成\n")


def main():
    """主测试函数"""
    logger.info("\n")
    logger.info("=" * 70)
    logger.info("🚀 A股数据采集系统 v3.0 - 新增模块测试")
    logger.info("=" * 70)
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    tests = [
        ("数据验证模块", test_data_validator),
        ("本地存储模块", test_local_storage),
        ("质量监控模块", test_quality_monitor),
        ("断点续传模块", test_checkpoint_manager),
        ("Excel导出模块", test_excel_exporter),
        ("数据处理流程模块", test_data_processing_pipeline),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name}测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # 最终总结
    logger.info("\n" + "=" * 70)
    logger.info("📊 测试总结")
    logger.info("=" * 70)
    logger.info(f"✅ 通过: {passed}")
    logger.info(f"❌ 失败: {failed}")
    logger.info(f"📈 总数: {len(tests)}")
    logger.info("=" * 70)
    
    if failed == 0:
        logger.info("🎉 所有测试通过！")
        return 0
    else:
        logger.warning(f"⚠️ 有{failed}个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
