#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5A股非经营性房地产资产查询界面 - 美化版本
"""

import sys
import os
from typing import List, Dict
from datetime import datetime
import pandas as pd

# PyQt5导入
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableView,
    QProgressBar,
    QMessageBox,
    QFileDialog,
    QDateEdit,
    QGroupBox,
    QHeaderView,
    QSplitter,
    QFrame,
    QSpacerItem,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPainter, QBrush

# 导入数据查询服务
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_query_service import DataQueryService


class ModernStyleSheet:
    """现代化样式表"""
    
    MAIN_STYLE = """
    /* 主窗口样式 */
    QMainWindow {
        background-color: #f8f9fa;
        color: #2c3e50;
    }
    
    /* 应用整体样式 */
    QWidget {
        background-color: transparent;
        font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
        font-size: 11px;
    }
    
    /* 分组框样式 */
    QGroupBox {
        font-weight: bold;
        font-size: 12px;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 8px;
        background-color: white;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 8px 0 8px;
        color: #1976d2;
        background-color: white;
    }
    
    /* 标签样式 */
    QLabel {
        color: #2c3e50;
        font-weight: 500;
        padding: 2px;
    }
    
    QLabel#TitleLabel {
        font-size: 16px;
        font-weight: bold;
        color: #1976d2;
        padding: 8px 0px;
        border-bottom: 2px solid #e3f2fd;
        margin-bottom: 10px;
    }
    
    /* 输入框样式 */
    QLineEdit {
        border: 2px solid #e9ecef;
        border-radius: 6px;
        padding: 6px 8px;
        background-color: white;
        font-size: 11px;
    }
    
    QLineEdit:focus {
        border-color: #1976d2;
        background-color: #f8f9ff;
    }
    
    QLineEdit:hover {
        border-color: #90caf9;
    }
    
    /* 下拉框样式 */
    QComboBox {
        border: 2px solid #e9ecef;
        border-radius: 6px;
        padding: 6px 8px;
        background-color: white;
        font-size: 11px;
        min-width: 100px;
    }
    
    QComboBox:focus {
        border-color: #1976d2;
        background-color: #f8f9ff;
    }
    
    QComboBox:hover {
        border-color: #90caf9;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #666;
        margin-right: 5px;
    }
    
    /* 日期编辑框样式 */
    QDateEdit {
        border: 2px solid #e9ecef;
        border-radius: 6px;
        padding: 4px 6px;
        background-color: white;
        font-size: 11px;
        min-width: 110px;
    }
    
    QDateEdit:focus {
        border-color: #1976d2;
        background-color: #f8f9ff;
    }
    
    QDateEdit:hover {
        border-color: #90caf9;
    }
    
    QDateEdit::drop-down {
        border: none;
        width: 20px;
    }
    
    QDateEdit::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 4px solid #666;
        margin-right: 3px;
    }
    
    /* 按钮样式 */
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #1976d2, stop:1 #1565c0);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 11px;
        font-weight: 600;
        min-width: 80px;
        min-height: 32px;
    }
    
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #2196f3, stop:1 #1976d2);
    }
    
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #1565c0, stop:1 #0d47a1);
    }
    
    QPushButton:disabled {
        background: #bdbdbd;
        color: #666;
    }
    
    /* 特殊按钮样式 */
    QPushButton#QueryButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #4caf50, stop:1 #388e3c);
        min-width: 100px;
        font-weight: bold;
    }
    
    QPushButton#QueryButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #66bb6a, stop:1 #4caf50);
    }
    
    QPushButton#ExportButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #ff9800, stop:1 #f57c00);
        min-width: 100px;
    }
    
    QPushButton#ExportButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #ffb74d, stop:1 #ff9800);
    }
    
    /* 预设按钮样式 */
    QPushButton#PresetButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #e3f2fd, stop:1 #bbdefb);
        color: #1976d2;
        border: 1px solid #90caf9;
        min-width: 80px;
        font-weight: 500;
    }
    
    QPushButton#PresetButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #bbdefb, stop:1 #90caf9);
    }
    
    /* 表格样式 */
    QTableView {
        background-color: white;
        alternate-background-color: #f8f9fa;
        gridline-color: #e9ecef;
        border: 1px solid #dee2e6;
        border-radius: 6px;
        selection-background-color: #e3f2fd;
        selection-color: #1976d2;
        font-size: 10px;
    }
    
    QTableView::item {
        padding: 4px 8px;
        border: none;
    }
    
    QTableView::item:selected {
        background-color: #e3f2fd;
        color: #1976d2;
    }
    
    QTableView::item:hover {
        background-color: #f5f5f5;
    }
    
    /* 表头样式 */
    QHeaderView::section {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #f8f9fa, stop:1 #e9ecef);
        color: #2c3e50;
        border: 1px solid #dee2e6;
        padding: 6px 8px;
        font-weight: bold;
        font-size: 10px;
    }
    
    QHeaderView::section:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #e9ecef, stop:1 #dee2e6);
    }
    
    /* 进度条样式 */
    QProgressBar {
        border: 2px solid #e9ecef;
        border-radius: 6px;
        text-align: center;
        font-size: 10px;
        font-weight: bold;
        height: 20px;
        background-color: #f8f9fa;
    }
    
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #4caf50, stop:1 #388e3c);
        border-radius: 4px;
    }
    
    /* 状态栏样式 */
    QStatusBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #f8f9fa, stop:1 #e9ecef);
        border-top: 1px solid #dee2e6;
        color: #495057;
        font-size: 10px;
    }
    
    /* 分隔线样式 */
    QFrame#Separator {
        background-color: #e9ecef;
        max-height: 1px;
    }
    
    /* 滚动条样式 */
    QScrollBar:vertical {
        background: #f8f9fa;
        width: 12px;
        border: none;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background: #c1c1c1;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background: #a8a8a8;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    """


class QueryWorker(QThread):
    """数据查询工作线程"""
    
    # 定义信号
    progress = pyqtSignal(int)  # 进度信号
    finished = pyqtSignal(pd.DataFrame)  # 完成信号
    error = pyqtSignal(str)  # 错误信号
    
    def __init__(self, query_service: DataQueryService, **kwargs):
        """
        初始化查询工作线程
        
        Args:
            query_service: 数据查询服务
            **kwargs: 查询参数
        """
        super().__init__()
        self.query_service = query_service
        self.query_params = kwargs
        
    def run(self):
        """执行查询"""
        try:
            self.progress.emit(10)
            
            # 准备查询参数
            stock_codes = []
            stock_names = []
            
            # 解析股票代码和名称
            codes_text = self.query_params.get('stock_codes', '').strip()
            names_text = self.query_params.get('stock_names', '').strip()
            
            if codes_text:
                stock_codes = [code.strip() for code in codes_text.split(',') if code.strip()]
            
            if names_text:
                stock_names = [name.strip() for name in names_text.split(',') if name.strip()]
            
            market = self.query_params.get('market', '全部')
            subject_code = self.query_params.get('subject_code')
            industry = self.query_params.get('industry', '全行业')

            # 处理时点：兼容年份/财报期日期
            time_points: List[str] = []
            for i in range(4):
                date_value = self.query_params.get(f'time_point_{i}')
                if not date_value:
                    continue

                if isinstance(date_value, QDate):
                    if date_value.isValid() and not date_value.isNull():
                        time_points.append(date_value.toString('yyyy-MM-dd'))
                    continue

                token = str(date_value).strip()
                if token:
                    # 允许 '2024-06-30' / '2024/06/30' / '2024'
                    token = token.replace('/', '-')
                    time_points.append(token)

            self.progress.emit(30)

            # 执行查询
            df = self.query_service.query_data(
                stock_codes=stock_codes,
                stock_names=stock_names,
                market=market,
                time_points=time_points,
                subject_code=subject_code,
                industry=industry
            )
            
            self.progress.emit(100)
            
            # 发射完成信号
            self.finished.emit(df)
            
        except Exception as e:
            # 发射错误信号
            self.error.emit(str(e))


class RealEstateQueryApp(QMainWindow):
    """A股非经营性房地产资产查询主界面"""
    
    def __init__(self):
        """初始化主界面"""
        super().__init__()
        self.query_service = DataQueryService()
        self.query_worker = None
        self.current_data = pd.DataFrame()
        self.query_start_time = None
        self.last_query_params = None
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("A股非经营性房地产资产查询系统")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # 应用现代化样式
        self.setStyleSheet(ModernStyleSheet.MAIN_STYLE)
        
        # 设置主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 使用更紧凑的布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # 标题栏
        title_label = QLabel("A股非经营性房地产资产查询系统")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建分割器 - 调整比例让结果区域更大
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # 上半部分：查询条件 - 紧凑化
        query_group = self.create_compact_query_group()
        splitter.addWidget(query_group)
        
        # 下半部分：结果展示
        result_group = self.create_result_group()
        splitter.addWidget(result_group)
        
        # 设置分割比例 - 查询条件更紧凑
        splitter.setSizes([280, 600])
        
        # 状态栏
        self.statusBar().showMessage("就绪 - 请选择查询条件后点击查询")
        
    def create_compact_query_group(self) -> QGroupBox:
        """创建紧凑化的查询条件组"""
        group = QGroupBox("查询条件")
        group.setFlat(False)
        
        # 使用网格布局组织控件
        layout = QGridLayout(group)
        layout.setSpacing(8)  # 减少间距
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 第一行：科目选择和时点选择
        # 科目选择
        subject_label = QLabel("财务科目:")
        layout.addWidget(subject_label, 0, 0)
        
        subject_container = QWidget()
        subject_layout = QVBoxLayout(subject_container)
        subject_layout.setContentsMargins(0, 0, 0, 0)
        subject_layout.setSpacing(3)
        
        self.subject_combo = QComboBox()
        self.subject_combo.addItem("-- 选择科目 --", None)
        for subject in self.query_service.available_subjects:
            self.subject_combo.addItem(subject['name'], subject['code'])
        self.subject_combo.currentIndexChanged.connect(self.on_subject_changed)
        self.subject_combo.setMinimumWidth(180)
        subject_layout.addWidget(self.subject_combo)
        
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("或手动输入科目名称...")
        self.subject_input.setMaximumWidth(180)
        subject_layout.addWidget(self.subject_input)
        
        layout.addWidget(subject_container, 0, 1)
        
        # 时点选择
        time_label = QLabel("财报期选择:")
        layout.addWidget(time_label, 0, 2)
        
        time_container = QWidget()
        time_layout = QGridLayout(time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(3)
        
        # 创建时点编辑框 (2x2网格)
        self.time_edits = []
        empty_date = QDate(1900, 1, 1)
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for i, (row, col) in enumerate(positions):
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd")
            date_edit.setMinimumDate(empty_date)
            date_edit.setSpecialValueText("留空")
            date_edit.setDate(empty_date)
            date_edit.setMaximumWidth(110)
            self.time_edits.append(date_edit)
            time_layout.addWidget(date_edit, row, col)
        
        layout.addWidget(time_container, 0, 3, 2, 1)  # 占用2行
        
        # 第二行：预设按钮
        preset_container = QWidget()
        preset_layout = QHBoxLayout(preset_container)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.setSpacing(6)
        
        self.preset_quarter_button = QPushButton("最近季报")
        self.preset_quarter_button.setObjectName("PresetButton")
        self.preset_halfyear_button = QPushButton("最近半年报")
        self.preset_halfyear_button.setObjectName("PresetButton")
        self.preset_annual_button = QPushButton("最近年报")
        self.preset_annual_button.setObjectName("PresetButton")
        
        preset_layout.addWidget(self.preset_quarter_button)
        preset_layout.addWidget(self.preset_halfyear_button)
        preset_layout.addWidget(self.preset_annual_button)
        
        layout.addWidget(preset_container, 1, 0)
        
        # 标准财报期下拉框
        standard_container = QWidget()
        standard_layout = QVBoxLayout(standard_container)
        standard_layout.setContentsMargins(0, 0, 0, 0)
        standard_layout.setSpacing(3)
        
        self.standard_date_combo = QComboBox()
        self.standard_date_combo.addItem("-- 标准财报期 --", None)
        for date_str, label in self._get_standard_report_date_options():
            self.standard_date_combo.addItem(f"{date_str} ({label})", date_str)
        self.standard_date_combo.setMinimumWidth(150)
        standard_layout.addWidget(self.standard_date_combo)
        
        layout.addWidget(standard_container, 1, 1)
        
        # 第三行：筛选条件
        # 股票代码
        code_label = QLabel("股票代码:")
        layout.addWidget(code_label, 2, 0)
        
        self.stock_code_input = QLineEdit()
        self.stock_code_input.setPlaceholderText("多个代码用逗号分隔")
        self.stock_code_input.setMaximumWidth(180)
        layout.addWidget(self.stock_code_input, 2, 1)
        
        # 股票名称
        name_label = QLabel("股票名称:")
        layout.addWidget(name_label, 2, 2)
        
        self.stock_name_input = QLineEdit()
        self.stock_name_input.setPlaceholderText("支持模糊搜索")
        self.stock_name_input.setMaximumWidth(150)
        layout.addWidget(self.stock_name_input, 2, 3)
        
        # 第四行：市场和行业
        market_label = QLabel("市场:")
        layout.addWidget(market_label, 3, 0)
        
        self.market_combo = QComboBox()
        for market in self.query_service.markets:
            self.market_combo.addItem(market)
        self.market_combo.setMinimumWidth(120)
        layout.addWidget(self.market_combo, 3, 1)
        
        industry_label = QLabel("行业:")
        layout.addWidget(industry_label, 3, 2)
        
        self.industry_combo = QComboBox()
        self.industry_combo.addItem("全行业")
        for ind in self.query_service.get_industry_options():
            self.industry_combo.addItem(ind)
        self.industry_combo.setMinimumWidth(150)
        layout.addWidget(self.industry_combo, 3, 3)
        
        # 第五行：操作按钮
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        # 查询按钮
        self.query_button = QPushButton("🔍 查询")
        self.query_button.setObjectName("QueryButton")
        self.query_button.setMinimumWidth(100)
        button_layout.addWidget(self.query_button)
        
        # 重置按钮
        self.reset_button = QPushButton("🔄 重置")
        self.reset_button.setMinimumWidth(80)
        button_layout.addWidget(self.reset_button)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumWidth(200)
        button_layout.addWidget(self.progress_bar)
        
        button_layout.addStretch()
        
        layout.addWidget(button_container, 4, 0, 1, 4)  # 跨越4列
        
        # 连接预设相关信号
        self.preset_quarter_button.clicked.connect(lambda: self.apply_report_date_preset("quarter"))
        self.preset_halfyear_button.clicked.connect(lambda: self.apply_report_date_preset("halfyear"))
        self.preset_annual_button.clicked.connect(lambda: self.apply_report_date_preset("annual"))
        self.standard_date_combo.currentIndexChanged.connect(self.on_standard_date_selected)
        
        return group
    
    def create_result_group(self) -> QGroupBox:
        """创建美化的结果展示组"""
        group = QGroupBox("查询结果")
        group.setFlat(False)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 分隔线
        separator = QFrame()
        separator.setObjectName("Separator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # 结果统计信息
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        
        self.result_count_label = QLabel("记录数: 0")
        self.result_count_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #e8f5e8;
                border-radius: 4px;
                border: 1px solid #c8e6c9;
            }
        """)
        
        self.query_time_label = QLabel("查询用时: 0ms")
        self.query_time_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 8px;
                background-color: #e3f2fd;
                border-radius: 4px;
                border: 1px solid #bbdefb;
            }
        """)
        
        info_layout.addWidget(self.result_count_label)
        info_layout.addWidget(self.query_time_label)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # 结果表格 - 使用更美观的设置
        self.result_table = QTableView()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QTableView.SelectRows)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.result_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.result_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 设置表格字体和样式
        font = QFont("Microsoft YaHei", 10)
        self.result_table.setFont(font)
        
        # 设置表格最小高度
        self.result_table.setMinimumHeight(400)
        
        layout.addWidget(self.result_table)
        
        # 分隔线
        separator2 = QFrame()
        separator2.setObjectName("Separator")
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator2)
        
        # 底部操作区域
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 8, 0, 0)
        bottom_layout.setSpacing(10)
        
        # 导出按钮
        self.export_button = QPushButton("📊 导出Excel")
        self.export_button.setObjectName("ExportButton")
        self.export_button.setMinimumWidth(120)
        self.export_button.setMinimumHeight(35)
        self.export_button.setEnabled(False)  # 默认禁用
        bottom_layout.addWidget(self.export_button)
        
        # 清空结果按钮
        self.clear_button = QPushButton("🗑️ 清空结果")
        self.clear_button.setMinimumWidth(100)
        self.clear_button.setMinimumHeight(35)
        self.clear_button.setEnabled(False)
        bottom_layout.addWidget(self.clear_button)
        
        bottom_layout.addStretch()
        
        # 刷新按钮
        self.refresh_button = QPushButton("🔄 刷新数据")
        self.refresh_button.setMinimumWidth(100)
        self.refresh_button.setMinimumHeight(35)
        self.refresh_button.setEnabled(False)
        bottom_layout.addWidget(self.refresh_button)
        
        layout.addWidget(bottom_container)
        
        return group
    
    def setup_connections(self):
        """设置信号连接"""
        self.query_button.clicked.connect(self.start_query)
        self.reset_button.clicked.connect(self.reset_form)
        self.export_button.clicked.connect(self.export_data)
        self.clear_button.clicked.connect(self.clear_results)
        self.refresh_button.clicked.connect(self.refresh_data)
        
    def on_subject_changed(self, index):
        """科目选择变化处理"""
        # 如果选择了下拉框中的项目，清空手动输入框
        if index > 0:
            self.subject_input.clear()

    @staticmethod
    def _is_time_edit_empty(date_edit: QDateEdit) -> bool:
        return date_edit.date() == date_edit.minimumDate()

    def _collect_selected_report_dates(self) -> List[str]:
        dates: List[str] = []
        seen = set()
        for date_edit in self.time_edits:
            if self._is_time_edit_empty(date_edit):
                continue
            d = date_edit.date().toString('yyyy-MM-dd')
            if d in seen:
                continue
            seen.add(d)
            dates.append(d)
        return dates

    def _add_report_date_to_next_slot(self, report_date: QDate) -> None:
        if not report_date or report_date.isNull() or not report_date.isValid():
            return

        report_date_str = report_date.toString('yyyy-MM-dd')
        if report_date_str in set(self._collect_selected_report_dates()):
            QMessageBox.information(self, "提示", f"时点 {report_date_str} 已经选择过")
            return

        for date_edit in self.time_edits:
            if self._is_time_edit_empty(date_edit):
                date_edit.setDate(report_date)
                return

        QMessageBox.warning(self, "警告", "最多只能选择4个时点")

    def _get_latest_quarter_end(self) -> QDate:
        today = datetime.now().date()
        year = today.year

        candidates = [
            (12, 31),
            (9, 30),
            (6, 30),
            (3, 31),
        ]
        for month, day in candidates:
            d = datetime(year, month, day).date()
            if today >= d:
                return QDate(year, month, day)

        # 如果在 Q1 之前，则取上一年年报
        return QDate(year - 1, 12, 31)

    def _get_latest_halfyear_end(self) -> QDate:
        today = datetime.now().date()
        year = today.year
        half = datetime(year, 6, 30).date()
        if today >= half:
            return QDate(year, 6, 30)
        return QDate(year - 1, 6, 30)

    def _get_latest_annual_end(self) -> QDate:
        today = datetime.now().date()
        year = today.year
        annual = datetime(year, 12, 31).date()
        if today >= annual:
            return QDate(year, 12, 31)
        return QDate(year - 1, 12, 31)

    def apply_report_date_preset(self, preset: str) -> None:
        """将预设时点填入到下一个空位（最多4个）。"""
        if preset == 'quarter':
            q = self._get_latest_quarter_end()
            self._add_report_date_to_next_slot(q)
        elif preset == 'halfyear':
            h = self._get_latest_halfyear_end()
            self._add_report_date_to_next_slot(h)
        elif preset == 'annual':
            a = self._get_latest_annual_end()
            self._add_report_date_to_next_slot(a)

    def _get_standard_report_date_options(self, years_back: int = 6) -> List[tuple[str, str]]:
        """生成标准财报期列表（用于下拉框展示）。"""
        year = datetime.now().year
        labels = [
            (12, 31, '年报'),
            (9, 30, '三季报'),
            (6, 30, '半年报'),
            (3, 31, '一季报'),
        ]

        options: List[tuple[str, str]] = []
        for y in range(year, year - years_back - 1, -1):
            for m, d, label in labels:
                options.append((f"{y:04d}-{m:02d}-{d:02d}", label))
        return options

    def on_standard_date_selected(self, index: int) -> None:
        date_str = self.standard_date_combo.currentData()
        if not date_str:
            return

        qdate = QDate.fromString(str(date_str), 'yyyy-MM-dd')
        if qdate.isValid():
            self._add_report_date_to_next_slot(qdate)

        # 复位，避免重复触发
        self.standard_date_combo.setCurrentIndex(0)

    def validate_input(self) -> bool:
        """验证输入参数"""
        selected_dates = self._collect_selected_report_dates()

        # 检查是否有至少一个时点
        if not selected_dates:
            reply = QMessageBox.question(
                self, "确认", "未选择时点，将查询所有可用数据，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return False

        return True

    def start_query(self):
        """开始查询"""
        if not self.validate_input():
            return

        query_params = {
            'stock_codes': self.stock_code_input.text(),
            'stock_names': self.stock_name_input.text(),
            'market': self.market_combo.currentText(),
            'industry': self.industry_combo.currentText(),
            'subject_code': self.subject_combo.currentData()
        }

        for i, date_edit in enumerate(self.time_edits):
            query_params[f'time_point_{i}'] = (
                date_edit.date().toString('yyyy-MM-dd') if not self._is_time_edit_empty(date_edit) else None
            )

        self.execute_query(query_params)
    
    def execute_query(self, query_params: Dict):
        """执行查询"""
        # 记录开始时间
        self.query_start_time = datetime.now()
        
        # 禁用界面控件
        self.set_ui_enabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 更新状态栏
        self.statusBar().showMessage("🔍 正在查询数据，请稍候...")
        
        # 创建并启动工作线程
        self.query_worker = QueryWorker(self.query_service, **query_params)
        self.query_worker.progress.connect(self.progress_bar.setValue)
        self.query_worker.finished.connect(self.on_query_finished)
        self.query_worker.error.connect(self.on_query_error)
        
        self.query_worker.start()
    
    def on_query_finished(self, df: pd.DataFrame):
        """查询完成处理"""
        self.current_data = df
        
        # 计算查询用时
        query_end_time = datetime.now()
        query_duration = (query_end_time - self.query_start_time).total_seconds() * 1000  # 毫秒
        
        # 更新界面
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        
        # 显示结果
        self.display_results(df)
        
        # 更新统计信息
        self.update_result_stats(len(df), query_duration)
        
        # 更新状态和按钮状态
        if df.empty:
            self.statusBar().showMessage("❌ 查询完成：未找到符合条件的数据")
            self.export_button.setEnabled(False)
            self.clear_button.setEnabled(False)
            self.refresh_button.setEnabled(False)
            QMessageBox.information(self, "提示", "未找到符合条件的数据")
        else:
            self.statusBar().showMessage(f"✅ 查询完成：共找到 {len(df)} 条记录，用时 {query_duration:.0f}ms")
            self.export_button.setEnabled(True)
            self.clear_button.setEnabled(True)
            self.refresh_button.setEnabled(True)
    
    def on_query_error(self, error_msg: str):
        """查询错误处理"""
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("查询失败")
        
        QMessageBox.critical(self, "查询错误", f"查询过程中发生错误：\n{error_msg}")
    
    def set_ui_enabled(self, enabled: bool):
        """设置界面控件可用性"""
        self.query_button.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)
        self.subject_combo.setEnabled(enabled)
        self.subject_input.setEnabled(enabled)

        for date_edit in self.time_edits:
            date_edit.setEnabled(enabled)

        self.preset_quarter_button.setEnabled(enabled)
        self.preset_halfyear_button.setEnabled(enabled)
        self.preset_annual_button.setEnabled(enabled)
        self.standard_date_combo.setEnabled(enabled)

        self.stock_code_input.setEnabled(enabled)
        self.stock_name_input.setEnabled(enabled)
        self.market_combo.setEnabled(enabled)
        self.industry_combo.setEnabled(enabled)

        if enabled:
            self.export_button.setEnabled(not self.current_data.empty)
    
    def display_results(self, df: pd.DataFrame):
        """显示查询结果"""
        if df.empty:
            # 清空表格
            self.result_table.setModel(None)
            return
        
        # 创建数据模型
        from PyQt5.QtGui import QStandardItemModel, QStandardItem
        
        model = QStandardItemModel()
        
        # 设置列标题
        headers = list(df.columns)
        model.setHorizontalHeaderLabels(headers)
        
        # 添加数据行
        for row_idx, row in df.iterrows():
            row_items = []
            for col_idx, value in enumerate(row):
                item = QStandardItem(str(value) if pd.notna(value) else "")
                item.setToolTip(str(value) if pd.notna(value) else "")
                row_items.append(item)
            model.appendRow(row_items)
        
        # 设置表格模型
        self.result_table.setModel(model)
        
        # 设置列宽
        header = self.result_table.horizontalHeader()
        for i, col_name in enumerate(headers):
            # 根据列名设置合适的宽度
            if "代码" in col_name or "名称" in col_name:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            elif "行业" in col_name:
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    
    def export_data(self):
        """导出数据"""
        if self.current_data.empty:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
        
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "导出Excel", 
            f"A股房地产资产查询结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        # 执行导出
        try:
            success = self.query_service.export_to_excel(self.current_data, file_path)
            
            if success:
                QMessageBox.information(self, "成功", f"数据已成功导出到：\n{file_path}")
            else:
                QMessageBox.critical(self, "失败", "数据导出失败，请检查文件路径和权限")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出过程中发生错误：\n{str(e)}")
    
    def reset_form(self):
        """重置表单"""
        self.subject_combo.setCurrentIndex(0)
        self.subject_input.clear()

        for date_edit in self.time_edits:
            date_edit.setDate(date_edit.minimumDate())

        self.standard_date_combo.setCurrentIndex(0)

        self.stock_code_input.clear()
        self.stock_name_input.clear()
        self.market_combo.setCurrentIndex(0)
        self.industry_combo.setCurrentIndex(0)

        self.current_data = pd.DataFrame()
        self.result_table.setModel(None)
        self.export_button.setEnabled(False)

        self.statusBar().showMessage("已重置")
    
    def update_result_stats(self, record_count: int, query_time_ms: float):
        """更新结果统计信息"""
        self.result_count_label.setText(f"📊 记录数: {record_count:,}")
        self.query_time_label.setText(f"⏱️ 查询用时: {query_time_ms:.0f}ms")
        
        # 根据记录数设置不同颜色
        if record_count == 0:
            self.result_count_label.setStyleSheet("""
                QLabel {
                    color: #d32f2f;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 4px 8px;
                    background-color: #ffebee;
                    border-radius: 4px;
                    border: 1px solid #ffcdd2;
                }
            """)
        elif record_count < 100:
            self.result_count_label.setStyleSheet("""
                QLabel {
                    color: #f57c00;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 4px 8px;
                    background-color: #fff3e0;
                    border-radius: 4px;
                    border: 1px solid #ffcc02;
                }
            """)
        else:
            self.result_count_label.setStyleSheet("""
                QLabel {
                    color: #2e7d32;
                    font-weight: bold;
                    font-size: 11px;
                    padding: 4px 8px;
                    background-color: #e8f5e8;
                    border-radius: 4px;
                    border: 1px solid #c8e6c9;
                }
            """)
    
    def clear_results(self):
        """清空结果"""
        self.current_data = pd.DataFrame()
        self.result_table.setModel(None)
        self.result_count_label.setText("📊 记录数: 0")
        self.query_time_label.setText("⏱️ 查询用时: 0ms")
        
        self.export_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        
        self.statusBar().showMessage("🗑️ 结果已清空")
    
    def refresh_data(self):
        """刷新数据 - 使用当前查询条件重新查询"""
        if not hasattr(self, 'last_query_params') or self.last_query_params is None:
            QMessageBox.warning(self, "警告", "没有可刷新的查询条件")
            return
        
        self.statusBar().showMessage("🔄 正在刷新数据...")
        self.execute_query(self.last_query_params)
    
    def start_query(self):
        """开始查询"""
        if not self.validate_input():
            return

        query_params = {
            'stock_codes': self.stock_code_input.text(),
            'stock_names': self.stock_name_input.text(),
            'market': self.market_combo.currentText(),
            'industry': self.industry_combo.currentText(),
            'subject_code': self.subject_combo.currentData()
        }

        for i, date_edit in enumerate(self.time_edits):
            query_params[f'time_point_{i}'] = (
                date_edit.date().toString('yyyy-MM-dd') if not self._is_time_edit_empty(date_edit) else None
            )

        # 保存查询参数用于刷新
        self.last_query_params = query_params.copy()
        
        self.execute_query(query_params)

    def closeEvent(self, event):
        """关闭事件"""
        # 如果有正在运行的查询线程，先停止
        if self.query_worker and self.query_worker.isRunning():
            self.query_worker.terminate()
            self.query_worker.wait()
        
        event.accept()


def main():
    """主函数（供直接调用）"""
    # 创建QApplication（如果在其他地方没有创建的话）
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("A股非经营性房地产资产查询系统")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("DataQuery System")
    
    # 创建主窗口
    window = RealEstateQueryApp()
    window.show()
    
    # 启动事件循环
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()