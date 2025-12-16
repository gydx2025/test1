#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI测试脚本和示例数据生成器
"""

import sys
import os
import pandas as pd
import sqlite3
from datetime import datetime
import random

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from ui.data_query_service import DataQueryService

def create_sample_data():
    """创建示例数据"""
    print("正在创建示例数据...")
    
    # 初始化数据库
    service = DataQueryService()
    
    # 创建示例股票数据
    sample_stocks = [
        {'code': '000001', 'name': '平安银行', 'market': 'SZ'},
        {'code': '000002', 'name': '万科A', 'market': 'SZ'},
        {'code': '600000', 'name': '浦发银行', 'market': 'SH'},
        {'code': '600036', 'name': '招商银行', 'market': 'SH'},
        {'code': '600519', 'name': '贵州茅台', 'market': 'SH'},
        {'code': '000858', 'name': '五粮液', 'market': 'SZ'},
        {'code': '300059', 'name': '东方财富', 'market': 'SZ'},
        {'code': '002415', 'name': '海康威视', 'market': 'SZ'},
        {'code': '600276', 'name': '恒瑞医药', 'market': 'SH'},
        {'code': '002304', 'name': '洋河股份', 'market': 'SZ'},
    ]
    
    # 创建示例行业数据
    sample_industries = [
        {'code': '000001', 'l1': '银行', 'l2': '股份制银行', 'l3': '全国性股份制银行'},
        {'code': '000002', 'l1': '房地产', 'l2': '房地产开发', 'l3': '住宅开发'},
        {'code': '600000', 'l1': '银行', 'l2': '股份制银行', 'l3': '全国性股份制银行'},
        {'code': '600036', 'l1': '银行', 'l2': '股份制银行', 'l3': '全国性股份制银行'},
        {'code': '600519', 'l1': '食品饮料', 'l2': '白酒', 'l3': '高端白酒'},
        {'code': '000858', 'l1': '食品饮料', 'l2': '白酒', 'l3': '高端白酒'},
        {'code': '300059', 'l1': '非银金融', 'l2': '证券', 'l3': '综合证券'},
        {'code': '002415', 'l1': '电子', 'l2': '安防监控', 'l3': '视频监控设备'},
        {'code': '600276', 'l1': '医药生物', 'l2': '化学制药', 'l3': '创新药'},
        {'code': '002304', 'l1': '食品饮料', 'l2': '白酒', 'l3': '高端白酒'},
    ]
    
    # 创建示例财务数据
    sample_financial = []
    years = ['2022', '2023', '2024']
    
    for stock in sample_stocks:
        for year in years:
            # 生成一些随机的非经营性房地产资产数据
            if random.random() > 0.3:  # 70%的概率有数据
                non_op_real_estate = round(random.uniform(1000, 50000) * 10000, 2)  # 万元
                
                sample_financial.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    'year': year,
                    'non_op_real_estate': non_op_real_estate,
                    'data_source': 'sample_data'
                })
    
    # 插入数据到数据库
    conn = service._get_connection()
    cursor = conn.cursor()
    
    try:
        # 清空现有数据
        cursor.execute('DELETE FROM financial_data')
        cursor.execute('DELETE FROM industries')
        cursor.execute('DELETE FROM stocks')
        
        # 插入股票数据
        for stock in sample_stocks:
            cursor.execute('''
                INSERT INTO stocks (code, name, market, data_source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                stock['code'], 
                stock['name'], 
                stock['market'],
                'sample_data',
                datetime.now(),
                datetime.now()
            ))
        
        # 插入行业数据
        for industry in sample_industries:
            cursor.execute('''
                INSERT INTO industries (code, l1, l2, l3, data_source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                industry['code'],
                industry['l1'],
                industry['l2'],
                industry['l3'],
                'sample_data',
                datetime.now(),
                datetime.now()
            ))
        
        # 插入财务数据
        for fin_data in sample_financial:
            cursor.execute('''
                INSERT INTO financial_data (code, name, year, non_op_real_estate, data_source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                fin_data['code'],
                fin_data['name'],
                fin_data['year'],
                fin_data['non_op_real_estate'],
                fin_data['data_source'],
                datetime.now(),
                datetime.now()
            ))
        
        conn.commit()
        print(f"示例数据创建成功！")
        print(f"- 股票数据: {len(sample_stocks)} 条")
        print(f"- 行业数据: {len(sample_industries)} 条")
        print(f"- 财务数据: {len(sample_financial)} 条")
        
    except Exception as e:
        conn.rollback()
        print(f"插入数据失败: {e}")
    finally:
        conn.close()
        service.close()

def test_query_functions():
    """测试查询功能"""
    print("\n正在测试查询功能...")
    
    service = DataQueryService()
    try:
        # 测试1: 查询所有数据
        print("\n=== 测试1: 查询所有数据 ===")
        try:
            df = service.query_data()
            print(f"查询结果: {len(df)} 条记录")
            if not df.empty:
                print("前5条记录:")
                print(df.head())
        except Exception as e:
            print(f"查询失败: {e}")
        
        # 测试2: 按市场查询
        print("\n=== 测试2: 按市场查询 ===")
        try:
            df = service.query_data(market='沪市')
            print(f"沪市查询结果: {len(df)} 条记录")
            if not df.empty:
                print("前3条记录:")
                print(df.head(3))
        except Exception as e:
            print(f"查询失败: {e}")
        
        # 测试3: 按股票代码查询
        print("\n=== 测试3: 按股票代码查询 ===")
        try:
            df = service.query_data(stock_codes=['000001', '600519'])
            print(f"特定股票查询结果: {len(df)} 条记录")
            if not df.empty:
                print(df)
        except Exception as e:
            print(f"查询失败: {e}")
        
        # 测试4: 按年份查询
        print("\n=== 测试4: 按年份查询 ===")
        try:
            df = service.query_data(time_points=['2023'])
            print(f"2023年查询结果: {len(df)} 条记录")
            if not df.empty:
                print("前3条记录:")
                print(df.head(3))
        except Exception as e:
            print(f"查询失败: {e}")
    finally:
        service.close()

def test_export_function():
    """测试导出功能"""
    print("\n正在测试导出功能...")
    
    service = DataQueryService()
    try:
        # 查询一些数据
        df = service.query_data()
        
        if df.empty:
            print("没有数据可导出")
            return
        
        # 导出到Excel
        export_path = 'test_export.xlsx'
        success = service.export_to_excel(df, export_path)
        
        if success:
            print(f"数据已导出到: {export_path}")
            print(f"导出记录数: {len(df)}")
            
            # 检查文件是否存在
            if os.path.exists(export_path):
                file_size = os.path.getsize(export_path)
                print(f"文件大小: {file_size} 字节")
            else:
                print("警告: 导出文件未找到")
        else:
            print("导出失败")
            
    except Exception as e:
        print(f"导出测试失败: {e}")
    finally:
        service.close()

def test_subjects_and_markets():
    """测试科目和市场数据"""
    print("\n正在测试科目和市场数据...")
    
    service = DataQueryService()
    try:
        print("可用财务指标:")
        for i, subject in enumerate(service.available_subjects, 1):
            print(f"{i:2d}. {subject['name']} ({subject['code']})")
        
        print(f"\n可用市场: {service.markets}")
    finally:
        service.close()

def main():
    """主测试函数"""
    print("=== A股房地产资产查询系统 - 测试脚本 ===")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 测试科目和市场数据
    test_subjects_and_markets()
    
    # 2. 创建示例数据
    create_sample_data()
    
    # 3. 测试查询功能
    test_query_functions()
    
    # 4. 测试导出功能
    test_export_function()
    
    print("\n=== 测试完成 ===")
    print("\n可以使用以下方式启动UI:")
    print("python -m ui.real_estate_query_app")
    print("或")
    print("python run_ui.py")

if __name__ == "__main__":
    main()