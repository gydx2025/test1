#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5A股非经营性房地产资产查询界面
"""

import sys
import os
import logging
from typing import List, Dict
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# PyQt5导入
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QGridLayout, QLabel, QComboBox, 
                            QLineEdit, QPushButton, QTableView, QProgressBar,
                            QMessageBox, QFileDialog, QDateEdit, QGroupBox,
                            QFormLayout, QHeaderView, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QIcon, QStandardItemModel, QStandardItem

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
            
            # 处理时点
            time_points = []
            for i in range(4):
                date_value = self.query_params.get(f'time_point_{i}')
                if date_value and str(date_value).strip():
                    try:
                        # 提取年份
                        if isinstance(date_value, QDate):
                            time_points.append(str(date_value.year()))
                        else:
                            # 尝试解析字符串格式的日期
                            if '-' in str(date_value):
                                time_points.append(str(date_value).split('-')[0])
                            elif '/' in str(date_value):
                                time_points.append(str(date_value).split('/')[0])
                            else:
                                time_points.append(str(date_value))
                    except:
                        pass
            
            self.progress.emit(30)
            
            # 执行查询
            df = self.query_service.query_data(
                stock_codes=stock_codes,
                stock_names=stock_names,
                market=market,
                time_points=time_points,
                subject_code=subject_code
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
        logger.info("开始初始化主界面...")
        
        try:
            logger.info("正在初始化数据查询服务...")
            self.query_service = DataQueryService()
            logger.info("数据查询服务初始化完成")
            
            self.query_worker = None
            self.current_data = pd.DataFrame()
            
            logger.info("正在初始化UI...")
            self.init_ui()
            logger.info("UI初始化完成")
            
            logger.info("正在设置信号连接...")
            self.setup_connections()
            logger.info("信号连接完成")
            
            logger.info("主界面初始化成功")
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}", exc_info=True)
            raise
        
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
        
        # 第一行：科目选择和时点选择
        row1_layout = QHBoxLayout()
        
        # 科目选择
        subject_layout = QVBoxLayout()
        subject_layout.addWidget(QLabel("财务指标选择:"))
        
        # 指标下拉框
        self.subject_combo = QComboBox()
        self.subject_combo.addItem("-- 选择财务指标 --", None)
        for subject in self.query_service.available_subjects:
            self.subject_combo.addItem(subject['name'], subject['code'])
        self.subject_combo.currentIndexChanged.connect(self.on_subject_changed)
        subject_layout.addWidget(self.subject_combo)
        
        # 手动输入框
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("或手动输入科目名称...")
        subject_layout.addWidget(self.subject_input)
        
        row1_layout.addLayout(subject_layout)
        row1_layout.addStretch()
        
        # 时点选择
        time_layout = QVBoxLayout()
        time_layout.addWidget(QLabel("时点选择 (最多4个):"))
        
        time_points_layout = QHBoxLayout()
        self.time_edits = []
        for i in range(4):
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate.currentDate())
            date_edit.setSpecialValueText("留空")
            date_edit.clear()  # 设为空
            self.time_edits.append(date_edit)
            time_points_layout.addWidget(date_edit)
        
        time_layout.addLayout(time_points_layout)
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
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)
        
        layout.addLayout(button_layout)
        
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
        # 如果选择了下拉框中的项目，清空手动输入框
        if index > 0:
            self.subject_input.clear()
    
    def validate_input(self) -> bool:
        """验证输入参数"""
        # 检查时点数量
        selected_dates = []
        for date_edit in self.time_edits:
            if not date_edit.isNull():
                selected_dates.append(date_edit.date())
        
        if len(selected_dates) > 4:
            QMessageBox.warning(self, "警告", "最多只能选择4个时点")
            return False
        
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
        
        # 收集查询参数
        query_params = {
            'stock_codes': self.stock_code_input.text(),
            'stock_names': self.stock_name_input.text(),
            'market': self.market_combo.currentText(),
            'subject_code': self.subject_combo.currentData()
        }
        
        # 添加时点参数
        for i, date_edit in enumerate(self.time_edits):
            query_params[f'time_point_{i}'] = date_edit.date() if not date_edit.isNull() else None
        
        # 开始查询
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
        self.current_data = df
        
        # 更新界面
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        
        # 显示结果
        self.display_results(df)
        
        # 更新状态
        if df.empty:
            self.statusBar().showMessage("查询完成：无数据")
            QMessageBox.information(self, "提示", "未找到符合条件的数据")
        else:
            self.statusBar().showMessage(f"查询完成：共 {len(df)} 条记录")
            self.export_button.setEnabled(True)
    
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
        self.time_edits[0].setEnabled(enabled)
        self.time_edits[1].setEnabled(enabled)
        self.time_edits[2].setEnabled(enabled)
        self.time_edits[3].setEnabled(enabled)
        self.stock_code_input.setEnabled(enabled)
        self.stock_name_input.setEnabled(enabled)
        self.market_combo.setEnabled(enabled)
        
        if enabled:
            self.export_button.setEnabled(not self.current_data.empty)
    
    def display_results(self, df: pd.DataFrame):
        """显示查询结果"""
        if df.empty:
            # 清空表格
            self.result_table.setModel(None)
            return
        
        # 创建数据模型
        model = QStandardItemModel()
        
        # 设置列标题
        headers = list(df.columns)
        model.setHorizontalHeaderLabels(headers)
        
        # 为了避免内存问题，限制显示行数（显示前5000行）
        display_limit = 5000
        display_df = df.head(display_limit)
        
        # 添加数据行
        for row_idx, row in display_df.iterrows():
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
        
        # 如果有超过限制的数据，更新状态栏
        if len(df) > display_limit:
            self.statusBar().showMessage(f"显示前 {display_limit} 行，共 {len(df)} 条记录")
    
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
        # 重置控件值
        self.subject_combo.setCurrentIndex(0)
        self.subject_input.clear()
        
        for date_edit in self.time_edits:
            date_edit.clear()
        
        self.stock_code_input.clear()
        self.stock_name_input.clear()
        self.market_combo.setCurrentIndex(0)
        
        # 清空结果
        self.current_data = pd.DataFrame()
        self.result_table.setModel(None)
        self.export_button.setEnabled(False)
        
        # 重置状态
        self.statusBar().showMessage("已重置")
    
    def closeEvent(self, event):
        """关闭事件"""
        # 如果有正在运行的查询线程，先停止
        if self.query_worker and self.query_worker.isRunning():
            self.query_worker.terminate()
            self.query_worker.wait()
        
        # 关闭数据库连接
        if self.query_service:
            self.query_service.close()
        
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