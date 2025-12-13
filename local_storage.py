#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地离线数据库系统

提供SQLite本地数据库、缓存管理、备份和恢复机制
"""

import sqlite3
import json
import logging
import os
import csv
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LocalDatabase:
    """本地SQLite数据库系统"""
    
    def __init__(self, db_path: str = 'astock_data.db'):
        """
        初始化本地数据库
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_database()
    
    def init_database(self):
        """初始化SQLite数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            
            # 创建股票基础信息表
            self.cursor.execute('''
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
            
            # 创建行业分类表
            self.cursor.execute('''
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
            self.cursor.execute('''
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
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_code ON stocks(code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_industries_code ON industries(code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_financial_code ON financial_data(code)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_financial_year ON financial_data(year)')
            
            # 创建版本管理表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT,
                    collection_date TIMESTAMP,
                    total_stocks INTEGER,
                    total_industries INTEGER,
                    stocks_with_2023_data INTEGER,
                    stocks_with_2024_data INTEGER,
                    data_completeness REAL,
                    notes TEXT
                )
            ''')
            
            self.conn.commit()
            logger.info(f"数据库初始化成功: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def backup_stocks(self, stocks: List[Dict]):
        """
        备份股票基础信息
        
        Args:
            stocks: 股票列表
        """
        try:
            # 清空旧数据
            self.cursor.execute('DELETE FROM stocks')
            
            # 插入新数据
            for stock in stocks:
                self.cursor.execute('''
                    INSERT OR REPLACE INTO stocks 
                    (code, name, market, list_date, data_source, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    stock.get('code'),
                    stock.get('name'),
                    stock.get('market'),
                    stock.get('list_date'),
                    stock.get('data_source'),
                    datetime.now().isoformat()
                ))
            
            self.conn.commit()
            logger.info(f"备份{len(stocks)}只股票到数据库")
            
        except Exception as e:
            logger.error(f"备份股票失败: {e}")
            self.conn.rollback()
    
    def backup_industries(self, industries: Dict[str, Dict]):
        """
        备份行业分类信息
        
        Args:
            industries: code -> industry的映射
        """
        try:
            # 清空旧数据
            self.cursor.execute('DELETE FROM industries')
            
            # 插入新数据
            for code, industry in industries.items():
                if industry:
                    self.cursor.execute('''
                        INSERT INTO industries 
                        (code, l1, l2, l3, data_source, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        code,
                        industry.get('l1'),
                        industry.get('l2'),
                        industry.get('l3'),
                        industry.get('source'),
                        datetime.now().isoformat()
                    ))
            
            self.conn.commit()
            logger.info(f"备份{len(industries)}个行业分类到数据库")
            
        except Exception as e:
            logger.error(f"备份行业分类失败: {e}")
            self.conn.rollback()
    
    def backup_financial_data(self, financial_records: List[Dict]):
        """
        备份财务数据
        
        Args:
            financial_records: 财务数据列表
        """
        try:
            # 清空旧数据
            self.cursor.execute('DELETE FROM financial_data')
            
            # 插入新数据
            for record in financial_records:
                for year in ['2023', '2024']:
                    key = f'non_op_real_estate_{year}'
                    if key in record and record[key] is not None:
                        self.cursor.execute('''
                            INSERT INTO financial_data 
                            (code, name, year, non_op_real_estate, data_source, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            record.get('code'),
                            record.get('name'),
                            year,
                            record[key],
                            record.get('data_source'),
                            datetime.now().isoformat()
                        ))
            
            self.conn.commit()
            logger.info(f"备份{len(financial_records)}条财务数据到数据库")
            
        except Exception as e:
            logger.error(f"备份财务数据失败: {e}")
            self.conn.rollback()
    
    def save_version_info(self, version: str, data_report: Dict):
        """
        保存版本信息
        
        Args:
            version: 版本号
            data_report: 数据报告
        """
        try:
            self.cursor.execute('''
                INSERT INTO data_versions 
                (version, collection_date, total_stocks, total_industries, 
                 stocks_with_2023_data, stocks_with_2024_data, data_completeness, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                version,
                datetime.now().isoformat(),
                data_report.get('total_stocks', 0),
                data_report.get('total_industries', 0),
                data_report.get('stocks_with_2023_data', 0),
                data_report.get('stocks_with_2024_data', 0),
                data_report.get('data_completeness', 0.0),
                data_report.get('notes', '')
            ))
            
            self.conn.commit()
            logger.info(f"保存版本信息: {version}")
            
        except Exception as e:
            logger.error(f"保存版本信息失败: {e}")
            self.conn.rollback()
    
    def restore_stocks(self) -> List[Dict]:
        """
        从本地数据库恢复股票数据
        
        Returns:
            股票列表
        """
        try:
            self.cursor.execute('SELECT * FROM stocks ORDER BY code')
            columns = [desc[0] for desc in self.cursor.description]
            
            stocks = []
            for row in self.cursor.fetchall():
                stock = dict(zip(columns, row))
                stocks.append(stock)
            
            logger.info(f"从数据库恢复{len(stocks)}只股票")
            return stocks
            
        except Exception as e:
            logger.error(f"恢复股票数据失败: {e}")
            return []
    
    def restore_industries(self) -> Dict[str, Dict]:
        """
        从本地数据库恢复行业数据
        
        Returns:
            code -> industry的映射
        """
        try:
            self.cursor.execute('SELECT code, l1, l2, l3, data_source FROM industries')
            
            industries = {}
            for code, l1, l2, l3, source in self.cursor.fetchall():
                industries[code] = {
                    'l1': l1,
                    'l2': l2,
                    'l3': l3,
                    'source': source
                }
            
            logger.info(f"从数据库恢复{len(industries)}个行业分类")
            return industries
            
        except Exception as e:
            logger.error(f"恢复行业分类失败: {e}")
            return {}
    
    def restore_financial_data(self) -> List[Dict]:
        """
        从本地数据库恢复财务数据
        
        Returns:
            财务数据列表
        """
        try:
            self.cursor.execute('''
                SELECT code, name, year, non_op_real_estate, data_source 
                FROM financial_data 
                ORDER BY code, year
            ''')
            
            # 合并同一个code的多年数据
            data_map = {}
            for code, name, year, value, source in self.cursor.fetchall():
                if code not in data_map:
                    data_map[code] = {
                        'code': code,
                        'name': name,
                        'data_source': source
                    }
                
                key = f'non_op_real_estate_{year}'
                data_map[code][key] = value
            
            result = list(data_map.values())
            logger.info(f"从数据库恢复{len(result)}条财务数据")
            return result
            
        except Exception as e:
            logger.error(f"恢复财务数据失败: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")


class CacheManager:
    """缓存管理系统"""
    
    def __init__(self, cache_dir: str = 'cache'):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def save_cache(self, name: str, data: Dict):
        """
        保存缓存数据
        
        Args:
            name: 缓存名称
            data: 数据
        """
        try:
            cache_file = os.path.join(self.cache_dir, f'{name}.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"缓存已保存: {cache_file}")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def load_cache(self, name: str) -> Optional[Dict]:
        """
        加载缓存数据
        
        Args:
            name: 缓存名称
            
        Returns:
            缓存数据或None
        """
        try:
            cache_file = os.path.join(self.cache_dir, f'{name}.json')
            if not os.path.exists(cache_file):
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"缓存已加载: {cache_file}")
            return data
            
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return None
    
    def clear_cache(self, name: Optional[str] = None):
        """
        清空缓存
        
        Args:
            name: 要清空的缓存名称，None表示清空全部
        """
        try:
            if name:
                cache_file = os.path.join(self.cache_dir, f'{name}.json')
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    logger.info(f"缓存已清空: {cache_file}")
            else:
                for file in os.listdir(self.cache_dir):
                    if file.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, file))
                logger.info("全部缓存已清空")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")


class CSVBackupManager:
    """CSV备份管理"""
    
    @staticmethod
    def backup_to_csv(data: List[Dict], filename: str):
        """
        将数据备份为CSV文件
        
        Args:
            data: 数据列表
            filename: 文件名
        """
        if not data:
            logger.warning("没有数据可备份")
            return
        
        try:
            # 获取所有字段
            fieldnames = set()
            for item in data:
                fieldnames.update(item.keys())
            fieldnames = sorted(list(fieldnames))
            
            # 写入CSV
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            logger.info(f"数据已备份为CSV: {filename}")
            
        except Exception as e:
            logger.error(f"CSV备份失败: {e}")
    
    @staticmethod
    def restore_from_csv(filename: str) -> List[Dict]:
        """
        从CSV文件恢复数据
        
        Args:
            filename: 文件名
            
        Returns:
            数据列表
        """
        try:
            data = []
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                data = list(reader)
            
            logger.info(f"数据已从CSV恢复: {filename}")
            return data
            
        except Exception as e:
            logger.error(f"CSV恢复失败: {e}")
            return []
