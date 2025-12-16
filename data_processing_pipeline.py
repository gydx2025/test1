#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理流程管理系统

集成数据验证、清洗、存储、质量监控等所有功能
"""

import logging
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import time

from data_validator import DataValidator, DataCleaner, DataDeduplication
from local_storage import LocalDatabase, CacheManager, CSVBackupManager, write_to_local_cache
from quality_monitor import DataQualityScore, DataQualityMonitor
from checkpoint_manager import CheckpointManager, IncrementalUpdate, VersionManager
from excel_exporter import ExcelReportGenerator

logger = logging.getLogger(__name__)


class DataProcessingPipeline:
    """数据处理流程管理系统"""
    
    def __init__(self, enable_local_db: bool = True, enable_checkpoint: bool = True):
        """
        初始化数据处理流程
        
        Args:
            enable_local_db: 是否启用本地数据库
            enable_checkpoint: 是否启用断点续传
        """
        self.validator = DataValidator()
        self.cleaner = DataCleaner(self.validator)
        self.quality_monitor = DataQualityMonitor()
        self.checkpoint_manager = None
        self.local_database = None
        self.cache_manager = CacheManager()
        self.version_manager = VersionManager()
        
        if enable_checkpoint:
            self.checkpoint_manager = CheckpointManager()
        
        if enable_local_db:
            self.local_database = LocalDatabase()
        
        self.validation_stats = {
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'validation_errors': {}
        }
        
        self.start_time = None
        self.end_time = None
    
    def validate_stocks(self, stocks: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        验证股票列表
        
        Args:
            stocks: 股票列表
            
        Returns:
            (有效的股票列表, 验证报告)
        """
        valid_stocks = []
        invalid_stocks = []
        validation_report = {
            'total': len(stocks),
            'valid': 0,
            'invalid': 0,
            'errors': []
        }
        
        for stock in stocks:
            valid, error = self.validator.validate_stock_code(stock.get('code'))
            valid2, error2 = self.validator.validate_stock_name(stock.get('name'))
            
            if valid and valid2:
                valid_stocks.append(stock)
                validation_report['valid'] += 1
            else:
                invalid_stocks.append({
                    'stock': stock,
                    'errors': [error, error2] if error and error2 else [error or error2]
                })
                validation_report['invalid'] += 1
                validation_report['errors'].append({
                    'code': stock.get('code'),
                    'error': error or error2
                })
        
        logger.info(f"股票验证完成: {len(valid_stocks)}有效, {len(invalid_stocks)}无效")
        
        return valid_stocks, validation_report
    
    def clean_records(self, records: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        清洗数据记录
        
        Args:
            records: 原始记录列表
            
        Returns:
            (清洗后的记录, 清洗报告)
        """
        self.start_time = time.time()
        
        cleaned_records = []
        cleaning_report = {
            'total_input': len(records),
            'total_output': 0,
            'cleaned': 0,
            'discarded': 0
        }
        
        # 重置清洗器计数
        self.cleaner.cleaned_count = 0
        self.cleaner.discarded_count = 0
        
        # 清洗每条记录
        for record in records:
            cleaned = self.cleaner.clean_record(record)
            if cleaned:
                # 进行额外验证
                valid, errors = self.validator.validate_record(cleaned)
                if valid:
                    cleaned_records.append(cleaned)
        
        cleaning_report['total_output'] = len(cleaned_records)
        cleaning_report['cleaned'] = self.cleaner.cleaned_count
        cleaning_report['discarded'] = self.cleaner.discarded_count
        
        logger.info(f"数据清洗完成: 输入{len(records)}, 输出{len(cleaned_records)}, "
                   f"清洗{self.cleaner.cleaned_count}, 丢弃{self.cleaner.discarded_count}")
        
        return cleaned_records, cleaning_report
    
    def deduplicate_records(self, records: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        去重处理
        
        Args:
            records: 记录列表
            
        Returns:
            (去重后的记录, 去重报告)
        """
        dedup_report = {
            'before_dedup': len(records),
            'after_dedup': 0,
            'duplicates_removed': 0
        }
        
        # 按code去重
        seen_codes = set()
        deduped = []
        
        for record in records:
            code = record.get('code')
            if code and code not in seen_codes:
                seen_codes.add(code)
                deduped.append(record)
        
        dedup_report['after_dedup'] = len(deduped)
        dedup_report['duplicates_removed'] = len(records) - len(deduped)
        
        logger.info(f"去重完成: 去重前{len(records)}, 去重后{len(deduped)}, "
                   f"重复{dedup_report['duplicates_removed']}")
        
        return deduped, dedup_report
    
    def generate_data_statistics(self, stocks: List[Dict], 
                                 financial_data: List[Dict],
                                 industries: Dict[str, Dict]) -> Dict:
        """
        生成数据统计信息
        
        Args:
            stocks: 股票列表
            financial_data: 财务数据
            industries: 行业分类
            
        Returns:
            统计信息字典
        """
        stats = {
            'total_stocks': len(stocks),
            'total_records': len(financial_data),
            'valid_records': len(financial_data),
            'validation_errors': len([r for r in financial_data if not r.get('valid', True)]),
            'stocks_with_industry': len(industries),
            'stocks_with_2023_data': 0,
            'stocks_with_2024_data': 0,
            'code_distribution': {
                '6': 0,  # 沪
                '0': 0,  # 深
                '3': 0,  # 创业板
                '8': 0,  # 北交所
                '4': 0   # 其他
            }
        }
        
        # 统计2023和2024年数据覆盖
        for record in financial_data:
            if record.get('non_op_real_estate_2023'):
                stats['stocks_with_2023_data'] += 1
            if record.get('non_op_real_estate_2024'):
                stats['stocks_with_2024_data'] += 1
        
        # 统计代码分布
        for stock in stocks:
            code = stock.get('code', '')
            if code:
                first_char = code[0]
                if first_char in stats['code_distribution']:
                    stats['code_distribution'][first_char] += 1
        
        # 计算覆盖率
        total = len(stocks)
        if total > 0:
            stats['industry_coverage_rate'] = len(industries) / total
            stats['data_2023_coverage_rate'] = stats['stocks_with_2023_data'] / total
            stats['data_2024_coverage_rate'] = stats['stocks_with_2024_data'] / total
            stats['data_completeness'] = (
                (stats['stocks_with_industry'] + 
                 stats['stocks_with_2023_data'] + 
                 stats['stocks_with_2024_data']) / (total * 3)
            )
        
        stats['collection_date'] = datetime.now().strftime('%Y-%m-%d')
        stats['collection_time'] = datetime.now().isoformat()
        
        return stats
    
    def save_to_local_storage(self, stocks: List[Dict], 
                             industries: Dict[str, Dict],
                             financial_data: List[Dict],
                             version: str = 'v3.0'):
        """
        保存数据到本地存储
        
        Args:
            stocks: 股票列表
            industries: 行业分类
            financial_data: 财务数据
            version: 版本号
        """
        if not self.local_database:
            logger.warning("本地数据库未启用")
            return
        
        try:
            self.local_database.backup_stocks(stocks)
            self.local_database.backup_industries(industries)
            self.local_database.backup_financial_data(financial_data)
            
            # 保存版本信息
            version_info = {
                'total_stocks': len(stocks),
                'total_industries': len(industries),
                'stocks_with_2023_data': len([r for r in financial_data if r.get('non_op_real_estate_2023')]),
                'stocks_with_2024_data': len([r for r in financial_data if r.get('non_op_real_estate_2024')]),
                'data_completeness': (len(industries) + 
                                     len([r for r in financial_data if r.get('non_op_real_estate_2023')]) +
                                     len([r for r in financial_data if r.get('non_op_real_estate_2024')])) / 
                                     (len(stocks) * 3) if stocks else 0,
                'notes': '完整版本'
            }
            self.local_database.save_version_info(version, version_info)

            # 写入本地缓存层（供快速查询/前缀搜索使用）
            write_to_local_cache(stocks=stocks, industries=industries, version=version)
            
            logger.info(f"数据已保存到本地存储")
            
        except Exception as e:
            logger.error(f"保存本地存储失败: {e}")
    
    def save_csv_backup(self, financial_data: List[Dict], filename: str):
        """
        保存CSV备份
        
        Args:
            financial_data: 财务数据
            filename: 文件名
        """
        CSVBackupManager.backup_to_csv(financial_data, filename)
    
    def generate_quality_report(self, stats: Dict) -> Dict:
        """
        生成质量报告
        
        Args:
            stats: 数据统计信息
            
        Returns:
            质量报告
        """
        monitoring_result = self.quality_monitor.monitor(stats)
        return monitoring_result
    
    def generate_final_report(self, stats: Dict, quality_report: Dict) -> Dict:
        """
        生成最终报告
        
        Args:
            stats: 数据统计
            quality_report: 质量报告
            
        Returns:
            最终报告
        """
        if self.start_time and not self.end_time:
            self.end_time = time.time()
        
        duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        final_report = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration,
            'duration_minutes': duration / 60,
            'statistics': stats,
            'quality_report': quality_report,
            'version': '3.0.0 - 完整版',
            'status': 'SUCCESS' if stats.get('data_completeness', 0) >= 0.98 else 'WARNING'
        }
        
        return final_report
    
    def close(self):
        """关闭所有资源"""
        if self.local_database:
            self.local_database.close()
        logger.info("数据处理流程已关闭")


