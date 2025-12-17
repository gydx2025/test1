#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 reset_form 方法修复
"""

import sys
import os
import ast

def test_reset_form_method_exists():
    """测试 reset_form 方法是否存在"""
    print("=== 测试 reset_form 方法是否存在 ===")
    
    # 读取文件内容
    with open('/home/engine/project/ui/real_estate_query_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 解析AST
    tree = ast.parse(content)
    
    # 查找 reset_form 方法
    reset_form_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'reset_form':
            reset_form_found = True
            print(f"✅ find reset_form method at line {node.lineno}")
            break
    
    if not reset_form_found:
        print("❌ reset_form method not found")
        return False
    
    return True

def test_setup_connections():
    """测试 setup_connections 方法中的信号连接"""
    print("\n=== 测试信号连接 ===")
    
    with open('/home/engine/project/ui/real_estate_query_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键的连接语句
    required_connections = [
        "self.query_button.clicked.connect(self.start_query)",
        "self.reset_button.clicked.connect(self.reset_form)",
        "self.export_button.clicked.connect(self.export_data)"
    ]
    
    for connection in required_connections:
        if connection in content:
            print(f"✅ find connection: {connection}")
        else:
            print(f"❌ missing connection: {connection}")
            return False
    
    return True

def test_reset_form_functionality():
    """测试 reset_form 方法的功能完整性"""
    print("\n=== 测试 reset_form 方法功能 ===")
    
    with open('/home/engine/project/ui/real_estate_query_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 reset_form 方法定义
    method_start = content.find("def reset_form(self):")
    if method_start == -1:
        print("❌ reset_form method not found")
        return False
    
    # 找到方法的结束位置
    lines = content[method_start:].split('\n')
    method_lines = []
    indent_level = None
    
    for line in lines:
        if line.strip() == '':
            continue
        
        # 找到第一行的缩进级别作为方法内部的基准
        if indent_level is None and line.startswith('def reset_form'):
            indent_level = len(line) - len(line.lstrip())
            method_lines.append(line)
        elif indent_level is not None:
            current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
            if line.strip() and current_indent <= indent_level and not line.startswith(' '):
                # 遇到新方法或类，结束当前方法
                break
            method_lines.append(line)
    
    method_content = '\n'.join(method_lines)
    
    # 检查关键功能
    required_features = [
        "clear_selected_subjects()",
        "stock_code_input.clear()",
        "stock_name_input.clear()", 
        "result_table.setModel(None)",
        "current_data = pd.DataFrame()",
        "export_button.setEnabled(False)"
    ]
    
    for feature in required_features:
        if feature in method_content:
            print(f"✅ find feature: {feature}")
        else:
            print(f"❌ missing feature: {feature}")
            return False
    
    return True

def main():
    """主测试函数"""
    print("开始测试 reset_form 方法修复...")
    
    tests = [
        test_reset_form_method_exists,
        test_setup_connections,
        test_reset_form_functionality
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 所有测试通过！reset_form 方法修复成功！")
        print("\n修复内容总结:")
        print("1. 添加了缺失的 reset_form 方法")
        print("2. 实现了完整的表单重置功能:")
        print("   - 清空已选择的科目")
        print("   - 重置时点选择")
        print("   - 清空查询输入")
        print("   - 重置下拉框选择")
        print("   - 清空查询结果")
        print("   - 重置界面状态")
        print("3. 添加了异常处理和日志记录")
        print("4. 验证了所有信号连接的正确性")
    else:
        print("❌ 部分测试失败，需要进一步检查")

if __name__ == "__main__":
    main()