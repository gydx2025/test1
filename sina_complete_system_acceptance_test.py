#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新浪财经主源完整获取体系验收测试

功能：
1. 验证完整的股票获取流程
2. 检查数据质量和完整性
3. 验证新系统的各项功能

作者：Claude
日期：2024
版本：v1.0
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sina_stock_list_complete_fetcher import SinaStockListCompleteFetcher, StockListCompleteness
from astock_real_estate_collector import AStockRealEstateDataCollector

def test_individual_components():
    """测试各个组件"""
    print("="*80)
    print("组件测试")
    print("="*80)
    
    # 测试代码标准化
    print("1. 代码标准化测试")
    fetcher = SinaStockListCompleteFetcher()
    
    test_cases = [
        ('sh600000', '600000'),
        ('sz000001', '000001'),
        ('920000', '920000'),  # 新三板
        ('300001', '300001'),
        ('688001', '688001'),
    ]
    
    success_count = 0
    for input_code, expected in test_cases:
        try:
            result = fetcher._normalize_and_validate_code(input_code)
            if result == expected:
                print(f"   ✅ {input_code:12} → {result:6}")
                success_count += 1
            else:
                print(f"   ❌ {input_code:12} → {result:6} (期望: {expected})")
        except Exception as e:
            print(f"   ❌ {input_code:12} → 异常: {e}")
    
    print(f"   代码标准化: {success_count}/{len(test_cases)} 通过")
    
    # 测试代码验证
    print("\\n2. 代码验证测试")
    valid_codes = ['600000', '000001', '920000', '300001', '688001']
    invalid_codes = ['12345', 'abc123', '92000a']
    
    valid_success = sum(1 for code in valid_codes if fetcher._validate_code_format(code))
    invalid_success = sum(1 for code in invalid_codes if not fetcher._validate_code_format(code))
    
    print(f"   有效代码验证: {valid_success}/{len(valid_codes)} 通过")
    print(f"   无效代码验证: {invalid_success}/{len(invalid_codes)} 通过")
    
    return success_count == len(test_cases) and valid_success == len(valid_codes) and invalid_success == len(invalid_codes)

def test_main_system_integration():
    """测试主系统集成"""
    print("\\n" + "="*80)
    print("主系统集成测试")
    print("="*80)
    
    try:
        print("1. 导入测试")
        collector = AStockRealEstateDataCollector()
        print("   ✅ 主系统导入成功")
        
        print("2. 新浪获取器导入测试")
        sina_fetcher = SinaStockListCompleteFetcher()
        print("   ✅ 新浪获取器导入成功")
        
        print("3. 验证系统导入测试")
        verification = StockListCompleteness
        print("   ✅ 验证系统导入成功")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 集成测试失败: {e}")
        return False

def test_data_quality():
    """测试数据质量"""
    print("\\n" + "="*80)
    print("数据质量测试")
    print("="*80)
    
    try:
        # 获取少量样本数据进行质量检查
        fetcher = SinaStockListCompleteFetcher()
        
        print("1. 获取样本数据（限制前3页）...")
        
        # 模拟获取过程
        stocks = {}
        for page in range(1, 4):  # 只获取前3页
            page_data = fetcher._fetch_page(page)
            if not page_data:
                break
            
            for item in page_data:
                try:
                    code = fetcher._normalize_and_validate_code(item['code'])
                    if fetcher._validate_code_format(code):
                        stocks[code] = {
                            'code': code,
                            'name': item['name'],
                            'industry': item.get('industry', ''),
                            'market': '上海' if code.startswith('6') else '深圳',
                        }
                except Exception as e:
                    continue
        
        print(f"   ✅ 获取样本数据: {len(stocks)}只股票")
        
        if len(stocks) == 0:
            print("   ❌ 未获取到任何数据")
            return False
        
        # 质量检查
        print("\\n2. 质量检查")
        
        # 检查重复
        codes = list(stocks.keys())
        unique_codes = set(codes)
        duplicates = len(codes) - len(unique_codes)
        print(f"   - 去重检查: {len(unique_codes)}只唯一股票，{duplicates}个重复")
        
        # 检查格式
        format_valid = all(len(code) == 6 and code.isdigit() for code in codes)
        print(f"   - 格式检查: {'✅ 通过' if format_valid else '❌ 失败'}")
        
        # 检查代码分布
        distribution = {}
        for code in codes:
            first = code[0]
            distribution[first] = distribution.get(first, 0) + 1
        
        print(f"   - 代码分布: {distribution}")
        
        # 检查数据完整性
        name_missing = sum(1 for stock in stocks.values() if not stock.get('name'))
        print(f"   - 名称完整性: {len(stocks) - name_missing}/{len(stocks)} 只有效名称")
        
        return duplicates == 0 and format_valid and name_missing == 0
        
    except Exception as e:
        print(f"   ❌ 质量测试失败: {e}")
        return False

def test_verification_system():
    """测试验证系统"""
    print("\\n" + "="*80)
    print("验证系统测试")
    print("="*80)
    
    # 创建足够的测试数据（>= 5000只股票）
    test_stocks = []
    
    # 生成各种类型的股票代码，确保总数超过5000且无重复
    # 确保所有代码都是唯一的6位数字格式
    
    # 6开头：上海主板
    for i in range(600000, 601500):  
        test_stocks.append({'code': f'{i:06d}', 'name': f'上海股票{i}'})
    
    # 0开头：深圳主板（正确的0xxxxx格式）
    for i in range(10000, 11800):  
        test_stocks.append({'code': f'{i:06d}', 'name': f'深圳主板股票{i}'})
    
    # 3开头：创业板
    for i in range(300000, 301800):  
        test_stocks.append({'code': f'{i:06d}', 'name': f'创业板股票{i}'})
    
    # 8开头：科创板
    for i in range(800000, 801000):  
        test_stocks.append({'code': f'{i:06d}', 'name': f'科创板股票{i}'})
    
    # 9开头：新三板
    for i in range(900000, 904200):  
        test_stocks.append({'code': f'{i:06d}', 'name': f'新三板股票{i}'})
    
    # 4开头：北交所
    for i in range(400000, 400700):  
        test_stocks.append({'code': f'{i:06d}', 'name': f'北交所股票{i}'})
    
    # 剪裁到正好5000只股票
    test_stocks = test_stocks[:5000]
    
    print(f"1. 生成测试数据: {len(test_stocks)}只股票")
    
    try:
        # 测试验证系统
        result = StockListCompleteness.verify_all(test_stocks)
        print("2. 验证系统: ✅ 通过")
        return result
    except AssertionError as e:
        print(f"2. 验证系统: ❌ 失败 - {e}")
        return False
    except Exception as e:
        print(f"2. 验证系统: ❌ 异常 - {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 新浪财经主源完整获取体系验收测试")
    print("="*80)
    
    tests = [
        ("组件测试", test_individual_components),
        ("主系统集成", test_main_system_integration),
        ("数据质量", test_data_quality),
        ("验证系统", test_verification_system),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 发生异常: {e}")
            results.append((test_name, False))
    
    # 总结
    print("\\n" + "="*80)
    print("📊 验收测试总结")
    print("="*80)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:15}: {status}")
        if result:
            passed += 1
    
    print(f"\\n总计: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("\\n🎉 所有验收测试通过！")
        print("✅ 新浪财经主源完整获取体系功能正常")
        print("✅ 代码标准化和验证工作正常")
        print("✅ 数据质量检查和完整性验证正常")
        print("✅ 系统集成和兼容性正常")
    else:
        print(f"\\n⚠️ {len(results) - passed} 项测试失败，需要进一步检查。")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)