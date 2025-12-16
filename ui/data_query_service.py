#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据查询服务层
"""

import pandas as pd
import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
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
        """
        加载资产负债表科目列表
        
        Returns:
            科目列表
        """
        subjects = [
            {'code': 'total_assets', 'name': '总资产'},
            {'code': 'current_assets', 'name': '流动资产合计'},
            {'code': 'non_current_assets', 'name': '非流动资产合计'},
            {'code': 'total_liabilities', 'name': '负债合计'},
            {'code': 'current_liabilities', 'name': '流动负债合计'},
            {'code': 'non_current_liabilities', 'name': '非流动负债合计'},
            {'code': 'owners_equity', 'name': '所有者权益合计'},
            {'code': 'operating_income', 'name': '营业收入'},
            {'code': 'operating_cost', 'name': '营业成本'},
            {'code': 'net_profit', 'name': '净利润'},
            {'code': 'total_revenue', 'name': '营业总收入'},
            {'code': 'total_cost', 'name': '营业总成本'},
            {'code': 'business_income', 'name': '主营业务收入'},
            {'code': 'business_cost', 'name': '主营业务成本'},
            {'code': 'management_expense', 'name': '管理费用'},
            {'code': 'selling_expense', 'name': '销售费用'},
            {'code': 'rd_expense', 'name': '研发费用'},
            {'code': 'finance_expense', 'name': '财务费用'}
        ]
        return subjects
    
    def query_data(self, 
                   stock_codes: List[str] = None,
                   stock_names: List[str] = None,
                   market: str = '全部',
                   time_points: List[str] = None,
                   subject_code: str = None) -> pd.DataFrame:
        """
        查询数据
        
        Args:
            stock_codes: 股票代码列表
            stock_names: 股票名称列表
            market: 市场类型
            time_points: 时点列表
            subject_code: 科目代码
            
        Returns:
            查询结果DataFrame
        """
        try:
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
            
            # 时点过滤
            if time_points:
                year_conditions = []
                for year in time_points:
                    if year:
                        year_conditions.append("fd.year = ?")
                        params.append(year)
                if year_conditions:
                    sql += f" AND ({' OR '.join(year_conditions)})"
            
            # 科目过滤（这里使用现有的非经营性房地产资产字段）
            if subject_code:
                # 如果需要其他科目，这里可以扩展
                if subject_code == 'non_op_real_estate':
                    # 使用现有字段
                    pass
                else:
                    sql += " AND fd.non_op_real_estate IS NOT NULL"
            else:
                # 默认查询非经营性房地产资产数据
                sql += " AND fd.non_op_real_estate IS NOT NULL"
            
            sql += " ORDER BY s.code, fd.year"
            
            # 执行查询
            df = pd.read_sql_query(sql, self._get_connection(), params=params)
            
            logger.info(f"查询完成，返回 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"数据查询失败: {str(e)}")
            raise
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取股票列表
        
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