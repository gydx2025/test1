#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新浪财经完整获取系统

功能：
1. 测试代码标准化和验证功能
2. 测试完整性验证系统
3. 简单测试分页获取（如果网络可用）

作者：Claude
日期：2024
版本：v1.0
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sina_stock_list_complete_fetcher import SinaStockListCompleteFetcher, StockListCompleteness

def test_code_normalization():
    """测试代码标准化功能"""
    print("="*60)
    print("测试1: 代码标准化功能")
    print("="*60)
    
    fetcher = SinaStockListCompleteFetcher()
    
    # 测试各种代码格式
    test_cases = [
        ('sh600000', '600000'),
        ('sz000001', '000001'),
        ('300001', '300001'),
        ('688001', '688001'),
        ('600000.ss', '600000'),
        ('a000002', '000002'),
        ('sh000001', '000001'),
    ]
    
    success_count = 0
    for input_code, expected in test_cases:
        try:
            result = fetcher._normalize_and_validate_code(input_code)
            if result == expected:
                print(f"✅ {input_code:12} → {result:6} (正确)")
                success_count += 1
            else:
                print(f"❌ {input_code:12} → {result:6} (期望: {expected})")
        except Exception as e:
            print(f"❌ {input_code:12} → 异常: {e}")
    
    print(f"\n标准化测试: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)

def test_code_validation():
    """测试代码验证功能"""
    print("\n" + "="*60)
    print("测试2: 代码验证功能")
    print("="*60)
    
    fetcher = SinaStockListCompleteFetcher()
    
    # 测试有效代码
    valid_codes = ['600000', '000001', '300001', '688001', '400001', '800001']
    invalid_codes = ['12345', 'abcdef', '1234567', '920001', '999999', '999999.00']
    
    print("有效代码测试:")
    valid_success = 0
    for code in valid_codes:
        result = fetcher._validate_code_format(code)
        if result:
            print(f"✅ {code:6}: {result} (正确)")
            valid_success += 1
        else:
            print(f"❌ {code:6}: {result} (应该为True)")
    
    print("\n无效代码测试:")
    invalid_success = 0
    for code in invalid_codes:
        result = fetcher._validate_code_format(code)
        if not result:
            print(f"✅ {code:6}: {result} (正确)")
            invalid_success += 1
        else:
            print(f"❌ {code:6}: {result} (应该为False)")
    
    total_success = valid_success + invalid_success
    total_tests = len(valid_codes) + len(invalid_codes)
    print(f"\n验证测试: {total_success}/{total_tests} 通过")
    return total_success == total_tests

def test_completeness_verification():
    """测试完整性验证系统"""
    print("\n" + "="*60)
    print("测试3: 完整性验证系统")
    print("="*60)
    
    # 创建足够的测试数据（>= 5000只股票）
    test_stocks = []
    
    # 生成不同类型的股票代码
    for i in range(600, 700):  # 600xxx - 上海主板
        test_stocks.append({'code': f'{i:06d}', 'name': f'上海股票{i}'})
    
    for i in range(0, 100):    # 000xxx - 深圳主板
        test_stocks.append({'code': f'{i:06d}', 'name': f'深圳主板{i}'})
    
    for i in range(300, 400):  # 300xxx - 创业板
        test_stocks.append({'code': f'{i:06d}', 'name': f'创业板股票{i}'})
    
    for i in range(688, 698):  # 688xxx - 科创板
        test_stocks.append({'code': f'{i:06d}', 'name': f'科创板股票{i}'})
    
    print(f"生成了 {len(test_stocks)} 只测试股票")
    
    # 测试验证通过的情况
    try:
        result = StockListCompleteness.verify_all(test_stocks)
        print("✅ 验证系统工作正常")
        return True
    except AssertionError as e:
        print(f"❌ 验证失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 验证过程异常: {e}")
        return False

def test_page_fetching():
    """测试分页获取功能（简单测试）"""
    print("\n" + "="*60)
    print("测试4: 分页获取功能（简单测试）")
    print("="*60)
    
    fetcher = SinaStockListCompleteFetcher()
    
    try:
        # 测试获取第一页
        print("尝试获取第1页数据...")
        page_data = fetcher._fetch_page(1)
        
        if page_data is not None:
            print(f"✅ 成功获取第1页数据，共{len(page_data)}条记录")
            
            # 显示前3条记录的格式
            print("\n前3条记录示例:")
            for i, item in enumerate(page_data[:3]):
                print(f"  {i+1}. 代码: {item.get('code', 'N/A')}, 名称: {item.get('name', 'N/A')}")
            
            return True
        else:
            print("❌ 无法获取第1页数据")
            return False
            
    except Exception as e:
        print(f"❌ 分页获取测试异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 新浪财经完整获取系统测试")
    print("="*80)
    
    tests = [
        ("代码标准化", test_code_normalization),
        ("代码验证", test_code_validation),
        ("完整性验证", test_completeness_verification),
        ("分页获取", test_page_fetching),
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
    print("\n" + "="*80)
    print("📊 测试结果总结")
    print("="*80)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:15}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 项测试通过")
    
    if passed == len(results):
        print("\n🎉 所有测试通过！系统功能正常。")
    else:
        print(f"\n⚠️ {len(results) - passed} 项测试失败，需要检查。")
    
    return passed == len(results)

if __name__ == "__main__":
    main()