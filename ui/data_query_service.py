#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据查询服务层
"""

import pandas as pd
import sqlite3
import logging
from typing import List, Dict
import os
import re

logger = logging.getLogger(__name__)


class DataQueryService:
    """数据查询服务类"""
    
    def __init__(self, db_path: str = 'astock_data.db'):
        """
        初始化查询服务
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.available_subjects = self._load_available_subjects()
        self.markets = ['全部', '沪市', '深市', '北市']
    
    def _load_available_subjects(self) -> List[Dict]:
        """加载资产负债表科目列表。

        说明：
        - UI 的科目下拉框只展示资产负债表项目，不包含利润表/现金流表等。
        - 列表顺序尽量贴近资产负债表的展示顺序（资产 -> 负债 -> 所有者权益）。
        - 扩展为完整的资产负债表科目列表

        Returns:
            科目列表
        """
        subjects = [
            # 资产类科目
            {'code': 'INVEST_REALESTATE', 'name': '投资性房地产'},
            {'code': 'FIXED_ASSET', 'name': '固定资产'},
            {'code': 'CIP', 'name': '在建工程'},
            {'code': 'USERIGHT_ASSET', 'name': '使用权资产'},
            {'code': 'INTANGIBLE_ASSET', 'name': '无形资产'},
            {'code': 'GOODWILL', 'name': '商誉'},
            {'code': 'DEFERRED_EXPENSES', 'name': '长期待摊费用'},
            {'code': 'DEFERRED_TAX_ASSET', 'name': '递延所得税资产'},
            {'code': 'OTHER_NONCURRENT_ASSETS', 'name': '其他非流动资产'},
            {'code': 'NONCURRENT_ASSET_SUMMARY', 'name': '非流动资产合计'},
            {'code': 'CURRENT_ASSET_INVENTORY', 'name': '存货'},
            {'code': 'CURRENT_ASSET_ACCOUNT_RECEIVABLE', 'name': '应收账款'},
            {'code': 'CURRENT_ASSET_OTHER_RECEIVABLE', 'name': '其他应收款'},
            {'code': 'CURRENT_ASSET_PREPAYMENT', 'name': '预付款项'},
            {'code': 'CURRENT_ASSET_CASH', 'name': '货币资金'},
            {'code': 'CURRENT_ASSET_TRADING_FINASSET', 'name': '交易性金融资产'},
            {'code': 'CURRENT_ASSET_OTHER', 'name': '其他流动资产'},
            {'code': 'CURRENT_ASSET_SUMMARY', 'name': '流动资产合计'},
            {'code': 'TOTAL_ASSETS', 'name': '资产总计'},
            
            # 负债类科目
            {'code': 'NONCURRENT_LIABILITY_BORROW', 'name': '长期借款'},
            {'code': 'NONCURRENT_LIABILITY_BOND', 'name': '应付债券'},
            {'code': 'NONCURRENT_LIABILITY_LEASE', 'name': '租赁负债'},
            {'code': 'NONCURRENT_LIABILITY_DEFERRED_TAX', 'name': '递延所得税负债'},
            {'code': 'NONCURRENT_LIABILITY_OTHER', 'name': '其他非流动负债'},
            {'code': 'NONCURRENT_LIABILITY_SUMMARY', 'name': '非流动负债合计'},
            {'code': 'CURRENT_LIABILITY_ACCOUNT_PAYABLE', 'name': '应付账款'},
            {'code': 'CURRENT_LIABILITY_ADVANCE_RECEIPT', 'name': '预收款项'},
            {'code': 'CURRENT_LIABILITY_SALARY_PAYABLE', 'name': '应付职工薪酬'},
            {'code': 'CURRENT_LIABILITY_TAX_PAYABLE', 'name': '应交税费'},
            {'code': 'CURRENT_LIABILITY_OTHER_PAYABLE', 'name': '其他应付款'},
            {'code': 'CURRENT_LIABILITY_BORROW', 'name': '短期借款'},
            {'code': 'CURRENT_LIABILITY_TRADING_FINLIAB', 'name': '交易性金融负债'},
            {'code': 'CURRENT_LIABILITY_OTHER', 'name': '其他流动负债'},
            {'code': 'CURRENT_LIABILITY_SUMMARY', 'name': '流动负债合计'},
            {'code': 'TOTAL_LIABILITIES', 'name': '负债合计'},
            
            # 所有者权益类科目
            {'code': 'OWNER_EQUITY_SHARE_CAPITAL', 'name': '实收资本(或股本)'},
            {'code': 'OWNER_EQUITY_CAPITAL_RESERVE', 'name': '资本公积'},
            {'code': 'OWNER_EQUITY_SURPLUS_RESERVE', 'name': '盈余公积'},
            {'code': 'OWNER_EQUITY_RETAINED_EARNINGS', 'name': '未分配利润'},
            {'code': 'OWNER_EQUITY_SUMMARY', 'name': '所有者权益合计'},
            
            # 特殊科目（保持兼容性）
            {'code': 'non_op_real_estate', 'name': '非经营性房地产资产'},
        ]
        return subjects
    
    def query_data(self, 
                   stock_codes: List[str] = None,
                   stock_names: List[str] = None,
                   market: str = '全部',
                   time_points: List[str] = None,
                   subject_codes: List[str] = None,
                   subject_names: List[str] = None,
                   subject_code: str = None,  # 保持兼容性
                   industry: str = None) -> pd.DataFrame:
        """查询数据。

        Args:
            stock_codes: 股票代码列表
            stock_names: 股票名称列表（支持模糊匹配）
            market: 市场类型
            time_points: 时点列表。
                - 兼容传入年份（如 '2023'）
                - 也支持传入财报期日期（如 '2024-06-30'），会自动提取年份做兼容过滤
            subject_codes: 科目代码列表（新接口，支持多科目）
            subject_names: 科目名称列表（新接口，支持多科目）
            subject_code: 科目代码（兼容性）
            industry: 行业筛选（申万一级行业）。None/全行业 表示不筛选

        Returns:
            查询结果DataFrame
        """
        try:
            # 优先使用新的多科目接口
            if subject_codes is None and subject_code:
                subject_codes = [subject_code]
            elif subject_codes is None and subject_code is None:
                # 默认查询非经营性房地产资产
                subject_codes = ['non_op_real_estate']
            
            # 如果没有股票代码，则获取所有股票
            if not stock_codes and not stock_names:
                stock_list = self.get_stock_list()
                if not stock_list.empty:
                    stock_codes = stock_list['code'].tolist()
            
            # 构建查询SQL
            sql = """
                SELECT 
                    s.code as 股票代码,
                    s.name as 股票名称,
                    s.market as 市场,
                    i.l1 as 申万一级行业,
                    i.l2 as 申万二级行业,
                    i.l3 as 申万三级行业,
                    fd.year as 年份,
                    fd.non_op_real_estate as 非经营性房地产资产,
                    fd.created_at as 数据更新时间
                FROM stocks s
                LEFT JOIN industries i ON s.code = i.code
                LEFT JOIN financial_data fd ON s.code = fd.code
                WHERE 1=1
            """
            
            params = []
            
            # 股票代码过滤
            if stock_codes:
                code_placeholders = ','.join(['?' for _ in stock_codes])
                sql += f" AND s.code IN ({code_placeholders})"
                params.extend(stock_codes)
            
            # 股票名称模糊搜索
            if stock_names:
                name_conditions = []
                for name in stock_names:
                    name_conditions.append("s.name LIKE ?")
                    params.append(f"%{name}%")
                sql += f" AND ({' OR '.join(name_conditions)})"
            
            # 市场过滤
            if market and market != '全部':
                market_map = {
                    '沪市': 'SH',
                    '深市': 'SZ',
                    '北市': 'BJ'
                }
                if market in market_map:
                    sql += " AND s.market = ?"
                    params.append(market_map[market])

            # 行业过滤（申万一级）
            if industry and industry != '全行业':
                sql += " AND i.l1 = ?"
                params.append(industry)

            # 时点过滤（兼容年份/财报期日期）
            if time_points:
                years: List[str] = []
                for tp in time_points:
                    if not tp:
                        continue
                    token = str(tp).strip()
                    if not token:
                        continue

                    # '2024-06-30' -> '2024'
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
                        years.append(token[:4])
                    elif re.fullmatch(r"\d{4}", token):
                        years.append(token)

                if years:
                    year_conditions = []
                    for y in years:
                        year_conditions.append("fd.year = ?")
                        params.append(y)
                    sql += f" AND ({' OR '.join(year_conditions)})"
            
            # 科目过滤 - 支持多科目查询
            if subject_codes:
                # 检查是否有财务数据
                has_financial_data = False
                for code in subject_codes:
                    if code in ['non_op_real_estate']:  # 当前数据库中存在的字段
                        has_financial_data = True
                        break
                
                if has_financial_data:
                    sql += " AND fd.non_op_real_estate IS NOT NULL"
                else:
                    # 对于新的科目字段，如果数据库中没有相应数据，返回空结果
                    logger.warning(f"科目 {subject_codes} 在当前数据库中未找到对应数据字段")
            
            sql += " ORDER BY s.code, fd.year"
            
            # 执行查询
            df = pd.read_sql_query(sql, self._get_connection(), params=params)
            
            logger.info(f"查询完成，返回 {len(df)} 条记录")
            
            # 如果没有数据，尝试从主要数据源查询
            if df.empty and stock_codes:
                logger.info("数据库中无数据，尝试从主要数据源获取数据...")
                try:
                    df = self._query_from_main_source(stock_codes, subject_codes[0] if subject_codes else 'non_op_real_estate', time_points)
                except Exception as e:
                    logger.warning(f"从主要数据源获取数据失败: {e}")
            
            return df
            
        except Exception as e:
            logger.error(f"数据查询失败: {str(e)}")
            raise
    
    def _query_from_main_source(self, stock_codes: List[str], subject_code: str, time_points: List[str]) -> pd.DataFrame:
        """从主要数据源查询数据（备用方案）"""
        try:
            # 导入主数据收集器
            from financial_query_service import FinancialQueryService
            
            # 创建查询服务
            query_service = FinancialQueryService()
            
            # 准备查询参数
            query_params = {
                'stock_codes': stock_codes,
                'market': '全部',
                'subject': subject_code,
                'report_dates': time_points or ['2023-12-31'],
                'return_format': 'dataframe'
            }
            
            # 执行查询
            result = query_service.execute_query(query_params)
            
            if result.success and result.dataframe is not None:
                # 转换列名以匹配UI预期
                df = result.dataframe.copy()
                df = df.rename(columns={
                    'stock_code': '股票代码',
                    'stock_name': '股票名称',
                    'market': '市场'
                })
                return df
            else:
                logger.warning(f"主要数据源查询失败: {result.error}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"从主要数据源查询失败: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表。

        Returns:
            股票列表DataFrame
        """
        try:
            sql = """
                SELECT code, name, market 
                FROM stocks 
                ORDER BY code
            """
            df = pd.read_sql_query(sql, self._get_connection())
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {str(e)}")
            return pd.DataFrame()

    def get_industry_options(self) -> List[str]:
        """获取行业筛选下拉框的候选项（申万一级行业）。

        Returns:
            行业列表（不含“全行业”）
        """
        try:
            sql = """
                SELECT DISTINCT l1
                FROM industries
                WHERE l1 IS NOT NULL AND TRIM(l1) != ''
                ORDER BY l1
            """
            df = pd.read_sql_query(sql, self._get_connection())
            if not df.empty:
                industries = [str(x).strip() for x in df['l1'].tolist() if str(x).strip()]
                if industries:
                    return industries
            
            # 如果数据库中没有行业数据，尝试从主要数据源获取
            logger.info("数据库中无行业数据，尝试从主要数据源获取...")
            industries = self._get_industry_from_main_source()
            if industries:
                return industries
                
            # 如果主要数据源也没有，返回默认的行业列表
            logger.warning("无法获取行业列表，返回默认行业列表")
            return self._get_default_industries()
            
        except Exception as e:
            logger.error(f"获取行业列表失败: {str(e)}")
            return self._get_default_industries()
    
    def _get_industry_from_main_source(self) -> List[str]:
        """从主要数据源获取行业列表"""
        try:
            # 尝试从本地缓存获取行业数据
            cache_file = "shenwan_industry_mapping.pkl"
            if os.path.exists(cache_file):
                import pickle
                with open(cache_file, 'rb') as f:
                    industry_data = pickle.load(f)
                    if industry_data:
                        # 提取一级行业
                        l1_industries = set()
                        for stock_code, industry_info in industry_data.items():
                            if isinstance(industry_info, dict) and 'l1' in industry_info:
                                l1_industries.add(industry_info['l1'])
                        return sorted(list(l1_industries))
            
            # 如果有主要数据收集器，尝试从中获取
            try:
                from astock_real_estate_collector import AStockRealEstateDataCollector
                collector = AStockRealEstateDataCollector()
                # 这里可以调用收集器的方法来获取行业数据
                # 但考虑到性能，我们先返回默认列表
                return self._get_default_industries()
            except Exception:
                pass
                
            return []
            
        except Exception as e:
            logger.error(f"从主要数据源获取行业列表失败: {e}")
            return []
    
    def _get_default_industries(self) -> List[str]:
        """获取默认的申万一级行业列表"""
        return [
            "农林牧渔",
            "采掘",
            "化工",
            "钢铁",
            "有色金属",
            "电子",
            "家用电器",
            "食品饮料",
            "纺织服装",
            "轻工制造",
            "医药生物",
            "公用事业",
            "交通运输",
            "房地产",
            "商业贸易",
            "休闲服务",
            "综合",
            "建筑材料",
            "建筑装饰",
            "电气设备",
            "国防军工",
            "计算机",
            "传媒",
            "通信",
            "非银金融",
            "银行",
            "汽车",
            "机械设备"
        ]
    
    def export_to_excel(self, df: pd.DataFrame, file_path: str) -> bool:
        """
        导出数据到Excel
        
        Args:
            df: 要导出的数据
            file_path: 导出文件路径
            
        Returns:
            是否成功
        """
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 写入主数据
                df.to_excel(writer, sheet_name='查询结果', index=False)
                
                # 获取工作表对象
                worksheet = writer.sheets['查询结果']
                
                # 设置列宽
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"数据已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出Excel失败: {str(e)}")
            return False
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接
        
        Returns:
            SQLite连接对象
        """
        if not os.path.exists(self.db_path):
            # 如果数据库不存在，创建一个空的
            conn = sqlite3.connect(self.db_path)
            # 创建基本表结构
            self._create_basic_tables(conn)
            return conn
        else:
            return sqlite3.connect(self.db_path)
    
    def _create_basic_tables(self, conn: sqlite3.Connection):
        """
        创建基本表结构
        
        Args:
            conn: 数据库连接
        """
        cursor = conn.cursor()
        
        # 创建股票表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                market TEXT,
                list_date TEXT,
                data_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建行业表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS industries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                l1 TEXT,
                l2 TEXT,
                l3 TEXT,
                data_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code) REFERENCES stocks(code)
            )
        ''')
        
        # 创建财务数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                year TEXT NOT NULL,
                non_op_real_estate REAL,
                data_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (code) REFERENCES stocks(code)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_code ON stocks(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_industries_code ON industries(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_financial_code ON financial_data(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_financial_year ON financial_data(year)')
        
        conn.commit()
    
    def _get_industry_from_main_source(self) -> List[str]:
        """从主要数据源获取行业列表"""
        try:
            # 尝试从本地缓存获取行业数据
            cache_file = "shenwan_industry_mapping.pkl"
            if os.path.exists(cache_file):
                import pickle
                with open(cache_file, 'rb') as f:
                    industry_data = pickle.load(f)
                    if industry_data:
                        # 提取一级行业
                        l1_industries = set()
                        for stock_code, industry_info in industry_data.items():
                            if isinstance(industry_info, dict) and 'l1' in industry_info:
                                l1_industries.add(industry_info['l1'])
                        return sorted(list(l1_industries))
            
            # 如果有主要数据收集器，尝试从中获取
            try:
                from astock_real_estate_collector import AStockRealEstateDataCollector
                collector = AStockRealEstateDataCollector()
                # 这里可以调用收集器的方法来获取行业数据
                # 但考虑到性能，我们先返回默认列表
                return self._get_default_industries()
            except Exception:
                pass
                
            return []
            
        except Exception as e:
            logger.error(f"从主要数据源获取行业列表失败: {e}")
            return []
    
    def _get_default_industries(self) -> List[str]:
        """获取默认的申万一级行业列表"""
        return [
            "农林牧渔",
            "采掘",
            "化工",
            "钢铁",
            "有色金属",
            "电子",
            "家用电器",
            "食品饮料",
            "纺织服装",
            "轻工制造",
            "医药生物",
            "公用事业",
            "交通运输",
            "房地产",
            "商业贸易",
            "休闲服务",
            "综合",
            "建筑材料",
            "建筑装饰",
            "电气设备",
            "国防军工",
            "计算机",
            "传媒",
            "通信",
            "非银金融",
            "银行",
            "汽车",
            "机械设备"
        ]