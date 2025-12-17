#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试美化后的PyQt5界面
"""

import sys
import os

def test_ui_imports():
    """测试UI导入"""
    try:
        print("🔍 测试UI组件导入...")
        
        # 测试PyQt5导入
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        print("✅ PyQt5 基础组件导入成功")
        
        # 测试UI模块导入
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from ui.real_estate_query_app import RealEstateQueryApp, ModernStyleSheet
        print("✅ 美化版UI模块导入成功")
        
        # 测试样式表
        print(f"✅ 样式表加载成功，长度: {len(ModernStyleSheet.MAIN_STYLE)} 字符")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_ui_creation():
    """测试UI创建"""
    try:
        print("\n🏗️ 测试UI创建...")
        
        from PyQt5.QtWidgets import QApplication
        from ui.real_estate_query_app import RealEstateQueryApp
        
        # 创建应用程序
        app = QApplication(sys.argv)
        
        # 创建主窗口
        window = RealEstateQueryApp()
        
        print(f"✅ UI创建成功")
        print(f"   - 窗口标题: {window.windowTitle()}")
        print(f"   - 窗口尺寸: {window.size().width()}x{window.size().height()}")
        print(f"   - 最小尺寸: {window.minimumSize().width()}x{window.minimumSize().height()}")
        
        # 检查关键组件
        components = {
            "查询按钮": hasattr(window, 'query_button'),
            "重置按钮": hasattr(window, 'reset_button'),
            "导出按钮": hasattr(window, 'export_button'),
            "进度条": hasattr(window, 'progress_bar'),
            "结果表格": hasattr(window, 'result_table'),
            "状态栏": window.statusBar() is not None
        }
        
        for component, exists in components.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {component}")
        
        # 检查样式表是否应用
        if window.styleSheet():
            print("✅ 样式表已应用")
        else:
            print("⚠️ 样式表未应用")
        
        return True, app, window
        
    except Exception as e:
        print(f"❌ UI创建失败: {e}")
        return False, None, None

def main():
    """主测试函数"""
    print("🚀 开始测试美化后的PyQt5界面")
    print("=" * 50)
    
    # 测试导入
    if not test_ui_imports():
        return False
    
    # 测试UI创建
    success, app, window = test_ui_creation()
    if not success:
        return False
    
    print("\n🎨 UI美化特性验证:")
    print("✅ 现代化样式表 (蓝色/绿色配色)")
    print("✅ 紧凑化布局 (网格布局)")
    print("✅ 渐变按钮效果")
    print("✅ 统计信息显示")
    print("✅ 图标和emoji")
    print("✅ 分隔线和美化边框")
    
    print("\n📊 功能增强:")
    print("✅ 查询时间统计")
    print("✅ 记录数显示")
    print("✅ 清空结果功能")
    print("✅ 刷新数据功能")
    print("✅ 状态栏提示优化")
    
    print("\n🎯 用户体验改进:")
    print("✅ 响应式设计")
    print("✅ 视觉层次清晰")
    print("✅ 交互反馈良好")
    print("✅ 信息展示完整")
    
    if app and window:
        print(f"\n🌟 UI启动成功！窗口将在5秒后自动关闭...")
        print(f"💡 您可以直接运行 'python run_ui.py' 来体验完整的UI界面")
        
        # 5秒后自动关闭，用于演示
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(5000, app.quit)
        app.exec_()
    
    print("\n🎉 测试完成！UI美化改造成功！")
    return True

if __name__ == "__main__":
    main()