class ProcessingOrchestrator:
    """数据处理流程编排器 - 管理整个数据处理流程"""
    
    def __init__(self):
        """初始化流程编排器"""
        self.pipeline = DataProcessingPipeline()
    
    def process_complete_pipeline(
        self,
        stocks: List[Dict],
        industries: Dict[str, Dict],
        financial_data: List[Dict],
        output_filename: str = None,
        csv_backup_filename: str = None
    ) -> Tuple[List[Dict], Dict, str]:
        """
        执行完整的数据处理流程
        
        Args:
            stocks: 原始股票列表
            industries: 原始行业分类
            financial_data: 原始财务数据
            output_filename: Excel输出文件名
            csv_backup_filename: CSV备份文件名
            
        Returns:
            (清洗后的财务数据, 最终报告, 输出文件路径)
        """
        logger.info("=" * 70)
        logger.info("🔄 开始数据处理流程")
        logger.info("=" * 70)
        
        # 步骤1: 验证股票列表
        logger.info("\n[步骤1] 验证股票列表...")
        valid_stocks, stock_validation = self.pipeline.validate_stocks(stocks)
        
        # 步骤2: 清洗财务数据
        logger.info("\n[步骤2] 清洗财务数据...")
        cleaned_data, cleaning_report = self.pipeline.clean_records(financial_data)
        
        # 步骤3: 去重处理
        logger.info("\n[步骤3] 去重处理...")
        deduped_data, dedup_report = self.pipeline.deduplicate_records(cleaned_data)
        
        # 步骤4: 生成统计信息
        logger.info("\n[步骤4] 生成统计信息...")
        stats = self.pipeline.generate_data_statistics(valid_stocks, deduped_data, industries)
        
        # 步骤5: 生成质量报告
        logger.info("\n[步骤5] 生成质量报告...")
        quality_report = self.pipeline.generate_quality_report(stats)
        
        # 步骤6: 保存本地存储
        logger.info("\n[步骤6] 保存本地存储...")
        self.pipeline.save_to_local_storage(valid_stocks, industries, deduped_data)
        
        # 步骤7: 保存CSV备份
        if csv_backup_filename:
            logger.info("\n[步骤7] 保存CSV备份...")
            self.pipeline.save_csv_backup(deduped_data, csv_backup_filename)
        
        # 步骤8: 生成最终报告
        logger.info("\n[步骤8] 生成最终报告...")
        final_report = self.pipeline.generate_final_report(stats, quality_report)
        
        # 步骤9: 生成Excel报告
        logger.info("\n[步骤9] 生成Excel报告...")
        if not output_filename:
            output_filename = f"A股非经营性房地产资产_完整版_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        metadata = {
            'collection_date': stats.get('collection_date'),
            'collection_time': stats.get('collection_time'),
            'version': final_report.get('version'),
            'sources': 'Multi-source aggregation',
            'duration': f"{final_report.get('duration_minutes', 0):.1f}分钟",
            'file_size': '',
            'notes': f"总计{stats.get('total_stocks')}只股票，数据完整度{stats.get('data_completeness', 0)*100:.1f}%"
        }
        
        excel_file = ExcelReportGenerator.generate_complete_report(
            valid_stocks,
            industries,
            deduped_data,
            {**stats, 'quality_report': quality_report},
            metadata,
            output_filename
        )
        
        # 打印最终报告
        logger.info("\n" + "=" * 70)
        logger.info("📊 数据处理完成总结")
        logger.info("=" * 70)
        logger.info(f"⏱️ 处理用时: {final_report['duration_minutes']:.1f}分钟 ({final_report['duration_seconds']:.0f}秒)")
        logger.info(f"📈 处理股票: {stats['total_stocks']}只")
        logger.info(f"✅ 有效数据: {len(deduped_data)}条")
        logger.info(f"📊 数据完整度: {stats['data_completeness']*100:.1f}%")
        logger.info(f"⭐ 质量评分: {quality_report['quality_score']['overall_score']:.1f}/100 [{quality_report['quality_score']['grade']}]")
        logger.info(f"📄 输出文件: {excel_file}")
        logger.info("=" * 70)
        
        # 打印质量报告
        quality_report_text = self.pipeline.quality_monitor.generate_report(quality_report)
        logger.info("\n" + quality_report_text)
        
        self.pipeline.close()
        
        return deduped_data, final_report, excel_file
