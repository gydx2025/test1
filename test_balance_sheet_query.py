#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tempfile
import unittest

import pandas as pd

from astock_real_estate_collector import AStockRealEstateDataCollector


class DummyCollector(AStockRealEstateDataCollector):
    def __init__(self, cache_dir: str):
        # 仅初始化本次测试所需的最小字段，避免触发网络调用
        self.request_count = 0
        self.failed_request_count = 0
        self.retry_count = 0
        self.industry_cache = {}

        self._balance_sheet_subjects = None
        self._balance_sheet_subjects_cache_dir = cache_dir
        self._balance_sheet_subjects_cache_path = os.path.join(cache_dir, "balance_sheet_subjects.json")
        self._balance_sheet_subjects_ttl_seconds = 3600

    def _fetch_balance_sheet_subjects_from_source(self):  # type: ignore[override]
        return ["TOTAL_ASSETS", "INVEST_REALESTATE"]


class BalanceSheetQueryApiTests(unittest.TestCase):
    def test_get_balance_sheet_subjects_disk_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = DummyCollector(cache_dir=tmp)

            subjects_1 = collector.get_balance_sheet_subjects()
            self.assertEqual(subjects_1, ["TOTAL_ASSETS", "INVEST_REALESTATE"])
            self.assertTrue(os.path.exists(collector._balance_sheet_subjects_cache_path))

            # 强制清空内存缓存，验证能从磁盘缓存读取
            collector._balance_sheet_subjects = None

            def _raise():
                raise AssertionError("should not hit network")

            collector._fetch_balance_sheet_subjects_from_source = _raise  # type: ignore[assignment]
            subjects_2 = collector.get_balance_sheet_subjects()
            self.assertEqual(subjects_2, ["TOTAL_ASSETS", "INVEST_REALESTATE"])

    def test_query_balance_sheet_indicator(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector = DummyCollector(cache_dir=tmp)

            # 覆盖股票列表、行业、以及资产负债表数据源
            collector.get_stock_list = lambda: [  # type: ignore[assignment]
                {"code": "600000", "name": "测试A", "market": "上海"},
                {"code": "000001", "name": "测试B", "market": "深圳"},
            ]
            collector.get_shenwan_industry = lambda code, name: {  # type: ignore[assignment]
                "shenwan_level1": "测试一级",
                "shenwan_level2": "测试二级",
                "shenwan_level3": "测试三级",
                "industry": "测试行业",
                "source": "test",
            }

            def _fake_fetch_balance_sheet(symbol: str) -> pd.DataFrame:
                _ = symbol
                return pd.DataFrame(
                    {
                        "REPORT_DATE": [pd.Timestamp("2023-12-31"), pd.Timestamp("2024-12-31")],
                        "TOTAL_ASSETS": [100.0, 200.0],
                        "INVEST_REALESTATE": [1.0, 2.0],
                    }
                )

            collector._fetch_balance_sheet_by_report_em = _fake_fetch_balance_sheet  # type: ignore[assignment]

            results = collector.query_balance_sheet_indicator(
                periods=["2023-12-31", "2024-12-31"],
                indicator_name="投资性房地产",
                stock_filter="600000",
            )

            self.assertEqual(len(results), 1)
            rec = results[0]
            self.assertEqual(rec["code"], "600000")
            self.assertEqual(rec["indicator"], "INVEST_REALESTATE")
            self.assertEqual(rec["period_values"]["2023-12-31"], 1.0)
            self.assertEqual(rec["period_values"]["2024-12-31"], 2.0)


if __name__ == "__main__":
    unittest.main()
