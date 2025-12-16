#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化的Excel导出系统

提供规范的Excel文件生成、格式化、多表管理等功能
"""

import logging
import os
from typing import List, Dict, Optional
from datetime import datetime
import xlsxwriter

logger = logging.getLogger(__name__)


class ExcelExporter:
    """标准化的Excel导出系统"""
    
    def __init__(self):
        """初始化Excel导出器"""
        self.workbook = None
        self.worksheets = {}
        self.formats = {}
        self._init_formats()
    
    def _init_formats(self):
        """初始化格式"""
        if not self.workbook:
            return
        
        # 标题格式
        self.formats['title'] = self.workbook.add_format({
            'font_size': 16,
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4472C4',
            'font_color': '#FFFFFF'
        })
        
        # 表头格式
        self.formats['header'] = self.workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9E1F2',
            'border': 1,
            'border_color': '#000000'
        })
        
        # 数据格式
        self.formats['data'] = self.workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#CCCCCC'
        })
        
        # 数字格式
        self.formats['number'] = self.workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#CCCCCC',
            'num_format': '#,##0.00'
        })
        
        # 百分比格式
        self.formats['percent'] = self.workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#CCCCCC',
            'num_format': '0.00%'
        })
        
        # 日期格式
        self.formats['date'] = self.workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#CCCCCC',
            'num_format': 'yyyy-mm-dd'
        })
        
        # 缺失数据格式（红色背景）
        self.formats['missing'] = self.workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#CCCCCC',
            'bg_color': '#FFCCCC'
        })
        
        # 统计格式
        self.formats['stat'] = self.workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#FFF2CC',
            'border': 1,
            'border_color': '#000000'
        })
    
    def create_workbook(self, filename: str):
        """
        创建新的工作簿
        
        Args:
            filename: 文件名
        """
        self.workbook = xlsxwriter.Workbook(filename)
        self._init_formats()
        logger.info(f"Excel工作簿已创建: {filename}")
    
    def add_basic_info_sheet(self, stocks: List[Dict]):
        """
        添加基础信息表
        
        包含列：代码、名称、市场、上市日期、数据源
        
        Args:
            stocks: 股票列表
        """
        if not self.workbook:
            logger.error("工作簿未初始化")
            return
        
        sheet = self.workbook.add_worksheet('基础信息')
        self.worksheets['basic_info'] = sheet
        
        # 设置列宽
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 10)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 20)
        
        # 写入标题
        headers = ['股票代码', '公司名称', '市场', '上市日期', '数据源']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, self.formats['header'])
        
        # 冻结首行
        sheet.freeze_panes(1, 0)
        
        # 写入数据
        for row, stock in enumerate(stocks, start=1):
            sheet.write(row, 0, stock.get('code', ''), self.formats['data'])
            sheet.write(row, 1, stock.get('name', ''), self.formats['data'])
            sheet.write(row, 2, stock.get('market', ''), self.formats['data'])
            sheet.write(row, 3, stock.get('list_date', ''), self.formats['date'])
            sheet.write(row, 4, stock.get('data_source', ''), self.formats['data'])
        
        logger.info(f"基础信息表已添加，共{len(stocks)}条记录")
    
    def add_industry_sheet(self, industries: Dict[str, Dict]):
        """
        添加行业分类表
        
        包含列：代码、一级行业、二级行业、三级行业、数据源
        
        Args:
            industries: code -> industry的映射
        """
        if not self.workbook:
            logger.error("工作簿未初始化")
            return
        
        sheet = self.workbook.add_worksheet('行业分类')
        self.worksheets['industry'] = sheet
        
        # 设置列宽
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        
        # 写入标题
        headers = ['股票代码', '一级行业', '二级行业', '三级行业', '数据源']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, self.formats['header'])
        
        # 冻结首行
        sheet.freeze_panes(1, 0)
        
        # 写入数据
        row = 1
        for code in sorted(industries.keys()):
            industry = industries[code]
            if industry:
                sheet.write(row, 0, code, self.formats['data'])
                sheet.write(row, 1, industry.get('l1', ''), self.formats['data'])
                sheet.write(row, 2, industry.get('l2', ''), self.formats['data'])
                sheet.write(row, 3, industry.get('l3', ''), self.formats['data'])
                sheet.write(row, 4, industry.get('source', ''), self.formats['data'])
                row += 1
        
        logger.info(f"行业分类表已添加，共{row-1}条记录")
    
    def add_financial_sheet(self, data: List[Dict]):
        """
        添加财务数据表
        
        包含列：代码、名称、一级行业、2023年资产、2024年资产
        
        Args:
            data: 财务数据列表（包含industry信息）
        """
        if not self.workbook:
            logger.error("工作簿未初始化")
            return
        
        sheet = self.workbook.add_worksheet('财务数据')
        self.worksheets['financial'] = sheet
        
        # 设置列宽
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 18)
        sheet.set_column('E:E', 18)
        
        # 写入标题
        headers = ['股票代码', '公司名称', '一级行业', '2023年末资产', '2024年末资产']
        for col, header in enumerate(headers):
            sheet.write(0, col, header, self.formats['header'])
        
        # 冻结首行
        sheet.freeze_panes(1, 0)
        
        # 写入数据
        for row, record in enumerate(data, start=1):
            sheet.write(row, 0, record.get('code', ''), self.formats['data'])
            sheet.write(row, 1, record.get('name', ''), self.formats['data'])
            
            # 获取一级行业
            industry = record.get('industry', {})
            l1 = industry.get('l1', '') if industry else ''
            sheet.write(row, 2, l1, self.formats['data'])
            
            # 2023年数据
            value_2023 = record.get('non_op_real_estate_2023')
            if value_2023 is not None:
                sheet.write(row, 3, float(value_2023), self.formats['number'])
            else:
                sheet.write(row, 3, '', self.formats['missing'])
            
            # 2024年数据
            value_2024 = record.get('non_op_real_estate_2024')
            if value_2024 is not None:
                sheet.write(row, 4, float(value_2024), self.formats['number'])
            else:
                sheet.write(row, 4, '', self.formats['missing'])
        
        logger.info(f"财务数据表已添加，共{len(data)}条记录")
    
    def add_summary_sheet(self, report: Dict):
        """
        添加汇总统计表
        
        包含：总公司数、代码分布、行业分布、数据完整度等
        
        Args:
            report: 统计报告
        """
        if not self.workbook:
            logger.error("工作簿未初始化")
            return
        
        sheet = self.workbook.add_worksheet('汇总统计')
        self.worksheets['summary'] = sheet
        
        # 设置列宽
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 18)
        
        row = 0
        
        # 标题
        sheet.merge_range(row, 0, row, 1, '数据汇总统计', self.formats['title'])
        row += 2
        
        # 基本统计
        sheet.write(row, 0, '基本统计', self.formats['header'])
        sheet.write(row, 1, '', self.formats['header'])
        row += 1
        
        basic_stats = [
            ('总公司数', report.get('total_stocks', 0)),
            ('行业分类覆盖数', report.get('stocks_with_industry', 0)),
            ('2023年数据覆盖数', report.get('stocks_with_2023_data', 0)),
            ('2024年数据覆盖数', report.get('stocks_with_2024_data', 0)),
        ]
        
        for label, value in basic_stats:
            sheet.write(row, 0, label, self.formats['data'])
            sheet.write(row, 1, value, self.formats['stat'])
            row += 1
        
        row += 1
        
        # 数据完整度
        sheet.write(row, 0, '数据完整度分析', self.formats['header'])
        sheet.write(row, 1, '', self.formats['header'])
        row += 1
        
        total = report.get('total_stocks', 0)
        if total > 0:
            completeness_stats = [
                ('行业分类完整度', report.get('stocks_with_industry', 0) / total),
                ('2023年数据完整度', report.get('stocks_with_2023_data', 0) / total),
                ('2024年数据完整度', report.get('stocks_with_2024_data', 0) / total),
            ]
            
            for label, value in completeness_stats:
                sheet.write(row, 0, label, self.formats['data'])
                sheet.write(row, 1, value, self.formats['percent'])
                row += 1
        
        row += 1
        
        # 数据质量评分
        quality_report = report.get('quality_report')
        if quality_report:
            sheet.write(row, 0, '数据质量评分', self.formats['header'])
            sheet.write(row, 1, '', self.formats['header'])
            row += 1
            
            quality_score = quality_report.get('overall_score', 0)
            grade = quality_report.get('grade', 'N/A')
            
            sheet.write(row, 0, '综合评分', self.formats['data'])
            sheet.write(row, 1, quality_score, self.formats['stat'])
            row += 1
            
            sheet.write(row, 0, '评级', self.formats['data'])
            sheet.write(row, 1, grade, self.formats['stat'])
            row += 1
        
        logger.info("汇总统计表已添加")
    
    def add_metadata_sheet(self, metadata: Dict):
        """
        添加元数据表
        
        包含：采集日期、数据源、版本、说明等
        
        Args:
            metadata: 元数据
        """
        if not self.workbook:
            logger.error("工作簿未初始化")
            return
        
        sheet = self.workbook.add_worksheet('元数据')
        self.worksheets['metadata'] = sheet
        
        # 设置列宽
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 50)
        
        row = 0
        
        # 标题
        sheet.merge_range(row, 0, row, 1, '数据采集元数据', self.formats['title'])
        row += 2
        
        # 写入元数据
        metadata_items = [
            ('采集日期', metadata.get('collection_date', '')),
            ('采集时间', metadata.get('collection_time', '')),
            ('版本号', metadata.get('version', '')),
            ('数据来源', metadata.get('sources', '')),
            ('处理时长', metadata.get('duration', '')),
            ('文件大小', metadata.get('file_size', '')),
            ('说明', metadata.get('notes', '')),
        ]
        
        for label, value in metadata_items:
            sheet.write(row, 0, label, self.formats['header'])
            sheet.write(row, 1, str(value), self.formats['data'])
            row += 1
        
        logger.info("元数据表已添加")
    
    def _add_query_metadata_sheet(self, indicator_name: str, periods: List[str], 
                                   filters: Dict, generation_time: str):
        """
        添加查询条件/元数据表
        
        Args:
            indicator_name: 指标名称
            periods: 时点列表
            filters: 过滤条件
            generation_time: 生成时间
        """
        if not self.workbook:
            logger.error("工作簿未初始化")
            return
        
        sheet = self.workbook.add_worksheet('查询条件')
        self.worksheets['query_metadata'] = sheet
        
        # 设置列宽
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 50)
        
        row = 0
        
        # 标题
        sheet.merge_range(row, 0, row, 1, '查询条件与元数据', self.formats['title'])
        row += 2
        
        # 基本信息
        sheet.write(row, 0, '生成时间', self.formats['header'])
        sheet.write(row, 1, generation_time, self.formats['data'])
        row += 1
        
        sheet.write(row, 0, '指标名称', self.formats['header'])
        sheet.write(row, 1, indicator_name, self.formats['data'])
        row += 1
        
        # 时点信息
        sheet.write(row, 0, '时点数量', self.formats['header'])
        sheet.write(row, 1, len(periods), self.formats['data'])
        row += 1
        
        sheet.write(row, 0, '时点列表', self.formats['header'])
        sheet.write(row, 1, ', '.join(periods) if periods else '无', self.formats['data'])
        row += 2
        
        # 过滤条件
        sheet.write(row, 0, '过滤条件', self.formats['header'])
        sheet.write(row, 1, '', self.formats['header'])
        row += 1
        
        if filters:
            for key, value in filters.items():
                sheet.write(row, 0, key, self.formats['data'])
                sheet.write(row, 1, str(value), self.formats['data'])
                row += 1
        else:
            sheet.write(row, 0, '无过滤条件', self.formats['data'])
            sheet.write(row, 1, '', self.formats['data'])
            row += 1
        
        logger.info("查询条件元数据表已添加")
    
    def export_query_results(self, data: List[Dict], indicator_name: str, 
                            periods: List[str], filters: Dict, filename: str) -> Optional[str]:
        """
        导出动态查询结果到Excel
        
        根据参数动态创建列：基本字段（代码、名称、市场、行业）+ 每个时点的指标列
        
        Args:
            data: 查询结果数据列表，每条记录包含基本字段和各时点的指标值
            indicator_name: 指标名称（如"投资性房地产"）
            periods: 时点列表（如["2023-12-31", "2024-06-30"]，支持0~4个时点）
            filters: 过滤条件字典（如{"市场": "主板", "行业": "房地产"}）
            filename: 输出文件名
            
        Returns:
            生成的文件路径或None（如果失败）
        """
        try:
            # 创建工作簿
            self.create_workbook(filename)
            
            # 添加数据表
            sheet = self.workbook.add_worksheet('查询结果')
            self.worksheets['query_results'] = sheet
            
            # 构建列定义
            base_columns = [
                ('股票代码', 'code', 'data', 12),
                ('公司名称', 'name', 'data', 20),
                ('市场', 'market', 'data', 10),
                ('行业', 'industry', 'data', 20),
            ]
            
            # 动态添加时点列
            period_columns = []
            for period in periods:
                col_header = f"{period}_{indicator_name}"
                col_key = f"value_{period}"
                period_columns.append((col_header, col_key, 'number', 18))
            
            all_columns = base_columns + period_columns
            
            # 设置列宽
            for col_idx, (_, _, _, width) in enumerate(all_columns):
                col_letter = chr(65 + col_idx)  # A, B, C, ...
                sheet.set_column(f'{col_letter}:{col_letter}', width)
            
            # 写入表头
            for col_idx, (header, _, _, _) in enumerate(all_columns):
                sheet.write(0, col_idx, header, self.formats['header'])
            
            # 冻结首行
            sheet.freeze_panes(1, 0)
            
            # 写入数据
            for row_idx, record in enumerate(data, start=1):
                for col_idx, (_, key, fmt_type, _) in enumerate(all_columns):
                    value = record.get(key, '')
                    
                    # 根据格式类型选择格式
                    if fmt_type == 'number':
                        # 数值列处理
                        if value is not None and value != '':
                            try:
                                sheet.write(row_idx, col_idx, float(value), self.formats['number'])
                            except (ValueError, TypeError):
                                sheet.write(row_idx, col_idx, '', self.formats['missing'])
                        else:
                            sheet.write(row_idx, col_idx, '', self.formats['missing'])
                    else:
                        # 文本列处理
                        sheet.write(row_idx, col_idx, value, self.formats['data'])
            
            # 添加查询条件/元数据表
            generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._add_query_metadata_sheet(indicator_name, periods, filters, generation_time)
            
            # 设置工作簿属性
            self.workbook.set_properties({
                'title': f'{indicator_name}查询结果',
                'subject': '动态指标查询导出',
                'author': 'A股数据采集系统',
                'created': datetime.now().isoformat()
            })
            
            # 关闭工作簿
            self.close()
            
            logger.info(f"动态查询结果已导出: {filename}, 共{len(data)}条记录, {len(periods)}个时点")
            return filename
            
        except Exception as e:
            logger.error(f"导出动态查询结果失败: {e}", exc_info=True)
            if self.workbook:
                try:
                    self.workbook.close()
                except:
                    pass
            return None
    
    def format_workbook(self):
        """标准格式化工作簿"""
        if not self.workbook:
            logger.error("工作簿未初始化")
            return
        
        # 设置工作簿属性
        self.workbook.set_properties({
            'title': 'A股非经营性房地产资产数据',
            'subject': '上市公司房地产资产数据',
            'author': 'A股数据采集系统',
            'created': datetime.now().isoformat()
        })
        
        logger.info("工作簿格式化完成")
    
    def close(self):
        """关闭工作簿"""
        if self.workbook:
            self.workbook.close()
            logger.info("Excel文件已生成")


class ExcelReportGenerator:
    """Excel报告生成器"""
    
    @staticmethod
    def generate_complete_report(
        stocks: List[Dict],
        industries: Dict[str, Dict],
        financial_data: List[Dict],
        report: Dict,
        metadata: Dict,
        filename: str
    ) -> Optional[str]:
        """
        生成完整的Excel报告
        
        Args:
            stocks: 股票基础信息
            industries: 行业分类
            financial_data: 财务数据
            report: 统计报告
            metadata: 元数据
            filename: 输出文件名
            
        Returns:
            生成的文件路径或None
        """
        try:
            exporter = ExcelExporter()
            exporter.create_workbook(filename)
            
            # 添加各个表
            exporter.add_basic_info_sheet(stocks)
            exporter.add_industry_sheet(industries)
            exporter.add_financial_sheet(financial_data)
            exporter.add_summary_sheet(report)
            exporter.add_metadata_sheet(metadata)
            
            # 格式化
            exporter.format_workbook()
            
            # 关闭
            exporter.close()
            
            logger.info(f"Excel报告已生成: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"生成Excel报告失败: {e}")
            return None
    
    @staticmethod
    def export_dynamic_query_results(
        data: List[Dict],
        indicator_name: str,
        periods: List[str],
        filters: Optional[Dict] = None,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        导出动态查询结果（服务层API）
        
        这是一个简化的API，供服务层调用，用于导出UI查询结果
        
        Args:
            data: 查询结果数据列表，每条记录应包含：
                  - code: 股票代码
                  - name: 公司名称
                  - market: 市场
                  - industry: 行业
                  - value_{period}: 各时点的指标值（如value_2023-12-31）
            indicator_name: 指标名称（如"投资性房地产"、"固定资产"等）
            periods: 时点列表（如["2023-12-31", "2024-06-30"]），支持0~4个时点
            filters: 过滤条件字典（如{"市场": "主板", "行业": "房地产"}），可选
            filename: 输出文件名，如果不提供则自动生成
            
        Returns:
            生成的文件路径或None（如果失败）
            
        Example:
            >>> data = [
            ...     {
            ...         'code': '000001',
            ...         'name': '平安银行',
            ...         'market': '深交所主板',
            ...         'industry': '银行',
            ...         'value_2023-12-31': 1234567.89,
            ...         'value_2024-06-30': 1345678.90
            ...     }
            ... ]
            >>> result = ExcelReportGenerator.export_dynamic_query_results(
            ...     data=data,
            ...     indicator_name='投资性房地产',
            ...     periods=['2023-12-31', '2024-06-30'],
            ...     filters={'市场': '主板'}
            ... )
        """
        try:
            # 输入验证
            if not data:
                logger.warning("数据为空，无法导出")
                return None
            
            if not indicator_name:
                logger.error("指标名称不能为空")
                return None
            
            if not isinstance(periods, list):
                logger.error("时点参数必须是列表类型")
                return None
            
            if len(periods) > 4:
                logger.warning(f"时点数量({len(periods)})超过建议值(4)，将全部导出")
            
            # 生成默认文件名
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_indicator_name = indicator_name.replace('/', '_').replace('\\', '_')
                filename = f"query_export_{safe_indicator_name}_{timestamp}.xlsx"
            
            # 确保文件名以.xlsx结尾
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            
            # 处理过滤条件
            if filters is None:
                filters = {}
            
            # 创建导出器并导出
            exporter = ExcelExporter()
            result = exporter.export_query_results(
                data=data,
                indicator_name=indicator_name,
                periods=periods,
                filters=filters,
                filename=filename
            )
            
            if result:
                # 验证文件是否生成
                if os.path.exists(result):
                    file_size = os.path.getsize(result)
                    logger.info(f"动态查询结果导出成功: {result} ({file_size} bytes)")
                    return result
                else:
                    logger.error(f"文件生成失败，路径不存在: {result}")
                    return None
            else:
                logger.error("导出失败，未返回文件路径")
                return None
            
        except Exception as e:
            logger.error(f"导出动态查询结果时发生异常: {e}", exc_info=True)
            return None
