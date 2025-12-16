#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""financial_query_service

该模块提供一个面向 PyQt 前端的查询服务层（Facade），让 UI 可以：
- 懒加载初始化 AStockRealEstateDataCollector
- 将用户输入（股票/市场/科目/时点）转换为可执行的查询参数
- 统一输出 pandas.DataFrame，并携带 UI/Excel 导出所需的列顺序与列头
- 缓存最近一次查询结果，供“导出 Excel”按钮复用

示例（供后续 UI 集成参考）：

    from financial_query_service import FinancialQueryService

    svc = FinancialQueryService()
    subjects = svc.load_subject_options()  # 下拉选项

    result = svc.execute_query({
        "stock_codes": "600519, 000001",
        "market": "全部",
        "subject": "投资性房地产",
        "report_dates": ["2024-03-31", "2023-12-31"],
        "unit": "万元",
    })

    if result.success:
        df = result.dataframe
        # UI 侧可使用 result.column_order / result.column_headers 控制展示与导出
    else:
        print(result.error)

注：该服务层不做 PyQt 依赖，便于后续在不同前端/脚本中复用。
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd


SubjectOption = Dict[str, str]


DEFAULT_SUBJECT_OPTIONS: List[SubjectOption] = [
    {"key": "INVEST_REALESTATE", "label": "投资性房地产", "unit": "万元"},
    {"key": "FIXED_ASSET", "label": "固定资产", "unit": "万元"},
    {"key": "CIP", "label": "在建工程", "unit": "万元"},
    {"key": "USERIGHT_ASSET", "label": "使用权资产", "unit": "万元"},
    {"key": "INTANGIBLE_ASSET", "label": "无形资产", "unit": "万元"},
    {"key": "TOTAL_ASSETS", "label": "资产总计", "unit": "万元"},
    {"key": "TOTAL_LIABILITIES", "label": "负债合计", "unit": "万元"},
    {"key": "TOTAL_OWNER_EQUITY", "label": "所有者权益合计", "unit": "万元"},
]


