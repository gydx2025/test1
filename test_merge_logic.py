#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证merge操作的完整性 - 确保科目数据正确地添加为列
"""

import pandas as pd

# 模拟财务查询服务返回的结果
# 每个科目查询返回的数据格式
def simulate_query_result(subject_name):
    """模拟FinancialQueryService.execute_query()返回的DataFrame"""
    data = [
        {
            'stock_code': '000001',
            'stock_name': '平安',
            'market': '深市',
            f'2024-12-31/{subject_name}(万元)': 100.5,
            f'2023-12-31/{subject_name}(万元)': 90.2,
        },
        {
            'stock_code': '600000',
            'stock_name': '浦发',
            'market': '沪市',
            f'2024-12-31/{subject_name}(万元)': 200.3,
            f'2023-12-31/{subject_name}(万元)': 180.1,
        },
    ]
    return pd.DataFrame(data)

# 创建基础行
base_rows = [
    {'股票代码': '000001', '股票名称': '平安', '上市时间': '2020-01-01', '市场': '深市'},
    {'股票代码': '600000', '股票名称': '浦发', '上市时间': '2019-01-01', '市场': '沪市'},
]
result_df = pd.DataFrame(base_rows)
print(f"基础行数: {len(result_df)}, 列数: {len(result_df.columns)}")
print(f"基础列: {list(result_df.columns)}")
print()

# 模拟merge第一个科目
subject1_name = '投资性房地产'
df1 = simulate_query_result(subject1_name)
print(f"科目1 ({subject1_name}) 返回的数据:")
print(f"  行数: {len(df1)}, 列数: {len(df1.columns)}")
print(f"  列: {list(df1.columns)}")

# 提取科目数据
base_cols = {'stock_code', 'stock_name', 'market'}
subject_data = df1[['stock_code']].copy()
subject_data.rename(columns={'stock_code': '股票代码'}, inplace=True)
for col in df1.columns:
    if col not in base_cols:
        subject_data[col] = df1[col]

print(f"  提取的科目数据列: {list(subject_data.columns)}")

# 执行merge
result_df = result_df.merge(subject_data, on='股票代码', how='left')
print(f"Merge后: {len(result_df)} 行, {len(result_df.columns)} 列")
print(f"Merge后的列: {list(result_df.columns)}")
print()

# 模拟merge第二个科目
subject2_name = '固定资产'
df2 = simulate_query_result(subject2_name)
print(f"科目2 ({subject2_name}) 返回的数据:")
print(f"  行数: {len(df2)}, 列数: {len(df2.columns)}")

subject_data = df2[['stock_code']].copy()
subject_data.rename(columns={'stock_code': '股票代码'}, inplace=True)
for col in df2.columns:
    if col not in base_cols:
        subject_data[col] = df2[col]

result_df = result_df.merge(subject_data, on='股票代码', how='left')
print(f"Merge后: {len(result_df)} 行, {len(result_df.columns)} 列")
print(f"Merge后的列: {list(result_df.columns)}")
print()

# 去重
result_df = result_df.drop_duplicates(subset=['股票代码'], keep='first').reset_index(drop=True)
print(f"去重后: {len(result_df)} 行, {len(result_df.columns)} 列")
print()

# 验证数据完整性
print("最终数据:")
print(result_df.to_string())
print()

# 验证关键信息
print("验证清单:")
print(f"✓ 行数正确（应该是2行，实际{len(result_df)}行）" if len(result_df) == 2 else f"✗ 行数错误")
print(f"✓ 包含上市时间列" if '上市时间' in result_df.columns else "✗ 缺少上市时间列")
print(f"✓ 包含市场列" if '市场' in result_df.columns else "✗ 缺少市场列")
print(f"✓ 包含科目数据列（多个）" if any('万元' in col for col in result_df.columns) else "✗ 缺少科目数据")

subject_cols = [col for col in result_df.columns if '万元' in col]
print(f"✓ 科目数据列数: {len(subject_cols)}")
print(f"  包含的科目列: {subject_cols}")
