#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
断点续传和增量更新系统

提供检查点管理、增量更新、变更追踪等功能
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class CheckpointManager:
    """断点续传检查点管理系统"""
    
    def __init__(self, checkpoint_dir: str = 'checkpoints'):
        """
        初始化检查点管理器
        
        Args:
            checkpoint_dir: 检查点目录
        """
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
    
    def save_checkpoint(self, stage: str, progress: Dict):
        """
        保存检查点
        
        Args:
            stage: 阶段名称（如'stock_list', 'industry', 'financial'）
            progress: 进度信息
        """
        try:
            checkpoint_file = os.path.join(
                self.checkpoint_dir, 
                f'checkpoint_{stage}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )
            
            checkpoint_data = {
                'stage': stage,
                'timestamp': datetime.now().isoformat(),
                'progress': progress
            }
            
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"检查点已保存: {checkpoint_file}")
            
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
    
    def save_partial_results(self, stage: str, data: List[Dict], count: int):
        """
        保存部分处理结果（用于断点续传）
        
        Args:
            stage: 阶段名称
            data: 已处理的数据
            count: 处理计数
        """
        try:
            result_file = os.path.join(
                self.checkpoint_dir,
                f'partial_result_{stage}_{count}.json'
            )
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"部分结果已保存: {result_file} ({len(data)}条)")
            
        except Exception as e:
            logger.error(f"保存部分结果失败: {e}")
    
    def get_latest_checkpoint(self, stage: str) -> Optional[Dict]:
        """
        获取最新的检查点
        
        Args:
            stage: 阶段名称
            
        Returns:
            检查点数据或None
        """
        try:
            files = [f for f in os.listdir(self.checkpoint_dir) 
                    if f.startswith(f'checkpoint_{stage}_')]
            
            if not files:
                logger.info(f"未找到{stage}阶段的检查点")
                return None
            
            # 获取最新的文件
            latest_file = sorted(files)[-1]
            checkpoint_file = os.path.join(self.checkpoint_dir, latest_file)
            
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            logger.info(f"已加载最新检查点: {checkpoint_file}")
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None
    
    def resume_from_checkpoint(self, stage: str) -> Optional[Dict]:
        """
        从检查点恢复
        
        Args:
            stage: 阶段名称
            
        Returns:
            进度信息或None
        """
        checkpoint = self.get_latest_checkpoint(stage)
        if checkpoint:
            logger.info(f"从{checkpoint['timestamp']}恢复{stage}阶段")
            return checkpoint.get('progress')
        return None
    
    def clear_checkpoints(self, stage: Optional[str] = None):
        """
        清空检查点
        
        Args:
            stage: 阶段名称，None表示清空所有
        """
        try:
            if stage:
                files = [f for f in os.listdir(self.checkpoint_dir) 
                        if f.startswith(f'checkpoint_{stage}_')]
            else:
                files = os.listdir(self.checkpoint_dir)
            
            for file in files:
                os.remove(os.path.join(self.checkpoint_dir, file))
            
            logger.info(f"检查点已清空: {stage or '全部'}")
            
        except Exception as e:
            logger.error(f"清空检查点失败: {e}")


