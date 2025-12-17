#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5A股非经营性房地产资产查询界面
"""

import sys
import os
from typing import List, Dict
from datetime import datetime
import pandas as pd
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PyQt5导入
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
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
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont

# 导入数据查询服务
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_query_service import DataQueryService


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
            logger.info("=== 开始查询线程 ===")
            self.progress.emit(10)
            
            # 准备查询参数
            stock_codes = []
            stock_names = []
            
            # 解析股票代码和名称
            codes_text = self.query_params.get('stock_codes', '').strip()
            names_text = self.query_params.get('stock_names', '').strip()
            
            logger.info(f"股票代码输入: {codes_text}")
            logger.info(f"股票名称输入: {names_text}")
            
            if codes_text:
                stock_codes = [code.strip() for code in codes_text.split(',') if code.strip()]
            
            if names_text:
                stock_names = [name.strip() for name in names_text.split(',') if name.strip()]
            
            logger.info(f"解析后的股票代码: {stock_codes}")
            logger.info(f"解析后的股票名称: {stock_names}")
            
            market = self.query_params.get('market', '全部')
            subject_codes = self.query_params.get('subject_codes', [])
            industry = self.query_params.get('industry', '全行业')
            
            logger.info(f"市场: {market}, 行业: {industry}")
            logger.info(f"科目代码: {subject_codes}")

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

            logger.info(f"时点: {time_points}")
            self.progress.emit(30)

            # 执行查询
            logger.info("开始执行数据查询...")
            df = self.query_service.query_data(
                stock_codes=stock_codes if stock_codes else None,
                stock_names=stock_names if stock_names else None,
                market=market,
                time_points=time_points if time_points else None,
                subject_codes=subject_codes if subject_codes else None,
                industry=industry
            )
            
            logger.info(f"查询完成，返回 {len(df)} 条记录")
            self.progress.emit(100)
            
            # 发射完成信号
            self.finished.emit(df)
            logger.info("=== 查询线程完成 ===")
            
        except Exception as e:
            logger.error(f"查询过程中发生错误: {str(e)}", exc_info=True)
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
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("A股非经营性房地产资产查询系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # 上半部分：查询条件
        query_group = self.create_query_group()
        splitter.addWidget(query_group)
        
        # 下半部分：结果展示
        result_group = self.create_result_group()
        splitter.addWidget(result_group)
        
        # 设置分割比例
        splitter.setSizes([300, 500])
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def create_query_group(self) -> QGroupBox:
        """创建查询条件组"""
        group = QGroupBox("查询条件")
        layout = QVBoxLayout(group)

        # 第一行：科目选择 + 时点选择
        row1_layout = QHBoxLayout()

        # 科目选择（多选，最多3个）
        subject_layout = QVBoxLayout()
        subject_layout.addWidget(QLabel("资产负债表科目 (最多选择3个):"))

        # 创建多选科目下拉框
        self.subject_combo = QComboBox()
        self.subject_combo.addItem("-- 选择科目 --", None)
        for subject in self.query_service.available_subjects:
            self.subject_combo.addItem(subject['name'], subject['code'])
        self.subject_combo.currentIndexChanged.connect(self.on_subject_changed)
        subject_layout.addWidget(self.subject_combo)

        # 已选择的科目显示
        self.selected_subjects = []
        self.selected_subjects_layout = QVBoxLayout()
        self.subject_label = QLabel("已选择的科目:")
        self.subject_label.setVisible(False)
        self.selected_subjects_layout.addWidget(self.subject_label)
        
        self.selected_subjects_text = QLabel("")
        self.selected_subjects_text.setVisible(False)
        self.selected_subjects_layout.addWidget(self.selected_subjects_text)
        
        subject_layout.addLayout(self.selected_subjects_layout)

        row1_layout.addLayout(subject_layout)
        row1_layout.addStretch()

        # 时点选择
        time_layout = QVBoxLayout()
        time_layout.addWidget(QLabel("财报期选择 (最多4个):"))

        time_points_layout = QHBoxLayout()
        self.time_edits = []
        empty_date = QDate(1900, 1, 1)
        for i in range(4):
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("yyyy-MM-dd")
            date_edit.setMinimumDate(empty_date)
            date_edit.setSpecialValueText("留空")
            date_edit.setDate(empty_date)
            # 添加日期变化监听
            date_edit.dateChanged.connect(self.on_time_point_changed)
            self.time_edits.append(date_edit)
            time_points_layout.addWidget(date_edit)

        time_layout.addLayout(time_points_layout)

        # 预设 & 标准时点
        preset_layout = QHBoxLayout()

        self.preset_quarter_button = QPushButton("最近季报")
        self.preset_halfyear_button = QPushButton("最近半年报")
        self.preset_annual_button = QPushButton("最近年报")

        preset_layout.addWidget(self.preset_quarter_button)
        preset_layout.addWidget(self.preset_halfyear_button)
        preset_layout.addWidget(self.preset_annual_button)
        preset_layout.addStretch()

        preset_layout.addWidget(QLabel("标准财报期:"))
        self.standard_date_combo = QComboBox()
        self.standard_date_combo.addItem("-- 选择后自动填入 --", None)
        for date_str, label in self._get_standard_report_date_options():
            self.standard_date_combo.addItem(f"{date_str} ({label})", date_str)
        preset_layout.addWidget(self.standard_date_combo)

        time_layout.addLayout(preset_layout)
        row1_layout.addLayout(time_layout)

        layout.addLayout(row1_layout)

        # 第二行：查询条件
        row2_layout = QHBoxLayout()

        # 股票代码
        code_layout = QVBoxLayout()
        code_layout.addWidget(QLabel("股票代码:"))
        self.stock_code_input = QLineEdit()
        self.stock_code_input.setPlaceholderText("多个代码用逗号分隔，留空表示全部")
        code_layout.addWidget(self.stock_code_input)
        row2_layout.addLayout(code_layout)

        # 股票名称
        name_layout = QVBoxLayout()
        name_layout.addWidget(QLabel("股票名称:"))
        self.stock_name_input = QLineEdit()
        self.stock_name_input.setPlaceholderText("支持模糊搜索，多个名称用逗号分隔")
        name_layout.addWidget(self.stock_name_input)
        row2_layout.addLayout(name_layout)

        # 市场选择
        market_layout = QVBoxLayout()
        market_layout.addWidget(QLabel("市场:"))
        self.market_combo = QComboBox()
        for market in self.query_service.markets:
            self.market_combo.addItem(market)
        market_layout.addWidget(self.market_combo)
        row2_layout.addLayout(market_layout)

        # 行业选择
        industry_layout = QVBoxLayout()
        industry_layout.addWidget(QLabel("行业分类:"))
        self.industry_combo = QComboBox()
        self.industry_combo.addItem("全行业")
        for ind in self.query_service.get_industry_options():
            self.industry_combo.addItem(ind)
        industry_layout.addWidget(self.industry_combo)
        row2_layout.addLayout(industry_layout)

        layout.addLayout(row2_layout)

        # 第三行：按钮
        button_layout = QHBoxLayout()

        self.query_button = QPushButton("查询")
        self.query_button.setMinimumHeight(40)
        self.query_button.setFont(QFont("Arial", 10, QFont.Bold))
        button_layout.addWidget(self.query_button)

        self.reset_button = QPushButton("重置")
        self.reset_button.setMinimumHeight(40)
        button_layout.addWidget(self.reset_button)

        button_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)

        layout.addLayout(button_layout)

        # 连接预设相关信号
        self.preset_quarter_button.clicked.connect(lambda: self.apply_report_date_preset("quarter"))
        self.preset_halfyear_button.clicked.connect(lambda: self.apply_report_date_preset("halfyear"))
        self.preset_annual_button.clicked.connect(lambda: self.apply_report_date_preset("annual"))
        self.standard_date_combo.currentIndexChanged.connect(self.on_standard_date_selected)

        return group
    
    def create_result_group(self) -> QGroupBox:
        """创建结果展示组"""
        group = QGroupBox("查询结果")
        layout = QVBoxLayout(group)
        
        # 结果表格
        self.result_table = QTableView()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(QTableView.SelectRows)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        
        # 设置表格字体
        font = QFont("Microsoft YaHei", 9)
        self.result_table.setFont(font)
        
        layout.addWidget(self.result_table)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.export_button = QPushButton("导出Excel")
        self.export_button.setMinimumHeight(35)
        self.export_button.setEnabled(False)  # 默认禁用
        bottom_layout.addWidget(self.export_button)
        
        layout.addLayout(bottom_layout)
        
        return group
    
    def setup_connections(self):
        """设置信号连接"""
        self.query_button.clicked.connect(self.start_query)
        self.reset_button.clicked.connect(self.reset_form)
        self.export_button.clicked.connect(self.export_data)
        
    def on_subject_changed(self, index):
        """科目选择变化处理"""
        if index == 0:  # 如果选择了"-- 选择科目 --"，不做任何处理
            return
        
        selected_code = self.subject_combo.currentData()
        selected_name = self.subject_combo.currentText()
        
        if not selected_code:
            return
            
        # 检查是否已经选择了这个科目
        if any(subj['code'] == selected_code for subj in self.selected_subjects):
            QMessageBox.information(self, "提示", f"科目 '{selected_name}' 已经被选择")
            return
            
        # 检查是否已达到最大选择数量（3个）
        if len(self.selected_subjects) >= 3:
            QMessageBox.warning(self, "警告", "最多只能选择3个科目")
            return
            
        # 添加科目到已选择列表
        self.selected_subjects.append({
            'code': selected_code,
            'name': selected_name
        })
        
        # 更新已选择科目的显示
        self._update_selected_subjects_display()
        
        # 重置下拉框到第一项
        self.subject_combo.setCurrentIndex(0)
    
    def _update_selected_subjects_display(self):
        """更新已选择科目的显示"""
        if not self.selected_subjects:
            self.subject_label.setVisible(False)
            self.selected_subjects_text.setVisible(False)
        else:
            self.subject_label.setVisible(True)
            self.selected_subjects_text.setVisible(True)
            
            # 显示已选择的科目
            subject_names = [f"{i+1}. {subj['name']}" for i, subj in enumerate(self.selected_subjects)]
            self.selected_subjects_text.setText("\n".join(subject_names))
            
            # 添加清除按钮
            if not hasattr(self, 'clear_subjects_button'):
                self.clear_subjects_button = QPushButton("清除已选科目")
                self.clear_subjects_button.clicked.connect(self.clear_selected_subjects)
                self.selected_subjects_layout.addWidget(self.clear_subjects_button)
                
            self.clear_subjects_button.setVisible(True)
    
    def clear_selected_subjects(self):
        """清除所有已选择的科目"""
        self.selected_subjects.clear()
        self._update_selected_subjects_display()
        if hasattr(self, 'clear_subjects_button'):
            self.clear_subjects_button.setVisible(False)
    
    def on_time_point_changed(self, date=None):
        """财报期变化处理 - 实时更新状态栏显示"""
        selected_dates = self._collect_selected_report_dates()
        if selected_dates:
            dates_str = ", ".join(selected_dates)
            self.statusBar().showMessage(f"已选择时点: {dates_str}")
        else:
            self.statusBar().showMessage("就绪 - 请选择财报期")
            
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
        # 检查是否选择了科目
        if not self.selected_subjects:
            QMessageBox.warning(self, "警告", "请至少选择一个科目")
            return False
            
        # 检查是否有至少一个时点
        selected_dates = self._collect_selected_report_dates()
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
            'subject_codes': [subj['code'] for subj in self.selected_subjects],
            'subject_names': [subj['name'] for subj in self.selected_subjects]
        }

        for i, date_edit in enumerate(self.time_edits):
            query_params[f'time_point_{i}'] = (
                date_edit.date().toString('yyyy-MM-dd') if not self._is_time_edit_empty(date_edit) else None
            )

        self.execute_query(query_params)
    
    def execute_query(self, query_params: Dict):
        """执行查询"""
        # 禁用界面控件
        self.set_ui_enabled(False)
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.query_worker = QueryWorker(self.query_service, **query_params)
        self.query_worker.progress.connect(self.progress_bar.setValue)
        self.query_worker.finished.connect(self.on_query_finished)
        self.query_worker.error.connect(self.on_query_error)
        
        self.statusBar().showMessage("正在查询...")
        self.query_worker.start()
    
    def on_query_finished(self, df: pd.DataFrame):
        """查询完成处理"""
        try:
            logger.info(f"查询完成，返回 {len(df)} 条记录")
            self.current_data = df
            
            # 更新界面
            self.set_ui_enabled(True)
            self.progress_bar.setVisible(False)
            
            # 显示结果
            self.display_results(df)
            
            # 更新状态
            if df.empty:
                self.statusBar().showMessage("查询完成：无数据")
                logger.info("查询结果为空")
                QMessageBox.information(self, "提示", "未找到符合条件的数据")
            else:
                self.statusBar().showMessage(f"查询完成：共 {len(df)} 条记录")
                self.export_button.setEnabled(True)
                logger.info(f"成功显示查询结果，共 {len(df)} 条记录")
        except Exception as e:
            logger.error(f"处理查询结果时出错: {str(e)}", exc_info=True)
            self.set_ui_enabled(True)
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "处理错误", f"处理查询结果时出错：\n{str(e)}")
    
    def on_query_error(self, error_msg: str):
        """查询错误处理"""
        logger.error(f"查询过程中发生错误: {error_msg}")
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("查询失败")
        
        QMessageBox.critical(self, "查询错误", f"查询过程中发生错误：\n{error_msg}")
    
    def set_ui_enabled(self, enabled: bool):
        """设置界面控件可用性"""
        self.query_button.setEnabled(enabled)
        self.reset_button.setEnabled(enabled)
        self.subject_combo.setEnabled(enabled)

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
            logger.info("查询结果为空")
            return
        
        try:
            logger.info(f"开始显示 {len(df)} 条查询结果")
            
            # 创建数据模型
            from PyQt5.QtGui import QStandardItemModel, QStandardItem
            
            model = QStandardItemModel()
            
            # 设置列标题
            headers = list(df.columns)
            model.setHorizontalHeaderLabels(headers)
            
            # 限制显示行数，防止UI卡顿（超过5000行只显示前5000行）
            max_rows = min(len(df), 5000)
            if len(df) > max_rows:
                logger.warning(f"查询结果过多（{len(df)} 行），只显示前 {max_rows} 行")
            
            # 添加数据行
            for row_idx in range(max_rows):
                row = df.iloc[row_idx]
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
            
            logger.info("查询结果显示完成")
            
        except Exception as e:
            logger.error(f"显示查询结果时出错: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "显示错误", f"显示查询结果时出错：\n{str(e)}")
    
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
        """重置所有表单输入"""
        try:
            logger.info("开始重置表单")
            
            # 1. 清空已选择的科目
            self.clear_selected_subjects()
            
            # 2. 重置时点选择 - 将所有日期编辑框重置为最小日期
            empty_date = QDate(1900, 1, 1)
            for date_edit in self.time_edits:
                date_edit.setDate(empty_date)
            
            # 3. 清空查询输入
            self.stock_code_input.clear()
            self.stock_name_input.clear()
            
            # 4. 重置下拉框选择
            # 市场选择重置为"全部"
            for i in range(self.market_combo.count()):
                if self.market_combo.itemText(i) == "全部":
                    self.market_combo.setCurrentIndex(i)
                    break
            
            # 行业选择重置为"全行业"
            for i in range(self.industry_combo.count()):
                if self.industry_combo.itemText(i) == "全行业":
                    self.industry_combo.setCurrentIndex(i)
                    break
            
            # 5. 清空查询结果表格
            self.result_table.setModel(None)
            self.current_data = pd.DataFrame()
            
            # 6. 重置状态
            self.statusBar().showMessage("表单已重置")
            self.export_button.setEnabled(False)
            
            # 7. 隐藏进度条
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
            
            logger.info("表单重置完成")
            
        except Exception as e:
            logger.error(f"重置表单时出错: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"重置表单时出错：\n{str(e)}")
    
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