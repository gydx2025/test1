#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证和清洗系统

提供完整的数据验证、清洗、去重和合并机制
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class DataValidator:
    """数据验证系统"""
    
    # A股代码的合法首位
    VALID_FIRST_CHARS = {'0', '3', '4', '6', '8'}
    # 28个标准一级行业
    STANDARD_L1_INDUSTRIES = {
        '农业', '采矿业', '制造业', '电力、热力、燃气及水生产和供应业',
        '建筑业', '批发和零售业', '交通运输、仓储和邮政业', '住宿和餐饮业',
        '信息传输、软件和信息技术服务业', '金融业', '房地产业',
        '租赁和商务服务业', '科学研究和技术服务业', '水利、环境和公共设施管理业',
        '居民服务、修理和其他服务业', '教育', '卫生和社会工作', '文化、体育和娱乐业',
        '综合', '石油、煤炭及其他燃料加工业', '化工', '非金属矿物制品业',
        '黑色金属冶炼和压延加工业', '有色金属冶炼和压延加工业',
        '金属制品业', '通用设备制造业', '专用设备制造业', '汽车制造业'
    }
    
    def __init__(self):
        """初始化验证器"""
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_stock_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        验证股票代码格式
        
        Args:
            code: 股票代码
            
        Returns:
            (是否有效, 错误信息)
        """
        if not code:
            return False, "代码为空"
        
        code = str(code).strip()
        
        # 检查长度
        if len(code) != 6:
            return False, f"代码长度不是6位: {code}"
        
        # 检查是否全是数字
        if not code.isdigit():
            return False, f"代码包含非数字字符: {code}"
        
        # 检查首位
        if code[0] not in self.VALID_FIRST_CHARS:
            return False, f"代码首位非法(不是0/3/4/6/8): {code}"
        
        # 拒绝明显错误的代码（920000等）
        if code.startswith('92'):
            return False, f"代码为错误代码(920000系列): {code}"
        
        return True, None
    
    def validate_stock_name(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        验证公司名称
        
        Args:
            name: 公司名称
            
        Returns:
            (是否有效, 错误信息)
        """
        if not name:
            return False, "名称为空"
        
        name = str(name).strip()
        
        # 检查长度
        if len(name) < 2 or len(name) > 100:
            return False, f"名称长度不合理: {name}"
        
        # 检查特殊字符（允许中文、英文、数字、括号、杠）
        if re.search(r'[<>\"\'\\|?*]', name):
            return False, f"名称包含非法字符: {name}"
        
        return True, None
    
    def validate_financial_data(self, data: Dict) -> Tuple[bool, Optional[str]]:
        """
        验证财务数据
        
        Args:
            data: 财务数据字典
            
        Returns:
            (是否有效, 错误信息)
        """
        if not data:
            return False, "数据为空"
        
        # 检查必要的字段
        required_fields = ['code', 'name']
        for field in required_fields:
            if field not in data or not data[field]:
                return False, f"缺少必要字段: {field}"
        
        # 验证财务数值
        for year in ['2023', '2024']:
            key = f'non_op_real_estate_{year}'
            if key in data and data[key] is not None:
                try:
                    value = float(data[key])
                    if value < 0:
                        return False, f"{year}年资产为负数: {value}"
                    if value > 1e12:  # 超过1万亿
                        return False, f"{year}年资产过大(>1万亿): {value}"
                except (ValueError, TypeError):
                    return False, f"{year}年资产无法转换为数字: {data[key]}"
        
        return True, None
    
    def validate_industry_classification(self, industry: Dict) -> Tuple[bool, Optional[str]]:
        """
        验证申万行业分类
        
        Args:
            industry: 行业分类字典 {l1, l2, l3}
            
        Returns:
            (是否有效, 错误信息)
        """
        if not industry:
            return False, "行业分类为空"
        
        # 检查必要的字段
        if 'l1' not in industry or not industry['l1']:
            return False, "缺少一级行业分类"
        
        # 验证一级行业是否在标准列表中
        l1 = str(industry['l1']).strip()
        if l1 not in self.STANDARD_L1_INDUSTRIES:
            # 允许部分非标准行业，但记录警告
            logger.warning(f"非标准一级行业: {l1}")
        
        # 验证二级和三级（如果存在）
        if 'l2' in industry and industry['l2']:
            l2 = str(industry['l2']).strip()
            if len(l2) > 50:
                return False, f"二级行业分类过长: {l2}"
        
        if 'l3' in industry and industry['l3']:
            l3 = str(industry['l3']).strip()
            if len(l3) > 50:
                return False, f"三级行业分类过长: {l3}"
        
        return True, None
    
    def validate_record(self, record: Dict) -> Tuple[bool, List[str]]:
        """
        验证完整的数据记录
        
        Args:
            record: 数据记录
            
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        # 验证股票代码
        code = record.get('code')
        valid, error = self.validate_stock_code(code)
        if not valid:
            errors.append(f"代码错误: {error}")
        
        # 验证公司名称
        name = record.get('name')
        valid, error = self.validate_stock_name(name)
        if not valid:
            errors.append(f"名称错误: {error}")
        
        # 验证财务数据
        valid, error = self.validate_financial_data(record)
        if not valid:
            errors.append(f"财务数据错误: {error}")
        
        # 验证行业分类（如果存在）
        if 'industry' in record and record['industry']:
            valid, error = self.validate_industry_classification(record['industry'])
            if not valid:
                errors.append(f"行业分类错误: {error}")
        
        return len(errors) == 0, errors


class DataCleaner:
    """数据清洗系统"""
    
    def __init__(self, validator: Optional[DataValidator] = None):
        """初始化清洗器"""
        self.validator = validator or DataValidator()
        self.cleaned_count = 0
        self.discarded_count = 0
        self.fixed_count = 0
    
    def clean_stock_code(self, code: str) -> Optional[str]:
        """清洗股票代码"""
        if not code:
            return None
        
        code = str(code).strip()
        
        # 去除不必要的前缀（如'sh'、'sz'）
        code = re.sub(r'^[a-zA-Z]{2}', '', code)
        code = code.strip()
        
        # 验证
        valid, _ = self.validator.validate_stock_code(code)
        if valid:
            return code
        return None
    
    def clean_stock_name(self, name: str) -> Optional[str]:
        """清洗公司名称"""
        if not name:
            return None
        
        name = str(name).strip()
        
        # 移除不必要的空白
        name = ' '.join(name.split())
        
        # 移除括号内的特殊信息
        name = re.sub(r'\(.*\)|\（.*\）', '', name).strip()
        
        # 验证
        valid, _ = self.validator.validate_stock_name(name)
        if valid:
            return name
        return None
    
    def clean_financial_value(self, value, allow_zero: bool = True) -> Optional[float]:
        """清洗财务数值"""
        if value is None:
            return None
        
        try:
            # 处理字符串中的中文数字单位
            value_str = str(value).strip()
            
            # 处理千位分隔符
            value_str = value_str.replace(',', '')
            
            # 处理单位（万元、百万元等）
            if '万' in value_str:
                value_str = value_str.replace('万', '')
                value = float(value_str) * 10000
            elif '百万' in value_str:
                value_str = value_str.replace('百万', '')
                value = float(value_str) * 1000000
            else:
                value = float(value_str)
            
            # 检查范围
            if value < 0:
                logger.warning(f"负数财务值被设为0: {value}")
                return 0 if allow_zero else None
            
            if value > 1e12:
                logger.warning(f"异常大的财务值: {value}")
                return None
            
            return value
        except (ValueError, TypeError):
            return None
    
    def clean_record(self, record: Dict) -> Optional[Dict]:
        """
        清洗单条记录
        
        Args:
            record: 原始记录
            
        Returns:
            清洗后的记录或None（如果无法清洗）
        """
        if not record:
            return None
        
        cleaned = {}
        
        # 清洗股票代码
        code = self.clean_stock_code(record.get('code'))
        if not code:
            self.discarded_count += 1
            return None
        cleaned['code'] = code
        
        # 清洗公司名称
        name = self.clean_stock_name(record.get('name'))
        if not name:
            self.discarded_count += 1
            return None
        cleaned['name'] = name
        
        # 清洗财务数据
        for year in ['2023', '2024']:
            key = f'non_op_real_estate_{year}'
            if key in record:
                value = self.clean_financial_value(record[key])
                cleaned[key] = value
            else:
                cleaned[key] = None
        
        # 清洗行业分类
        if 'industry' in record and record['industry']:
            cleaned['industry'] = record['industry']
        else:
            cleaned['industry'] = None
        
        # 清洗其他字段
        for key in ['market', 'list_date', 'data_source']:
            if key in record:
                cleaned[key] = record[key]
        
        # 验证清洗后的记录
        valid, _ = self.validator.validate_record(cleaned)
        if valid:
            self.cleaned_count += 1
        
        return cleaned
    
    def clean_records(self, records: List[Dict]) -> List[Dict]:
        """
        批量清洗记录
        
        Args:
            records: 原始记录列表
            
        Returns:
            清洗后的记录列表
        """
        cleaned_records = []
        
        for record in records:
            cleaned = self.clean_record(record)
            if cleaned:
                cleaned_records.append(cleaned)
        
        return cleaned_records


class DataDeduplication:
    """数据去重和合并"""
    
    @staticmethod
    def deduplicate_stocks(stocks: List[Dict]) -> List[Dict]:
        """
        去除重复的股票记录
        
        保留最新的数据（基于code）
        
        Args:
            stocks: 股票列表
            
        Returns:
            去重后的股票列表
        """
        seen_codes: Set[str] = set()
        deduped = []
        
        # 假设列表已按优先级排序，后续重复项会被跳过
        for stock in stocks:
            code = stock.get('code')
            if code and code not in seen_codes:
                seen_codes.add(code)
                deduped.append(stock)
        
        return deduped
    
    @staticmethod
    def merge_industry_data(industry_sources: List[Dict], 
                           priority_order: List[str] = None) -> Dict[str, Dict]:
        """
        合并多源的行业数据
        
        优先级：sina > eastmoney > tencent > 其他
        
        Args:
            industry_sources: 行业数据列表，每项包含{code, industry, source}
            priority_order: 优先级顺序
            
        Returns:
            code -> industry的映射字典
        """
        if priority_order is None:
            priority_order = ['sina', 'eastmoney', 'tencent', 'cninfo']
        
        result = {}
        
        # 按优先级处理
        for source_name in priority_order:
            for item in industry_sources:
                if item.get('source') == source_name:
                    code = item.get('code')
                    if code and code not in result:
                        result[code] = item.get('industry')
        
        # 处理其他未优先级的源
        for item in industry_sources:
            code = item.get('code')
            if code and code not in result:
                result[code] = item.get('industry')
        
        return result
    
    @staticmethod
    def merge_financial_data(data_sources: List[Dict]) -> Dict[str, Dict]:
        """
        合并多源的财务数据
        
        按code合并，处理数据冲突
        
        Args:
            data_sources: 财务数据源列表
            
        Returns:
            合并后的数据字典
        """
        result = {}
        
        for item in data_sources:
            code = item.get('code')
            if not code:
                continue
            
            if code not in result:
                result[code] = item.copy()
            else:
                # 合并逻辑：优先使用已有的值，仅在缺失时补充
                existing = result[code]
                
                for year in ['2023', '2024']:
                    key = f'non_op_real_estate_{year}'
                    
                    # 如果现有值为空或None，使用新值
                    if not existing.get(key) and item.get(key):
                        existing[key] = item[key]
                    elif existing.get(key) and item.get(key):
                        # 两个都有值，保留较大的（假设数据来自不同年份）
                        try:
                            existing_val = float(existing[key])
                            item_val = float(item[key])
                            if item_val > existing_val:
                                existing[key] = item[key]
                        except (ValueError, TypeError):
                            pass
        
        return result
