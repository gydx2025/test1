#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化测试脚本

验证：
1. 并发获取功能正常
2. 快速失败策略应用
3. 配置参数正确
"""

import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入模块
from config import CONCURRENT_CONFIG, FAST_FAIL_CONFIG, REQUEST_CONFIG
from concurrent_data_fetcher import ConcurrentDataFetcher
from industry_classification_complete_getter import IndustryClassificationCompleteGetter


def test_config_optimization():
    """测试配置是否正确优化"""
    logger.info("=" * 60)
    logger.info("测试1：配置优化验证")
    logger.info("=" * 60)
    
    # 检查并发配置
    logger.info(f"并发配置启用: {CONCURRENT_CONFIG.get('enabled')}")
    logger.info(f"最大并发线程数: {CONCURRENT_CONFIG.get('max_workers')}")
    logger.info(f"快速失败策略: {CONCURRENT_CONFIG.get('use_fast_fail')}")
    
    # 检查快速失败配置
    logger.info(f"请求超时: {FAST_FAIL_CONFIG.get('request_timeout')}秒")
    logger.info(f"最大重试次数: {FAST_FAIL_CONFIG.get('max_retries')}")
    logger.info(f"重试延迟: {FAST_FAIL_CONFIG.get('retry_delays')}")
    logger.info(f"最小成功率阈值: {FAST_FAIL_CONFIG.get('min_success_rate')*100:.1f}%")
    
    # 检查请求配置
    logger.info(f"请求延迟范围: {REQUEST_CONFIG['delay_between_requests']}")
    logger.info(f"最大重试次数: {REQUEST_CONFIG['max_retries']}")
    
    # 验证优化参数
    assert CONCURRENT_CONFIG.get('max_workers', 5) >= 1, "并发线程数必须 >= 1"
    assert FAST_FAIL_CONFIG.get('request_timeout', 10) <= 20, "请求超时应该 <= 20秒"
    assert REQUEST_CONFIG['max_retries'] <= 5, "重试次数应该 <= 5"
    
    logger.info("✅ 配置优化验证通过\n")


def mock_fetch_function(stock_code: str, stock_name: str) -> dict:
    """模拟的股票数据获取函数"""
    time.sleep(0.1)  # 模拟网络请求时间
    return {
        'real_estate_2023': 1000000,
        'real_estate_2024': 1500000,
        'shenwan_level1': '房地产',
        'shenwan_level2': '房地产开发',
        'shenwan_level3': '房地产开发',
        'source': 'mock'
    }


def test_concurrent_fetcher():
    """测试并发获取器"""
    logger.info("=" * 60)
    logger.info("测试2：并发获取器功能")
    logger.info("=" * 60)
    
    # 创建测试数据
    test_stocks = [
        {'code': '000001', 'name': '平安银行'},
        {'code': '000002', 'name': '万科A'},
        {'code': '000858', 'name': '五粮液'},
        {'code': '600036', 'name': '招商银行'},
        {'code': '600519', 'name': '贵州茅台'},
    ]
    
    # 创建并发获取器
    fetcher = ConcurrentDataFetcher(
        fetch_func=mock_fetch_function,
        max_workers=2,  # 测试用2个线程
        logger_obj=logger
    )
    
    # 测试并发获取
    start_time = time.time()
    results, stats = fetcher.fetch_concurrent(test_stocks, show_progress=False)
    elapsed = time.time() - start_time
    
    # 验证结果
    assert len(results) == len(test_stocks), f"结果数量不符: {len(results)} vs {len(test_stocks)}"
    assert stats['success'] == len(test_stocks), "所有股票应该获取成功"
    assert stats['success_rate'] == 1.0, "成功率应该是100%"
    
    logger.info(f"✅ 并发获取成功: {len(results)}/{len(test_stocks)} 只股票")
    logger.info(f"⏱️ 耗时: {elapsed:.2f}秒（平均 {stats['avg_time']:.2f}秒/个）")
    
    # 计算性能提升
    # 串行处理时间估计（每个 0.1秒 + 0.1秒延迟）
    serial_time = len(test_stocks) * 0.2
    speedup = serial_time / elapsed
    logger.info(f"🚀 性能提升: {speedup:.1f}倍（从{serial_time:.1f}秒 → {elapsed:.1f}秒）\n")


def test_industry_classification_getter():
    """测试行业分类获取器的源过滤"""
    logger.info("=" * 60)
    logger.info("测试3：行业分类获取器源过滤")
    logger.info("=" * 60)
    
    # 创建行业分类获取器
    getter = IndustryClassificationCompleteGetter(logger=logger)
    
    # 验证源过滤功能
    test_sources = [
        ('eastmoney_quote', {'name': '东方财富行情', 'priority': 1}),
        ('sina_shenwan', {'name': '新浪财经', 'priority': 3}),
        ('tencent_quote', {'name': '腾讯财经', 'priority': 5}),
        ('netease_f10', {'name': '网易财经', 'priority': 6}),
    ]
    
    # 执行源过滤
    active_sources = getter._filter_sources_by_success_rate(
        test_sources,
        min_success_rate=0.05,
        show_progress=True
    )
    
    # 验证过滤结果
    source_names = [s[1]['name'] for s in active_sources]
    
    # 腾讯财经和网易财经应该被过滤掉（成功率0%）
    assert '腾讯财经' not in source_names, "腾讯财经应该被过滤"
    assert '网易财经' not in source_names, "网易财经应该被过滤"
    assert '东方财富行情' in source_names, "东方财富应该被保留"
    assert '新浪财经' in source_names, "新浪财经应该被保留"
    
    logger.info(f"✅ 源过滤成功: 保留{len(active_sources)}/{len(test_sources)}个源\n")


def test_performance_estimate():
    """性能提升估计"""
    logger.info("=" * 60)
    logger.info("测试4：性能提升估计")
    logger.info("=" * 60)
    
    # 参数
    total_stocks = 5171
    max_workers = CONCURRENT_CONFIG.get('max_workers', 5)
    avg_delay = 0.35  # (0.2 + 0.5) / 2
    
    # 串行处理时间
    serial_time = total_stocks * (avg_delay + 0.1)  # 加上网络请求时间
    
    # 并发处理时间（理想情况）
    concurrent_time = (total_stocks / max_workers) * (avg_delay + 0.1)
    
    # 实际并发时间（考虑开销）
    actual_concurrent_time = concurrent_time * 1.1
    
    # 性能提升
    speedup = serial_time / actual_concurrent_time
    
    logger.info(f"总股票数: {total_stocks}")
    logger.info(f"并发线程数: {max_workers}")
    logger.info(f"平均延迟: {avg_delay}秒")
    logger.info("")
    logger.info(f"串行处理时间: {serial_time/60:.1f}分钟 ({serial_time:.0f}秒)")
    logger.info(f"并发处理时间: {actual_concurrent_time/60:.1f}分钟 ({actual_concurrent_time:.0f}秒)")
    logger.info(f"性能提升: {speedup:.1f}倍")
    logger.info("")
    logger.info(f"✅ 预期提升: 从{serial_time/3600:.1f}小时 → {actual_concurrent_time/3600:.1f}小时\n")


def main():
    """运行所有测试"""
    logger.info("\n")
    logger.info("🧪 性能优化测试套件")
    logger.info("=" * 60)
    
    try:
        # 运行测试
        test_config_optimization()
        test_concurrent_fetcher()
        test_industry_classification_getter()
        test_performance_estimate()
        
        logger.info("=" * 60)
        logger.info("✅ 所有测试通过！")
        logger.info("=" * 60)
        
        return 0
        
    except AssertionError as e:
        logger.error(f"❌ 测试失败: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
