#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量监控和评分系统

提供数据质量评分、监控、报告生成等功能
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class DataQualityScore:
    """数据质量评分系统"""
    
    # 评分权重
    WEIGHTS = {
        'completeness': 0.30,      # 完整度 30%
        'accuracy': 0.30,           # 准确度 30%
        'timeliness': 0.20,         # 及时性 20%
        'coverage': 0.20,           # 覆盖度 20%
    }
    
    # 标准值
    STANDARDS = {
        'total_stocks': 5434,       # 标准A股数量
        'min_completeness': 0.98,   # 最低完整度 98%
        'min_accuracy': 0.95,       # 最低准确度 95%
        'industry_coverage': 0.95,  # 行业覆盖率 95%
    }
    
    def __init__(self):
        """初始化评分系统"""
        self.validation_errors = []
        self.validation_warnings = []
        self.metrics = {}
    
    def calculate_completeness_score(self, data_stats: Dict) -> Tuple[float, str]:
        """
        计算完整度评分
        
        完整度 = (实际获取的股票数 / 标准总数) * 100
        
        Args:
            data_stats: 数据统计字典
            
        Returns:
            (评分, 说明)
        """
        total_stocks = data_stats.get('total_stocks', 0)
        standard_total = self.STANDARDS['total_stocks']
        
        completeness = (total_stocks / standard_total) * 100 if standard_total > 0 else 0
        completeness = min(100, completeness)  # 上限100
        
        # 转换为0-100分
        score = completeness
        
        if completeness >= 98:
            status = "优秀"
        elif completeness >= 95:
            status = "良好"
        elif completeness >= 90:
            status = "一般"
        else:
            status = "不足"
        
        explanation = f"获取{total_stocks}只股票，标准{standard_total}只，完整度{completeness:.1f}% - {status}"
        
        return score, explanation
    
    def calculate_accuracy_score(self, data_stats: Dict) -> Tuple[float, str]:
        """
        计算准确度评分
        
        准确度 = (有效数据条数 / 总数据条数) * 100
        
        Args:
            data_stats: 数据统计字典
            
        Returns:
            (评分, 说明)
        """
        valid_records = data_stats.get('valid_records', 0)
        total_records = data_stats.get('total_records', 0)
        validation_errors = data_stats.get('validation_errors', 0)
        
        if total_records == 0:
            accuracy = 0
        else:
            accuracy = (valid_records / total_records) * 100
        
        accuracy = min(100, accuracy)
        
        if accuracy >= 95:
            status = "优秀"
        elif accuracy >= 90:
            status = "良好"
        elif accuracy >= 85:
            status = "一般"
        else:
            status = "不足"
        
        explanation = f"有效数据{valid_records}条，总计{total_records}条，准确度{accuracy:.1f}% - {status}"
        if validation_errors > 0:
            explanation += f"（包含{validation_errors}条验证错误）"
        
        return accuracy, explanation
    
    def calculate_timeliness_score(self, data_stats: Dict) -> Tuple[float, str]:
        """
        计算及时性评分
        
        检查数据是否为今日采集
        
        Args:
            data_stats: 数据统计字典
            
        Returns:
            (评分, 说明)
        """
        collection_date = data_stats.get('collection_date')
        
        if not collection_date:
            return 0, "未知采集日期"
        
        try:
            # 简单检查是否是今日
            from datetime import datetime as dt
            
            if isinstance(collection_date, str):
                # 假设格式为 "2024-12-13"
                collection_dt = dt.strptime(collection_date.split()[0], '%Y-%m-%d')
            else:
                collection_dt = collection_date
            
            today = dt.now()
            days_old = (today - collection_dt).days
            
            if days_old == 0:
                score = 100
                status = "最新"
            elif days_old <= 7:
                score = 80 - (days_old * 5)
                status = "较新"
            elif days_old <= 30:
                score = 40 - ((days_old - 7) * 2)
                status = "一般"
            else:
                score = 10
                status = "陈旧"
            
            score = max(0, min(100, score))
            explanation = f"采集于{days_old}天前（{collection_date}），数据状态 - {status}"
            
            return score, explanation
            
        except Exception as e:
            logger.warning(f"计算及时性评分时出错: {e}")
            return 50, "无法确定采集日期"
    
    def calculate_coverage_score(self, data_stats: Dict) -> Tuple[float, str]:
        """
        计算覆盖度评分
        
        主要考查：
        - 行业分类覆盖率
        - 财务数据覆盖率（2023、2024）
        
        Args:
            data_stats: 数据统计字典
            
        Returns:
            (评分, 说明)
        """
        total_stocks = data_stats.get('total_stocks', 0)
        stocks_with_industry = data_stats.get('stocks_with_industry', 0)
        stocks_with_2023 = data_stats.get('stocks_with_2023_data', 0)
        stocks_with_2024 = data_stats.get('stocks_with_2024_data', 0)
        
        if total_stocks == 0:
            return 0, "没有可计算的数据"
        
        # 计算各项覆盖率
        industry_coverage = (stocks_with_industry / total_stocks) * 100 if total_stocks > 0 else 0
        data_2023_coverage = (stocks_with_2023 / total_stocks) * 100 if total_stocks > 0 else 0
        data_2024_coverage = (stocks_with_2024 / total_stocks) * 100 if total_stocks > 0 else 0
        
        # 综合覆盖率（权重：行业40%，2023数据30%，2024数据30%）
        avg_coverage = (industry_coverage * 0.4 + data_2023_coverage * 0.3 + data_2024_coverage * 0.3)
        
        if avg_coverage >= 95:
            status = "优秀"
        elif avg_coverage >= 85:
            status = "良好"
        elif avg_coverage >= 75:
            status = "一般"
        else:
            status = "不足"
        
        explanation = (f"行业分类覆盖{industry_coverage:.1f}%，"
                      f"2023数据覆盖{data_2023_coverage:.1f}%，"
                      f"2024数据覆盖{data_2024_coverage:.1f}% - {status}")
        
        return avg_coverage, explanation
    
    def calculate_overall_score(self, data_stats: Dict) -> Dict:
        """
        计算综合评分
        
        Args:
            data_stats: 数据统计字典
            
        Returns:
            评分报告字典
        """
        self.metrics = {}
        
        # 计算各项评分
        completeness_score, completeness_explain = self.calculate_completeness_score(data_stats)
        accuracy_score, accuracy_explain = self.calculate_accuracy_score(data_stats)
        timeliness_score, timeliness_explain = self.calculate_timeliness_score(data_stats)
        coverage_score, coverage_explain = self.calculate_coverage_score(data_stats)
        
        self.metrics['completeness'] = {
            'score': completeness_score,
            'explanation': completeness_explain
        }
        self.metrics['accuracy'] = {
            'score': accuracy_score,
            'explanation': accuracy_explain
        }
        self.metrics['timeliness'] = {
            'score': timeliness_score,
            'explanation': timeliness_explain
        }
        self.metrics['coverage'] = {
            'score': coverage_score,
            'explanation': coverage_explain
        }
        
        # 计算综合评分
        overall_score = (
            completeness_score * self.WEIGHTS['completeness'] +
            accuracy_score * self.WEIGHTS['accuracy'] +
            timeliness_score * self.WEIGHTS['timeliness'] +
            coverage_score * self.WEIGHTS['coverage']
        )
        
        # 确定评级
        if overall_score >= 95:
            grade = "A+（优秀）"
        elif overall_score >= 90:
            grade = "A（很好）"
        elif overall_score >= 85:
            grade = "B+（良好）"
        elif overall_score >= 80:
            grade = "B（一般）"
        elif overall_score >= 70:
            grade = "C（较差）"
        else:
            grade = "D（不足）"
        
        return {
            'overall_score': overall_score,
            'grade': grade,
            'metrics': self.metrics,
            'timestamp': datetime.now().isoformat()
        }


