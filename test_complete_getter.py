#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多源循环补全行业分类获取器

功能：
1. 测试新的IndustryClassificationCompleteGetter类
2. 验证8个数据源的功能
3. 测试循环补全和中断处理机制

作者：Claude
日期：2024
版本：v3.0
"""

import sys
import os
import time
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from industry_classification_complete_getter import IndustryClassificationCompleteGetter


def test_complete_getter():
    """测试多源循环补全获取器"""
    print("=" * 80)
    print("🧪 测试多源循环补全行业分类获取器")
    print("=" * 80)
    
    # 创建测试数据
    test_stocks = [
        {"code": "000001", "name": "平安银行", "industry": "银行"},
        {"code": "000002", "name": "万科A", "industry": "房地产"},
        {"code": "000858", "name": "五粮液", "industry": "食品饮料"},
        {"code": "600519", "name": "贵州茅台", "industry": "食品饮料"},
        {"code": "600036", "name": "招商银行", "industry": "银行"},
    ]
    
    print(f"📊 测试股票数量: {len(test_stocks)}")
    print("📋 测试股票列表:")
    for stock in test_stocks:
        print(f"   - {stock['code']} {stock['name']} ({stock['industry']})")
    print()
    
    # 初始化获取器
    getter = IndustryClassificationCompleteGetter()
    
    # 开始获取
    print("🔄 开始多源循环补全测试...")
    print()
    
    try:
        # 测试获取完整分类
        result = getter.get_complete_classification(test_stocks, show_progress=True)
        
        print("\n" + "=" * 80)
        print("📊 测试结果汇总")
        print("=" * 80)
        
        # 显示结果
        success_count = 0
        total_count = len(result)
        
        for stock_code, data in result.items():
            if data.get('source') != 'unknown':
                success_count += 1
                print(f"✅ {stock_code}: {data.get('shenwan_level1', 'N/A')} -> {data.get('industry', 'N/A')} (来源: {data.get('source', 'N/A')})")
            else:
                print(f"❌ {stock_code}: 获取失败 (来源: {data.get('source', 'N/A')})")
        
        print(f"\n📈 成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        
        # 显示数据源统计
        print("\n📋 数据源使用统计:")
        source_stats = {}
        for stock_code, data in result.items():
            source = data.get('source', 'unknown')
            source_stats[source] = source_stats.get(source, 0) + 1
        
        for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_count * 100
            print(f"   - {source}: {count} 个股票 ({percentage:.1f}%)")
        
        print("\n✅ 测试完成！")
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了测试")
        return False
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_source():
    """测试单个数据源"""
    print("=" * 80)
    print("🧪 测试单个数据源功能")
    print("=" * 80)
    
    getter = IndustryClassificationCompleteGetter()
    
    # 测试东方财富F10源
    stock_code = "000001"
    stock_name = "平安银行"
    base_industry = "银行"
    
    print(f"🔍 测试股票: {stock_code} {stock_name}")
    print(f"🎯 测试源: 东方财富F10")
    
    try:
        result = getter._fetch_from_eastmoney_f10(stock_code, stock_name, base_industry)
        
        if result:
            print(f"✅ 获取成功:")
            print(f"   - 一级分类: {result.shenwan_level1}")
            print(f"   - 二级分类: {result.shenwan_level2}")
            print(f"   - 三级分类: {result.shenwan_level3}")
            print(f"   - 行业文本: {result.industry}")
            print(f"   - 数据源: {result.source}")
            print(f"   - 置信度: {result.confidence}")
        else:
            print("❌ 获取失败")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


def test_inference():
    """测试行业分类推断功能"""
    print("=" * 80)
    print("🧪 测试行业分类推断功能")
    print("=" * 80)
    
    getter = IndustryClassificationCompleteGetter()
    
    test_cases = [
        "银行业",
        "房地产开发",
        "白酒制造",
        "钢铁冶炼",
        "石油化工",
        "计算机应用",
        "医药生物",
        "未知行业"
    ]
    
    print("🔍 测试行业文本推断:")
    for industry_text in test_cases:
        l1, l2, l3 = getter._infer_shenwan_levels(industry_text)
        print(f"   '{industry_text}' -> {l1} / {l2} / {l3}")
    
    print("\n✅ 推断功能测试完成！")


def main():
    """主函数"""
    print("🚀 启动多源循环补全行业分类获取器测试")
    print()
    
    # 选择测试类型
    print("请选择测试类型:")
    print("1. 完整流程测试 (推荐)")
    print("2. 单个数据源测试")
    print("3. 行业推断功能测试")
    print("4. 全部测试")
    
    try:
        choice = input("\n请输入选择 (1-4): ").strip()
        
        if choice == "1":
            test_complete_getter()
        elif choice == "2":
            test_single_source()
        elif choice == "3":
            test_inference()
        elif choice == "4":
            test_inference()
            print()
            test_single_source()
            print()
            test_complete_getter()
        else:
            print("❌ 无效选择")
            
    except (EOFError, KeyboardInterrupt):
        print("\n👋 测试已取消")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")


if __name__ == "__main__":
    main()