class IncrementalUpdate:
    """增量更新管理系统"""
    
    def __init__(self, previous_data_file: Optional[str] = None):
        """
        初始化增量更新管理器
        
        Args:
            previous_data_file: 前一次采集的数据文件路径
        """
        self.previous_data_file = previous_data_file
        self.previous_data = {}
        self.load_previous_data()
    
    def load_previous_data(self):
        """加载前一次的数据"""
        if self.previous_data_file and os.path.exists(self.previous_data_file):
            try:
                with open(self.previous_data_file, 'r', encoding='utf-8') as f:
                    self.previous_data = json.load(f)
                logger.info(f"已加载前一次数据: {self.previous_data_file}")
            except Exception as e:
                logger.error(f"加载前一次数据失败: {e}")
    
    def compare_stocks(self, current_stocks: List[Dict]) -> Dict:
        """
        比较股票列表变化
        
        Args:
            current_stocks: 当前采集的股票列表
            
        Returns:
            变化分析
        """
        # 构建code集合
        previous_codes = set(stock.get('code') for stock in self.previous_data.get('stocks', []))
        current_codes = set(stock.get('code') for stock in current_stocks)
        
        # 计算变化
        new_stocks = current_codes - previous_codes
        delisted_stocks = previous_codes - current_codes
        unchanged_stocks = previous_codes & current_codes
        
        # 获取新上市和退市的详细信息
        new_stock_details = [s for s in current_stocks if s.get('code') in new_stocks]
        
        return {
            'new_stocks': list(new_stocks),
            'new_stock_count': len(new_stocks),
            'new_stock_details': new_stock_details,
            'delisted_stocks': list(delisted_stocks),
            'delisted_stock_count': len(delisted_stocks),
            'unchanged_stocks': unchanged_stocks,
            'unchanged_stock_count': len(unchanged_stocks),
            'total_current': len(current_stocks),
            'total_previous': len(self.previous_data.get('stocks', []))
        }
    
    def compare_financial_data(self, current_data: List[Dict]) -> Dict:
        """
        比较财务数据变化
        
        Args:
            current_data: 当前采集的财务数据
            
        Returns:
            变化分析
        """
        previous_data_map = {
            item['code']: item 
            for item in self.previous_data.get('financial', [])
        }
        
        updated_records = []
        unchanged_records = []
        
        for current_item in current_data:
            code = current_item.get('code')
            
            if code not in previous_data_map:
                # 新增
                updated_records.append({
                    'code': code,
                    'change': 'new',
                    'details': current_item
                })
            else:
                previous_item = previous_data_map[code]
                
                # 比较关键字段是否变化
                changed = False
                for year in ['2023', '2024']:
                    key = f'non_op_real_estate_{year}'
                    if current_item.get(key) != previous_item.get(key):
                        changed = True
                        break
                
                if changed:
                    updated_records.append({
                        'code': code,
                        'change': 'updated',
                        'previous': previous_item,
                        'current': current_item
                    })
                else:
                    unchanged_records.append(code)
        
        return {
            'updated_records': updated_records,
            'updated_count': len(updated_records),
            'unchanged_count': len(unchanged_records),
            'new_count': len([r for r in updated_records if r['change'] == 'new']),
            'modified_count': len([r for r in updated_records if r['change'] == 'updated'])
        }
    
    def generate_changelog(self, changes: Dict) -> str:
        """
        生成变更日志
        
        Args:
            changes: 变更信息
            
        Returns:
            变更日志文本
        """
        lines = []
        lines.append("=" * 70)
        lines.append("📝 数据变更日志")
        lines.append("=" * 70)
        lines.append(f"生成时间: {datetime.now().isoformat()}")
        
        if 'stock_changes' in changes:
            stock_changes = changes['stock_changes']
            lines.append(f"\n📈 股票列表变化:")
            lines.append(f"  • 新上市: {stock_changes['new_stock_count']}家")
            lines.append(f"  • 退市: {stock_changes['delisted_stock_count']}家")
            lines.append(f"  • 不变: {stock_changes['unchanged_stock_count']}家")
            lines.append(f"  • 总数: {stock_changes['total_previous']} → {stock_changes['total_current']}")
            
            if stock_changes['new_stock_count'] > 0:
                lines.append(f"\n  🆕 新上市公司:")
                for stock in stock_changes['new_stock_details'][:10]:  # 只显示前10个
                    lines.append(f"     - {stock.get('code')} {stock.get('name')}")
                if stock_changes['new_stock_count'] > 10:
                    lines.append(f"     ... 还有{stock_changes['new_stock_count'] - 10}家")
            
            if stock_changes['delisted_stock_count'] > 0:
                lines.append(f"\n  ❌ 退市公司: {stock_changes['delisted_stock_count']}家")
        
        if 'financial_changes' in changes:
            financial_changes = changes['financial_changes']
            lines.append(f"\n💰 财务数据变化:")
            lines.append(f"  • 新增: {financial_changes['new_count']}条")
            lines.append(f"  • 更新: {financial_changes['modified_count']}条")
            lines.append(f"  • 不变: {financial_changes['unchanged_count']}条")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def save_changelog(self, changes: Dict, filename: str = None):
        """
        保存变更日志到文件
        
        Args:
            changes: 变更信息
            filename: 文件名，默认为 changelog_{timestamp}.txt
        """
        if not filename:
            filename = f"changelog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            content = self.generate_changelog(changes)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"变更日志已保存: {filename}")
        except Exception as e:
            logger.error(f"保存变更日志失败: {e}")


class VersionManager:
    """版本管理系统"""
    
    def __init__(self, history_file: str = 'version_history.json'):
        """
        初始化版本管理器
        
        Args:
            history_file: 版本历史文件
        """
        self.history_file = history_file
        self.history = self.load_history()
    
    def load_history(self) -> List[Dict]:
        """加载版本历史"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载版本历史失败: {e}")
        return []
    
    def save_history(self):
        """保存版本历史"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存版本历史失败: {e}")
    
    def record_version(self, version: str, metadata: Dict):
        """
        记录新版本
        
        Args:
            version: 版本号
            metadata: 版本元数据
        """
        entry = {
            'version': version,
            'timestamp': datetime.now().isoformat(),
            'total_stocks': metadata.get('total_stocks'),
            'total_records': metadata.get('total_records'),
            'data_completeness': metadata.get('data_completeness'),
            'notes': metadata.get('notes', '')
        }
        
        self.history.append(entry)
        self.save_history()
        logger.info(f"版本已记录: {version}")
    
    def get_version_history(self) -> List[Dict]:
        """获取完整的版本历史"""
        return self.history
    
    def get_latest_version(self) -> Optional[Dict]:
        """获取最新版本信息"""
        if self.history:
            return self.history[-1]
        return None