class DataQualityMonitor:
    """数据质量监控系统"""
    
    def __init__(self):
        """初始化监控系统"""
        self.quality_score = DataQualityScore()
        self.issues = []
        self.warnings = []
        self.suggestions = []
    
    def monitor(self, data_stats: Dict) -> Dict:
        """
        监控数据质量
        
        Args:
            data_stats: 数据统计字典
            
        Returns:
            监控报告
        """
        self.issues = []
        self.warnings = []
        self.suggestions = []
        
        # 检查完整度
        total_stocks = data_stats.get('total_stocks', 0)
        if total_stocks < 5434 * 0.98:
            self.issues.append(f"完整度不足：{total_stocks}只，标准{5434}只")
            self.suggestions.append("建议尝试多个数据源获取更多股票")
        
        # 检查准确度
        validation_errors = data_stats.get('validation_errors', 0)
        if validation_errors > 0:
            error_rate = validation_errors / data_stats.get('total_records', 1) * 100
            if error_rate > 5:
                self.warnings.append(f"数据验证错误率较高：{error_rate:.1f}%")
                self.suggestions.append("建议检查数据源质量或调整验证规则")
        
        # 检查行业覆盖
        stocks_with_industry = data_stats.get('stocks_with_industry', 0)
        if stocks_with_industry < total_stocks * 0.95:
            self.warnings.append(f"行业分类覆盖率不足：{stocks_with_industry / total_stocks * 100:.1f}%")
            self.suggestions.append("建议使用多个行业分类数据源进行补全")
        
        # 检查财务数据
        stocks_with_2024 = data_stats.get('stocks_with_2024_data', 0)
        if stocks_with_2024 < total_stocks * 0.90:
            self.warnings.append(f"2024年财务数据缺失：仅{stocks_with_2024 / total_stocks * 100:.1f}%覆盖")
            self.suggestions.append("建议继续补全2024年财务数据")
        
        # 计算质量评分
        quality_report = self.quality_score.calculate_overall_score(data_stats)
        
        return {
            'quality_score': quality_report,
            'issues': self.issues,
            'warnings': self.warnings,
            'suggestions': self.suggestions,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_report(self, monitoring_result: Dict) -> str:
        """
        生成监控报告
        
        Args:
            monitoring_result: 监控结果
            
        Returns:
            报告文本
        """
        lines = []
        lines.append("=" * 70)
        lines.append("📊 数据质量监控报告")
        lines.append("=" * 70)
        
        # 综合评分
        quality = monitoring_result['quality_score']
        lines.append(f"\n⭐ 综合评分: {quality['overall_score']:.1f}/100 [{quality['grade']}]")
        
        # 各项评分
        lines.append("\n📈 各项评分详情：")
        for metric_name, metric_data in quality['metrics'].items():
            score = metric_data['score']
            explanation = metric_data['explanation']
            lines.append(f"  • {metric_name.upper()}: {score:.1f}/100 - {explanation}")
        
        # 问题清单
        if monitoring_result['issues']:
            lines.append("\n❌ 发现的问题：")
            for issue in monitoring_result['issues']:
                lines.append(f"  • {issue}")
        
        # 警告清单
        if monitoring_result['warnings']:
            lines.append("\n⚠️ 发现的警告：")
            for warning in monitoring_result['warnings']:
                lines.append(f"  • {warning}")
        
        # 改进建议
        if monitoring_result['suggestions']:
            lines.append("\n💡 改进建议：")
            for suggestion in monitoring_result['suggestions']:
                lines.append(f"  • {suggestion}")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
