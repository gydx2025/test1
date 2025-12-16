#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轻量测试: FinancialQueryService

该测试避免真实网络请求，通过注入 stub collector 覆盖 query_balance_sheet_indicator。

运行方式：
    python test_financial_query_service.py
"""

import unittest

import pandas as pd

from financial_query_service import FinancialQueryService


class DummyCollector:
    def get_stock_list(self):
        return [
            {"code": "600000", "name": "浦发银行", "market": "上海"},
            {"code": "000001", "name": "平安银行", "market": "深圳"},
            {"code": "430047", "name": "北交所样例", "market": "北交所"},
        ]

    def validate_stock_code(self, code: str) -> bool:
        return isinstance(code, str) and len(code) == 6 and code.isdigit()

    def query_balance_sheet_indicator(self, stock_code: str, indicator: str, report_dates):
        if isinstance(report_dates, str):
            report_dates = [report_dates]
        # 简单返回：value = int(code) % 100 + idx
        base = int(stock_code) % 100
        return {d: float(base + i) for i, d in enumerate(report_dates)}


class FinancialQueryServiceTests(unittest.TestCase):
    def setUp(self):
        self.svc = FinancialQueryService(collector_factory=lambda: DummyCollector())

    def test_reject_more_than_4_dates(self):
        result = self.svc.execute_query(
            {
                "stock_codes": "600000",
                "subject": "投资性房地产",
                "report_dates": [
                    "2024-12-31",
                    "2024-09-30",
                    "2024-06-30",
                    "2024-03-31",
                    "2023-12-31",
                ],
            }
        )
        self.assertFalse(result.success)
        self.assertIn("最多支持", result.error)

    def test_market_filter(self):
        result = self.svc.execute_query(
            {
                "stock_codes": "600000,000001",
                "market": "上海",
                "subject": "INVEST_REALESTATE",
                "report_dates": ["2024-03-31"],
            }
        )
        self.assertTrue(result.success)
        self.assertEqual(result.dataframe.shape[0], 1)
        self.assertEqual(result.dataframe.iloc[0]["stock_code"], "600000")

    def test_subject_label_and_output_columns(self):
        result = self.svc.execute_query(
            {
                "stock_codes": ["600000"],
                "subject": "投资性房地产",
                "report_dates": ["2024-03-31", "2023-12-31"],
                "unit": "万元",
            }
        )
        self.assertTrue(result.success)
        df = result.dataframe
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("2024-03-31/投资性房地产(万元)", df.columns)
        self.assertIn("2023-12-31/投资性房地产(万元)", df.columns)
        self.assertEqual(result.column_order[0:3], ["stock_code", "stock_name", "market"])

    def test_cache_returns_copy(self):
        result = self.svc.execute_query(
            {
                "stock_codes": "600000",
                "subject": "投资性房地产",
                "report_dates": ["2024-03-31"],
            }
        )
        self.assertTrue(result.success)

        _, cached = self.svc.get_last_query()
        self.assertTrue(cached.success)
        cached.dataframe.loc[0, "stock_code"] = "XXXXXX"

        _, cached2 = self.svc.get_last_query()
        self.assertEqual(cached2.dataframe.loc[0, "stock_code"], "600000")


if __name__ == "__main__":
    unittest.main()