@dataclass(frozen=True)
class QueryResult:
    success: bool
    dataframe: Optional[pd.DataFrame] = None
    data: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]] = None
    column_order: Optional[List[str]] = None
    column_headers: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class FinancialQueryService:
    """PyQt/UI 查询服务层。

    Args:
        collector_factory: 用于创建 AStockRealEstateDataCollector 的工厂函数；
            测试时可注入 stub，避免网络请求。
    """

    def __init__(
        self,
        collector_factory: Optional[Callable[[], Any]] = None,
        subject_options: Optional[List[SubjectOption]] = None,
    ):
        self._collector_factory = collector_factory
        self._collector = None

        self._subject_options = subject_options or DEFAULT_SUBJECT_OPTIONS
        self._subject_by_key = {o["key"].upper(): o for o in self._subject_options}
        self._subject_by_label = {o["label"]: o for o in self._subject_options}

        self._lock = threading.RLock()
        self._last_query_params: Optional[Dict[str, Any]] = None
        self._last_query_result: Optional[QueryResult] = None

    @property
    def collector(self) -> Any:
        if self._collector is None:
            with self._lock:
                if self._collector is None:
                    if self._collector_factory is not None:
                        self._collector = self._collector_factory()
                    else:
                        from astock_real_estate_collector import AStockRealEstateDataCollector

                        self._collector = AStockRealEstateDataCollector()
        return self._collector

    def load_subject_options(self) -> List[SubjectOption]:
        """返回用于下拉框的科目/指标选项。"""
        return [dict(o) for o in self._subject_options]

    def get_last_query(self) -> Tuple[Optional[Dict[str, Any]], Optional[QueryResult]]:
        """获取最近一次查询的参数与结果（深拷贝 DataFrame，避免 UI 侧误改）。"""
        with self._lock:
            params = dict(self._last_query_params) if self._last_query_params else None
            if not self._last_query_result or not self._last_query_result.success:
                return params, self._last_query_result

            df = self._last_query_result.dataframe
            df_copy = df.copy(deep=True) if df is not None else None
            result_copy = QueryResult(
                success=True,
                dataframe=df_copy,
                data=df_copy,
                column_order=list(self._last_query_result.column_order or []),
                column_headers=dict(self._last_query_result.column_headers or {}),
                error=None,
                meta=dict(self._last_query_result.meta or {}),
            )
            return params, result_copy

    def execute_query(self, params: Dict[str, Any]) -> QueryResult:
        """执行一次查询。

        params 推荐字段（允许存在冗余，服务层只读取需要的）：
            - stock_codes: str | list[str]   # 逗号/空格/换行分隔均可
            - market: str                    # 全部/上海/深圳/北交所
            - subject: str                   # 科目名称(中文) 或 key
            - report_dates: list[str] | str  # 最多四个时点
            - unit: str                      # 元/万元
            - return_format: str             # dataframe/list

        Returns:
            QueryResult: success=False 时 error 为友好提示文本。
        """

        try:
            normalized = self._normalize_params(params)
        except ValueError as e:
            return QueryResult(success=False, error=str(e))

        stock_items = normalized["stocks"]
        indicator_key = normalized["indicator_key"]
        indicator_label = normalized["indicator_label"]
        report_dates = normalized["report_dates"]
        unit = normalized["unit"]
        unit_factor = normalized["unit_factor"]

        # 构建列定义
        value_columns: List[str] = []
        column_headers: Dict[str, str] = {
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "market": "市场",
        }
        for d in report_dates:
            header = f"{d}/{indicator_label}({unit})"
            value_columns.append(header)
            column_headers[header] = header

        rows: List[Dict[str, Any]] = []
        errors: List[str] = []

        for stock in stock_items:
            code = stock["code"]
            name = stock.get("name", "")
            market = stock.get("market", self._infer_market(code))

            row: Dict[str, Any] = {
                "stock_code": code,
                "stock_name": name,
                "market": market,
            }

            try:
                values_by_date = self.collector.query_balance_sheet_indicator(
                    stock_code=code,
                    indicator=indicator_key,
                    report_dates=report_dates,
                )
            except Exception as e:  # collector/network error
                errors.append(f"{code}: {e}")
                values_by_date = {d: None for d in report_dates}

            for d in report_dates:
                header = f"{d}/{indicator_label}({unit})"
                raw_value = values_by_date.get(d)
                value = self._to_float(raw_value)
                if value is not None:
                    value = value / unit_factor
                row[header] = value

            rows.append(row)

        df = pd.DataFrame(rows)
        column_order = ["stock_code", "stock_name", "market"] + value_columns
        df = df.reindex(columns=column_order)

        result = QueryResult(
            success=True,
            dataframe=df,
            data=df,
            column_order=column_order,
            column_headers=column_headers,
            error=None,
            meta={
                "indicator_key": indicator_key,
                "indicator_label": indicator_label,
                "report_dates": list(report_dates),
                "unit": unit,
                "warnings": errors,
            },
        )

        with self._lock:
            self._last_query_params = dict(params)
            self._last_query_result = result

        return self._convert_result_format(result, normalized["return_format"])

    def _convert_result_format(self, result: QueryResult, return_format: str) -> QueryResult:
        if not result.success:
            return result

        if return_format == "dataframe":
            return result

        if return_format == "list":
            assert result.dataframe is not None
            records = result.dataframe.to_dict(orient="records")
            return QueryResult(
                success=True,
                dataframe=result.dataframe,
                data=records,
                column_order=list(result.column_order or []),
                column_headers=dict(result.column_headers or {}),
                error=None,
                meta=dict(result.meta or {}),
            )

        return QueryResult(success=False, error=f"不支持的 return_format: {return_format}")

    def _normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        subject_input = (params.get("subject") or params.get("indicator") or "").strip()
        if not subject_input:
            raise ValueError("请选择要查询的科目/指标")

        subject_opt = self._resolve_subject(subject_input)
        indicator_key = subject_opt["key"].upper()
        indicator_label = subject_opt["label"]

        report_dates = self._normalize_report_dates(params.get("report_dates") or params.get("dates"))
        if not report_dates:
            raise ValueError("请至少选择一个报表时点")
        if len(report_dates) > 4:
            raise ValueError("最多支持 4 个报表时点")

        unit = (params.get("unit") or subject_opt.get("unit") or "万元").strip()
        if unit not in {"元", "万元"}:
            raise ValueError("unit 仅支持 '元' 或 '万元'")
        unit_factor = 1 if unit == "元" else 10000

        market = (params.get("market") or "全部").strip()
        if market not in {"全部", "上海", "深圳", "北交所"}:
            raise ValueError("market 仅支持: 全部/上海/深圳/北交所")

        stock_codes = self._parse_stock_codes(params.get("stock_codes") or params.get("stocks"))
        if not stock_codes:
            raise ValueError("请输入至少一个股票代码")

        # 去重 + 市场过滤
        unique_codes: List[str] = []
        seen = set()
        for code in stock_codes:
            if code in seen:
                continue
            seen.add(code)
            inferred_market = self._infer_market(code)
            if market != "全部" and inferred_market != market:
                continue
            unique_codes.append(code)

        if not unique_codes:
            raise ValueError("市场过滤后无符合条件的股票代码")

        enrich_stock_info = bool(params.get("enrich_stock_info", False))
        stocks = self._build_stock_items(unique_codes, enrich_stock_info=enrich_stock_info)

        return_format = (params.get("return_format") or "dataframe").strip().lower()

        return {
            "indicator_key": indicator_key,
            "indicator_label": indicator_label,
            "report_dates": report_dates,
            "unit": unit,
            "unit_factor": unit_factor,
            "market": market,
            "stocks": stocks,
            "return_format": return_format,
        }

    def _build_stock_items(
        self, stock_codes: Sequence[str], enrich_stock_info: bool = False
    ) -> List[Dict[str, str]]:
        # 默认不主动拉取全量股票列表（可能较慢）。
        # UI 若希望补齐股票名称，可在 execute_query 中传入 enrich_stock_info=True。
        if not enrich_stock_info:
            return [{"code": c, "name": "", "market": self._infer_market(c)} for c in stock_codes]

        code_to_info: Dict[str, Dict[str, str]] = {}
        try:
            stock_list = self.collector.get_stock_list()
            for s in stock_list:
                c = str(s.get("code") or "").strip()
                if c:
                    code_to_info[c] = {
                        "code": c,
                        "name": str(s.get("name") or "").strip(),
                        "market": str(s.get("market") or self._infer_market(c)).strip(),
                    }
        except Exception:
            code_to_info = {}

        items: List[Dict[str, str]] = []
        for c in stock_codes:
            info = code_to_info.get(c)
            items.append(info or {"code": c, "name": "", "market": self._infer_market(c)})

        return items

    def _resolve_subject(self, subject: str) -> SubjectOption:
        key = subject.upper()
        if key in self._subject_by_key:
            return self._subject_by_key[key]
        if subject in self._subject_by_label:
            return self._subject_by_label[subject]

        raise ValueError(f"未知科目/指标: {subject}")

    @staticmethod
    def _parse_stock_codes(value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, (list, tuple, set)):
            tokens = [str(v) for v in value]
        else:
            tokens = re.split(r"[\s,;，；]+", str(value))

        cleaned: List[str] = []
        for t in tokens:
            t = t.strip()
            if not t:
                continue

            # 常见输入清洗：sh600000/sz000001 -> 600000
            t = re.sub(r"^(sh|sz|bj)", "", t, flags=re.IGNORECASE)
            if re.fullmatch(r"\d{6}", t):
                cleaned.append(t)

        return cleaned

    @staticmethod
    def _normalize_report_dates(value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            parts = re.split(r"[\s,;，；]+", value)
        else:
            parts = list(value)

        normalized: List[str] = []
        seen = set()
        for p in parts:
            d = FinancialQueryService._normalize_report_date(str(p))
            if d and d not in seen:
                seen.add(d)
                normalized.append(d)

        return normalized

    @staticmethod
    def _normalize_report_date(value: str) -> Optional[str]:
        v = value.strip()
        if not v:
            return None

        # 支持 20240331
        if re.fullmatch(r"\d{8}", v):
            try:
                dt = datetime.strptime(v, "%Y%m%d")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return None

        v = v.replace("/", "-")
        for fmt in ("%Y-%m-%d", "%Y-%m"):
            try:
                dt = datetime.strptime(v, fmt)
                if fmt == "%Y-%m":
                    # 默认月底
                    dt = datetime(dt.year, dt.month, 1)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # 支持 2024-03-31 00:00:00
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", v)
        if m:
            return m.group(1)

        return None

    @staticmethod
    def _infer_market(stock_code: str) -> str:
        if stock_code.startswith("6"):
            return "上海"
        if stock_code.startswith(("0", "3")):
            return "深圳"
        if stock_code.startswith(("4", "8")):
            return "北交所"
        return "未知"

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)

        s = str(value).strip()
        if not s or s.lower() in {"nan", "none"}:
            return None

        # 去掉千分位
        s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
