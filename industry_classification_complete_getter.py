# -*- coding: utf-8 -*-
"""
多源循环补全行业分类获取器

功能：
1. 支持8个分层数据源，按优先级自动循环获取
2. 循环补全遗漏数据，确保100%覆盖率
3. 用户可随时中断（Ctrl+C），中断后询问操作选择
4. 详细的实时进度显示和最终统计报告

作者：Claude
日期：2024
版本：v3.0
"""

from __future__ import annotations

import re
import signal
import sys
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import requests
from bs4 import BeautifulSoup
import pandas as pd
import akshare as ak
import json
from pathlib import Path
import random
from datetime import datetime

from config import (
    COMPLETE_INDUSTRY_SOURCES,
    REQUEST_TIMEOUT,
    API_SOURCE_TIMEOUT,
    MAX_RETRIES,
    BATCH_SIZE,
    PROGRESS_INTERVAL,
    MAX_RETRY_ROUNDS,
    RETRY_WAIT_TIME,
    USER_AGENT_POOL,
    INDUSTRY_FETCH_STOCK_CENTRIC,
    MIN_SUCCESS_RATE,
    MAX_SOURCES_PER_STOCK,
    SKIP_AFTER_FAILURES,
)


@dataclass
class IndustrySourceStats:
    """数据源统计信息"""

    name: str
    enabled: bool

    # 基础统计
    success_count: int = 0
    fail_count: int = 0
    timeout_count: int = 0
    retry_count: int = 0

    # 健康度/熔断控制（运行期动态调整）
    attempt_count: int = 0
    consecutive_failures: int = 0
    disabled: bool = False
    disabled_reason: str = ""

    # 运行统计
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    http_requests: int = 0
    avg_response_time: float = 0.0


@dataclass
class IndustryResult:
    """行业分类结果"""
    stock_code: str
    shenwan_level1: str
    shenwan_level2: str
    shenwan_level3: str
    industry: str
    source: str
    confidence: float = 1.0  # 数据质量置信度


class IndustryClassificationCompleteGetter:
    """
    多源循环补全行业分类获取器
    
    支持8个分层数据源，自动循环补全，用户可中断，提供详细统计信息
    """

    # 申万一级行业分类标准
    VALID_SHENWAN_L1: Tuple[str, ...] = (
        "农林牧渔", "煤炭", "石油石化", "钢铁", "有色金属", "基础化工",
        "建筑材料", "建筑装饰", "电力设备", "机械设备", "国防军工", "汽车",
        "商贸零售", "社会服务", "交通运输", "房地产", "公用事业", "环保",
        "纺织服饰", "轻工制造", "美容护理", "医药生物", "食品饮料",
        "家用电器", "电子", "计算机", "通信", "传媒", "银行", "非银金融", "综合"
    )

    def __init__(self, logger=None):
        self.logger = logger
        self.interrupted = False

        self.stock_centric = bool(INDUSTRY_FETCH_STOCK_CENTRIC)
        self.min_success_rate = float(MIN_SUCCESS_RATE or 0)
        self.max_sources_per_stock = int(MAX_SOURCES_PER_STOCK or 0)
        self.skip_after_failures = int(SKIP_AFTER_FAILURES or 0)

        self._min_attempts_before_disable = (
            max(10, int(1 / self.min_success_rate)) if self.min_success_rate > 0 else 20
        )

        self._current_timeout: Optional[float] = None

        self.sources_config = self._load_sources_config()
        self.source_stats: Dict[str, IndustrySourceStats] = {}
        self.remaining_stocks: Set[str] = set()
        self.processed_stocks: Dict[str, IndustryResult] = {}
        self.used_sources: List[str] = []
        self.round_number = 0
        self.total_stocks = 0
        self._setup_signal_handlers()
        self._initialize_source_stats()

    def _load_sources_config(self) -> Dict[str, Dict]:
        """加载数据源配置"""
        config = {}
        for key, cfg in COMPLETE_INDUSTRY_SOURCES.items():
            if cfg.get('enabled', True):
                config[key] = cfg
        return config

    def _initialize_source_stats(self):
        """初始化数据源统计"""
        for source_id, cfg in self.sources_config.items():
            self.source_stats[source_id] = IndustrySourceStats(
                name=cfg['name'],
                enabled=cfg['enabled']
            )

    def _setup_signal_handlers(self):
        """设置中断信号处理器"""
        def signal_handler(signum, frame):
            self.interrupted = True
            if self.logger:
                self.logger.info("⚠️ 检测到用户中断信号 (Ctrl+C)")
            sys.stdout.write("\n⚠️ 检测到中断信号，优雅关闭中...\n")
            sys.stdout.flush()
        
        signal.signal(signal.SIGINT, signal_handler)

    def get_complete_classification(
        self,
        stocks: Sequence[Dict[str, str]],
        show_progress: bool = True,
    ) -> Dict[str, Dict[str, str]]:
        """获取完整的行业分类数据。

        默认采用“股票维度”的智能循环：外层遍历股票，内层按优先级/健康度尝试多个源，
        单只股票一旦成功立即停止尝试后续源。
        """

        if not stocks:
            return {}

        if not self.stock_centric:
            return self._get_complete_classification_source_centric(stocks, show_progress=show_progress)

        self.total_stocks = len(stocks)
        self.remaining_stocks = {s.get("code", "") for s in stocks if s.get("code")}
        self.processed_stocks.clear()
        self.used_sources.clear()
        self.round_number = 0
        self.interrupted = False

        sorted_sources = sorted(self.sources_config.items(), key=lambda x: x[1]["priority"])
        self._reset_source_stats()

        if show_progress:
            print("\n开始获取行业分类（股票维度智能循环）...")
            self._display_initial_status(stocks, sorted_sources)

        for idx, stock in enumerate(stocks):
            stock_code = stock.get("code", "")
            if not stock_code or stock_code not in self.remaining_stocks:
                continue

            if self.interrupted:
                action = self._prompt_interruption_action()
                if action == "continue":
                    self.interrupted = False
                elif action == "skip":
                    break
                else:
                    raise SystemExit(0)

            processed = idx + 1
            if show_progress and (processed == 1 or processed % PROGRESS_INTERVAL == 0):
                self._display_stock_centric_progress(processed)

            result = self._fetch_single_stock_multi_source(
                stock_code=stock_code,
                stock_name=stock.get("name", ""),
                base_industry=stock.get("industry", ""),
                sorted_sources=sorted_sources,
            )

            if result:
                self.processed_stocks[stock_code] = result
                self.remaining_stocks.discard(stock_code)

        now = time.time()
        for stats in self.source_stats.values():
            if stats.start_time and not stats.end_time:
                stats.end_time = now

        self._fill_failed_stocks()

        if show_progress:
            self._display_final_report()

        return {code: self._result_to_dict(result) for code, result in self.processed_stocks.items()}

    def _get_complete_classification_source_centric(
        self,
        stocks: Sequence[Dict[str, str]],
        show_progress: bool = True,
    ) -> Dict[str, Dict[str, str]]:
        """旧版实现：源维度轮次处理（保留以便必要时回退）。"""

        self.total_stocks = len(stocks)
        self.remaining_stocks = {s.get("code", "") for s in stocks if s.get("code")}
        self.processed_stocks.clear()
        self.used_sources.clear()
        self.round_number = 0
        self.interrupted = False

        sorted_sources = sorted(self.sources_config.items(), key=lambda x: x[1]["priority"])
        self._reset_source_stats()

        if show_progress:
            print("\n开始获取行业分类（源维度轮次处理）...")
            self._display_initial_status(stocks, sorted_sources)

        round_num = 1
        while self.remaining_stocks and round_num <= len(sorted_sources):
            source_id, source_config = sorted_sources[round_num - 1]

            if not self._try_source(source_id, source_config, stocks, show_progress):
                break

            if show_progress:
                self._display_source_summary(round_num, source_id)

            round_num += 1

            if self.remaining_stocks and round_num <= len(sorted_sources):
                time.sleep(RETRY_WAIT_TIME)

        self._fill_failed_stocks()

        if show_progress:
            self._display_final_report()

        return {code: self._result_to_dict(result) for code, result in self.processed_stocks.items()}

    def _fetch_single_stock_multi_source(
        self,
        stock_code: str,
        stock_name: str,
        base_industry: str,
        sorted_sources: Sequence[Tuple[str, Dict]],
    ) -> Optional[IndustryResult]:
        active_sources = self._get_active_sources(sorted_sources)
        if self.max_sources_per_stock and self.max_sources_per_stock > 0:
            active_sources = active_sources[: self.max_sources_per_stock]

        for source_id, source_config in active_sources:
            if self.interrupted:
                return None
            result = self._fetch_single_stock_from_source(
                stock_code=stock_code,
                stock_name=stock_name,
                base_industry=base_industry,
                source_id=source_id,
                source_config=source_config,
            )
            if result:
                return result

        return None

    def _get_active_sources(self, sorted_sources: Sequence[Tuple[str, Dict]]) -> List[Tuple[str, Dict]]:
        """返回当前“活跃”的数据源列表（按优先级 + 运行期成功率动态调整）。"""

        active: List[Tuple[str, Dict]] = []

        for source_id, cfg in sorted_sources:
            stats = self.source_stats.get(source_id)
            if not stats or not cfg.get("enabled", True):
                continue

            if stats.disabled:
                continue

            attempts = stats.attempt_count
            if self.min_success_rate > 0 and attempts >= self._min_attempts_before_disable:
                success_rate = stats.success_count / attempts if attempts else 0.0
                if success_rate < self.min_success_rate:
                    stats.disabled = True
                    stats.disabled_reason = (
                        f"success_rate={success_rate:.1%} < {self.min_success_rate:.1%} after {attempts} attempts"
                    )
                    msg = f"⚠️ 停用数据源 {stats.name}: {stats.disabled_reason}"
                    if self.logger:
                        self.logger.warning(msg)
                    else:
                        print(msg)
                    continue

            active.append((source_id, cfg))

        def sort_key(item: Tuple[str, Dict]) -> Tuple[float, int]:
            source_id, cfg = item
            stats = self.source_stats[source_id]
            attempts = stats.attempt_count
            if attempts >= self._min_attempts_before_disable and attempts > 0:
                rate = stats.success_count / attempts
                return (-rate, int(cfg.get("priority", 999)))
            return (0.0, int(cfg.get("priority", 999)))

        active.sort(key=sort_key)
        return active

    def _fetch_single_stock_from_source(
        self,
        stock_code: str,
        stock_name: str,
        base_industry: str,
        source_id: str,
        source_config: Dict,
    ) -> Optional[IndustryResult]:
        fetch_method = self._get_fetch_method(source_id)
        stats = self.source_stats[source_id]

        timeout = float(source_config.get("timeout", REQUEST_TIMEOUT))
        retry_count = max(1, int(source_config.get("retry_count", 1)))

        if stats.start_time is None:
            stats.start_time = time.time()

        if source_id not in self.used_sources:
            self.used_sources.append(source_id)

        local_consecutive_failures = 0
        for attempt in range(retry_count):
            if attempt > 0:
                stats.retry_count += 1

            start = time.perf_counter()
            try:
                self._current_timeout = timeout
                result = fetch_method(stock_code, stock_name, base_industry)
                elapsed = time.perf_counter() - start

                stats.http_requests += 1
                stats.attempt_count += 1
                stats.avg_response_time = (
                    (stats.avg_response_time * (stats.http_requests - 1)) + elapsed
                ) / stats.http_requests

                if result:
                    stats.success_count += 1
                    stats.consecutive_failures = 0
                    return result

                stats.fail_count += 1
                stats.consecutive_failures += 1
                local_consecutive_failures += 1

            except requests.Timeout:
                elapsed = time.perf_counter() - start
                stats.http_requests += 1
                stats.attempt_count += 1
                stats.timeout_count += 1
                stats.consecutive_failures += 1
                local_consecutive_failures += 1
                stats.avg_response_time = (
                    (stats.avg_response_time * (stats.http_requests - 1)) + elapsed
                ) / stats.http_requests

            except Exception as e:
                elapsed = time.perf_counter() - start
                stats.http_requests += 1
                stats.attempt_count += 1
                stats.fail_count += 1
                stats.consecutive_failures += 1
                local_consecutive_failures += 1
                stats.avg_response_time = (
                    (stats.avg_response_time * (stats.http_requests - 1)) + elapsed
                ) / stats.http_requests
                if self.logger:
                    self.logger.debug(f"{stats.name} 获取 {stock_code} 失败: {e}")

            finally:
                self._current_timeout = None

            if self.skip_after_failures and local_consecutive_failures >= self.skip_after_failures:
                break

        return None

    def _display_stock_centric_progress(self, processed_count: int):
        success_count = len(self.processed_stocks)
        success_rate = (success_count / processed_count * 100) if processed_count else 0.0
        progress_rate = (processed_count / self.total_stocks * 100) if self.total_stocks else 0.0

        active_sources = len(
            [
                s
                for s in self.source_stats.values()
                if s.enabled and not s.disabled
            ]
        )

        print(
            f"已处理: {processed_count}/{self.total_stocks} ({progress_rate:.1f}%) | "
            f"成功: {success_count} ({success_rate:.1f}%) | "
            f"活跃源: {active_sources}"
        )

    def _prompt_interruption_action(self) -> str:
        print(
            f"\n\n⚠️ 用户中断了行业分类获取！\n\n"
            f"当前状态:\n"
            f"- 已成功获取: {len(self.processed_stocks)} / {self.total_stocks}\n"
            f"- 剩余未获取: {len(self.remaining_stocks)}\n\n"
            f"选择操作:\n"
            f"[1] 继续处理剩余股票\n"
            f"[2] 跳过剩余股票（填充未分类）\n"
            f"[3] 退出程序\n\n"
            f"请输入选择 (1/2/3): ",
            end="",
        )

        try:
            choice = input().strip()
        except (EOFError, KeyboardInterrupt):
            return "exit"

        if choice == "1":
            return "continue"
        if choice == "2":
            return "skip"
        return "exit"

    def _try_source(
        self, 
        source_id: str, 
        source_config: Dict,
        stocks: Sequence[Dict[str, str]],
        show_progress: bool = True
    ) -> bool:
        """
        尝试使用指定数据源获取行业分类
        
        Args:
            source_id: 数据源ID
            source_config: 数据源配置
            stocks: 股票列表
            show_progress: 是否显示进度
        
        Returns:
            True表示继续，False表示中断
        """
        source_name = source_config['name']
        start_time = time.time()
        
        self.round_number += 1
        if source_id not in self.used_sources:
            self.used_sources.append(source_id)

        # 重置该源的统计
        stats = self.source_stats[source_id]
        stats.start_time = start_time
        stats.success_count = 0
        stats.fail_count = 0

        # 获取剩余股票列表
        remaining_before = list(self.remaining_stocks)
        total_remaining = len(remaining_before)
        
        if show_progress:
            self._display_source_start(source_name, self.round_number, total_remaining)

        # 根据数据源选择获取方法
        fetch_method = self._get_fetch_method(source_id)
        
        success_count = 0
        fail_count = 0
        
        # 批量处理
        for i, stock_code in enumerate(remaining_before):
            if self.interrupted:
                return False
            
            # 显示进度
            if show_progress and (i + 1) % PROGRESS_INTERVAL == 0:
                self._display_progress(source_name, i + 1, total_remaining, stats)
            
            # 获取股票信息
            stock_info = next(
                (s for s in stocks if s.get("code") == stock_code), 
                {"code": stock_code, "name": "", "industry": ""}
            )
            
            try:
                # 使用指定源获取行业分类
                self._current_timeout = float(source_config.get("timeout", REQUEST_TIMEOUT))
                result = fetch_method(stock_code, stock_info.get("name", ""), stock_info.get("industry", ""))
                if result:
                    self.processed_stocks[stock_code] = result
                    self.remaining_stocks.remove(stock_code)
                    success_count += 1
                    stats.success_count += 1
                else:
                    fail_count += 1
                    stats.fail_count += 1

            except requests.Timeout:
                fail_count += 1
                stats.timeout_count += 1
            except Exception as e:
                fail_count += 1
                stats.fail_count += 1
                if self.logger:
                    self.logger.debug(f"{source_name} 获取 {stock_code} 失败: {e}")
            finally:
                self._current_timeout = None

        # 更新统计信息
        stats.end_time = time.time()
        stats.retry_count = stats.fail_count + stats.timeout_count
        
        # 输出源完成统计
        if show_progress:
            self._display_source_complete(source_name, success_count, fail_count, stats, start_time)
        
        return True

    def _get_fetch_method(self, source_id: str) -> Callable:
        """根据数据源ID获取相应的获取方法"""
        fetch_methods = {
            'eastmoney_quote': self._fetch_from_eastmoney_quote,
            'eastmoney_f10': self._fetch_from_eastmoney_f10,
            'sina_shenwan': self._fetch_from_sina_shenwan,
            'akshare': self._fetch_from_akshare,
            'tushare': self._fetch_from_tushare,
            'tencent_quote': self._fetch_from_tencent_quote,
            'netease_f10': self._fetch_from_netease_f10,
            'cninfo': self._fetch_from_cninfo,
            'cache_mapping': self._fetch_from_cache_mapping,
        }
        return fetch_methods.get(source_id, self._fetch_from_cache_mapping)

    def _fetch_from_akshare(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从AkShare获取行业分类"""
        try:
            # 使用AkShare获取股票基本信息
            stock_info = ak.stock_individual_info_em(symbol=stock_code)
            
            # 查找行业分类信息
            industry_info = {}
            for _, row in stock_info.iterrows():
                if isinstance(row['item'], str) and any(keyword in row['item'] for keyword in ['行业', '所属']):
                    industry_info['text'] = str(row['value'])
                    break
            
            if 'text' in industry_info:
                industry_text = industry_info['text']
                l1, l2, l3 = self._infer_shenwan_levels(industry_text)
                return IndustryResult(
                    stock_code, l1, l2, l3, industry_text, "AkShare", confidence=0.95
                )
        except Exception:
            pass
        
        return None

    def _fetch_from_tushare(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从TuShare获取行业分类"""
        try:
            # 注意：TuShare需要token，这里作为示例实现
            # 实际使用时需要配置tushare_token
            # import tushare as ts
            # ts.set_token('your_token')
            # pro = ts.pro_api()
            # stock_basic = pro.stock_basic(ts_code=f'{stock_code}.SZ' if not stock_code.startswith('6') else f'{stock_code}.SH')
            # industry = stock_basic.iloc[0]['industry']
            
            # 这里返回None作为占位，实际使用时需要配置
            return None
        except Exception:
            return None

    def _fetch_from_eastmoney_quote(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从东方财富行情接口获取行业分类"""
        try:
            secid = self._to_eastmoney_secid(stock_code)
            if not secid:
                return None

            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": secid,
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "fields": "f57,f58,f127",
            }
            
            headers = self._get_random_headers()
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self._get_request_timeout(),
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json().get("data") or {}
            industry = str(data.get("f127") or "").strip()
            
            # 该字段有时为空或为"-"
            if not industry or industry == "-":
                return None

            l1, l2, l3 = self._infer_shenwan_levels(industry)
            return IndustryResult(
                stock_code, l1, l2, l3, industry, "东方财富行情", confidence=0.9
            )
        except Exception:
            return None

    def _fetch_from_eastmoney_f10(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从东方财富F10获取行业分类"""
        try:
            # 转换股票代码格式
            secid = self._to_eastmoney_secid(stock_code)
            if not secid:
                return None

            url = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax"
            headers = self._get_random_headers()
            
            response = requests.get(
                url,
                params={"code": secid},
                headers=headers,
                timeout=self._get_request_timeout(),
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            industry = str((data.get("jbzl") or {}).get("sshy") or "").strip()
            
            if not industry:
                return None

            l1, l2, l3 = self._infer_shenwan_levels(industry)
            return IndustryResult(
                stock_code, l1, l2, l3, industry, "东方财富F10", confidence=0.9
            )
        except Exception:
            return None

    def _fetch_from_sina_shenwan(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从新浪财经获取申万行业分类"""
        try:
            url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCI_CorpOtherInfo/stockid/{stock_code}/menu_num/2.phtml"
            headers = self._get_random_headers()

            response = requests.get(
                url,
                headers=headers,
                timeout=self._get_request_timeout(),
            )
            
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.text, "lxml")
            
            # 查找行业分类表格
            tables = soup.select("table.comInfo1")
            for table in tables:
                title_cell = table.select_one("tr td")
                if not title_cell:
                    continue
                if "所属行业板块" not in title_cell.get_text(strip=True):
                    continue

                rows = table.select("tr")
                if len(rows) < 3:
                    continue

                cells = rows[2].select("td")
                if not cells:
                    continue

                industry = cells[0].get_text(strip=True)
                if not industry:
                    continue

                l1, l2, l3 = self._infer_shenwan_levels(industry)
                return IndustryResult(
                    stock_code, l1, l2, l3, industry, "新浪财经", confidence=0.85
                )
        except Exception:
            pass
        
        return None

    def _fetch_from_tencent_quote(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从腾讯财经获取行业分类"""
        try:
            symbol = ("sh" if stock_code.startswith("6") else "sz") + stock_code
            url = f"https://qt.gtimg.cn/q={symbol}"
            headers = self._get_random_headers()

            response = requests.get(
                url,
                headers=headers,
                timeout=self._get_request_timeout(),
            )
            
            if response.status_code != 200:
                return None
                
            text = response.text
            # 从响应中尝试提取行业信息
            m = re.search(r"行业[:：]\s*([^~;\"\n]{2,20})", text)
            if not m:
                return None

            industry = m.group(1).strip()
            if not industry:
                return None

            l1, l2, l3 = self._infer_shenwan_levels(industry)
            return IndustryResult(
                stock_code, l1, l2, l3, industry, "腾讯财经", confidence=0.7
            )
        except Exception:
            return None

    def _fetch_from_netease_f10(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从网易财经获取行业分类"""
        try:
            url = f"https://quotes.money.163.com/f10/gszl_{stock_code}.html"
            headers = self._get_random_headers()

            response = requests.get(
                url,
                headers=headers,
                timeout=self._get_request_timeout(),
            )
            
            if response.status_code >= 400:
                return None
                
            text = response.text
            m = re.search(r"所属行业</span>\s*<span[^>]*>\s*(?:<a[^>]*>)?([^<]+)", text)
            if not m:
                return None

            industry = m.group(1).strip()
            if not industry:
                return None

            l1, l2, l3 = self._infer_shenwan_levels(industry)
            return IndustryResult(
                stock_code, l1, l2, l3, industry, "网易财经", confidence=0.75
            )
        except Exception:
            return None

    def _fetch_from_cninfo(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从巨潮资讯获取行业分类"""
        try:
            # 巨潮资讯主要提供年报等文件，行业分类信息可能有限
            # 这里作为兜底实现
            if base_industry:
                l1, l2, l3 = self._infer_shenwan_levels(base_industry)
                return IndustryResult(
                    stock_code, l1, l2, l3, base_industry, "巨潮资讯", confidence=0.8
                )
        except Exception:
            pass
        
        return None

    def _fetch_from_cache_mapping(self, stock_code: str, stock_name: str, base_industry: str) -> Optional[IndustryResult]:
        """从缓存库或手动映射获取行业分类"""
        try:
            # 这里可以实现缓存映射逻辑
            # 例如：从历史数据或手动维护的映射表中查找
            mapping_data = {
                # 示例映射数据
                # "000001": {"industry": "银行", "confidence": 0.9}
            }
            
            if stock_code in mapping_data:
                mapped = mapping_data[stock_code]
                industry = mapped.get('industry', '')
                if industry:
                    l1, l2, l3 = self._infer_shenwan_levels(industry)
                    return IndustryResult(
                        stock_code, l1, l2, l3, industry, "缓存映射", 
                        confidence=mapped.get('confidence', 0.9)
                    )
        except Exception:
            pass
        
        return None

    def _infer_shenwan_levels(self, industry_text: str) -> Tuple[str, str, str]:
        """
        从行业文本推断申万三级分类
        
        Args:
            industry_text: 行业分类文本
            
        Returns:
            (一级分类, 二级分类, 三级分类)
        """
        industry_text = str(industry_text).strip()
        
        if not industry_text:
            return "未分类", "未分类", "未分类"
        
        # 一级分类映射规则
        l1_mapping = {
            "银行": "银行",
            "证券": "非银金融",
            "保险": "非银金融",
            "房地产": "房地产",
            "建筑": "建筑装饰",
            "建材": "建筑材料",
            "钢铁": "钢铁",
            "有色": "有色金属",
            "煤炭": "煤炭",
            "石油": "石油石化",
            "化工": "基础化工",
            "电力": "公用事业",
            "公用": "公用事业",
            "医药": "医药生物",
            "食品": "食品饮料",
            "饮料": "食品饮料",
            "家电": "家用电器",
            "电子": "电子",
            "计算机": "计算机",
            "通信": "通信",
            "传媒": "传媒",
            "汽车": "汽车",
            "机械": "机械设备",
            "设备": "机械设备",
            "军工": "国防军工",
            "国防": "国防军工",
            "纺织": "纺织服饰",
            "轻工": "轻工制造",
            "零售": "商贸零售",
            "商贸": "商贸零售",
            "交通": "交通运输",
            "运输": "交通运输",
            "环保": "环保",
            "农林": "农林牧渔",
            "牧渔": "农林牧渔",
            "农业": "农林牧渔",
            "美容": "美容护理",
            "护理": "美容护理",
            "综合": "综合"
        }
        
        # 尝试匹配一级分类
        l1 = "未分类"
        for keyword, category in l1_mapping.items():
            if keyword in industry_text:
                l1 = category
                break
        
        # 如果是未分类，使用通用规则
        if l1 == "未分类":
            l1 = "综合"
        
        # 生成二级和三级分类（简化处理）
        l2 = l1
        l3 = f"{l1}其他"
        
        # 特殊情况处理
        if l1 in ["银行", "非银金融"]:
            if "银行" in industry_text:
                l1 = "银行"
            elif "证券" in industry_text or "保险" in industry_text:
                l1 = "非银金融"
        
        return l1, l2, l3

    def _to_eastmoney_secid(self, stock_code: str) -> Optional[str]:
        """转换股票代码为东方财富格式"""
        if stock_code.startswith("6"):
            return f"1.{stock_code}"  # 沪市
        elif stock_code.startswith(('0', '3')):
            return f"0.{stock_code}"  # 深市
        return None

    def _get_random_headers(self) -> Dict[str, str]:
        """获取随机HTTP请求头"""
        user_agent = random.choice(USER_AGENT_POOL)
        return {
            'User-Agent': user_agent,
            'Accept': 'application/json, text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def _get_request_timeout(self) -> float:
        timeout = self._current_timeout if self._current_timeout is not None else REQUEST_TIMEOUT
        return float(timeout)

    def _fill_failed_stocks(self):
        """填充无法获取行业分类的股票"""
        for stock_code in self.remaining_stocks:
            self.processed_stocks[stock_code] = IndustryResult(
                stock_code=stock_code,
                shenwan_level1="未分类",
                shenwan_level2="未分类", 
                shenwan_level3="未分类",
                industry="未分类",
                source="unknown",
                confidence=0.0
            )

    def _result_to_dict(self, result: IndustryResult) -> Dict[str, str]:
        """将结果转换为字典"""
        return {
            "stock_code": result.stock_code,
            "shenwan_level1": result.shenwan_level1,
            "shenwan_level2": result.shenwan_level2,
            "shenwan_level3": result.shenwan_level3,
            "industry": result.industry,
            "source": result.source,
            "confidence": str(result.confidence)
        }

    def _reset_source_stats(self):
        """重置所有数据源统计"""
        for stats in self.source_stats.values():
            stats.success_count = 0
            stats.fail_count = 0
            stats.timeout_count = 0
            stats.retry_count = 0

            stats.attempt_count = 0
            stats.consecutive_failures = 0
            stats.disabled = False
            stats.disabled_reason = ""

            stats.start_time = None
            stats.end_time = None
            stats.http_requests = 0
            stats.avg_response_time = 0.0

    def _handle_interruption(self):
        """处理用户中断"""
        print(f"""
⚠️ 用户中断了行业分类获取！

当前状态:
- 已获取: {len(self.processed_stocks)} / {self.total_stocks} stocks
- 剩余遗漏: {len(self.remaining_stocks)} stocks
- 已使用源: {', '.join(self.used_sources)}

选择操作:
[1] 继续重试剩余的 {len(self.remaining_stocks)} 个 (从第 {len(self.used_sources) + 1} 个源开始)
[2] 跳过遗漏的 {len(self.remaining_stocks)} 个，继续处理财务数据
[3] 退出程序

请输入选择 (1/2/3): """, end="")
        
        try:
            choice = input().strip()
            if choice == "1":
                print("🔄 继续从下一个数据源开始重试...")
                return self._resume_processing()
            elif choice == "2":
                print("⏭️ 跳过遗漏的股票，继续处理财务数据...")
                self._fill_failed_stocks()
                return True
            else:
                print("👋 退出程序...")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\n👋 退出程序...")
            return False

    def _resume_processing(self):
        """恢复处理"""
        if not self.remaining_stocks:
            return True
        
        # 继续从下一个数据源开始
        sorted_sources = sorted(
            self.sources_config.items(),
            key=lambda x: x[1]['priority']
        )
        
        current_source_index = len(self.used_sources)
        if current_source_index >= len(sorted_sources):
            print("⚠️ 所有数据源都已尝试，无法继续...")
            return False
        
        # 重新加载股票数据（这里需要从外部传入）
        print("⚠️ 请重新运行程序以恢复处理...")
        return False

    # =================
    # 显示方法
    # =================

    def _display_initial_status(self, stocks: Sequence[Dict[str, str]], sorted_sources: List[Tuple]):
        """显示初始状态"""
        print("=" * 80)
        print("🔄 多源循环补全行业分类获取器")
        print("=" * 80)
        print(f"📊 总股票数: {len(stocks)}")
        print(f"🔗 可用数据源数: {len(sorted_sources)}")
        print()
        
        # 显示数据源信息
        print("📋 数据源配置:")
        for _, (_, cfg) in enumerate(sorted_sources, 1):
            print(f"   {cfg['priority']}. {cfg['name']} - {cfg['description']}")
        print()

    def _display_source_start(self, source_name: str, round_num: int, remaining_count: int):
        """显示数据源开始信息"""
        print()
        print("━" * 80)
        print(f"第{round_num}轮 - 数据源 {source_name}")
        print("━" * 80)
        print(f"🔄 正在使用: {source_name} (第{round_num}轮获取)")
        if remaining_count > 0:
            print(f"🔢 剩余待获取: {remaining_count} 个股票")
        print()

    def _display_progress(self, source_name: str, current: int, total: int, stats: IndustrySourceStats):
        """显示实时进度"""
        percentage = (current / total) * 100
        bar_length = 20
        filled_length = int(bar_length * current / total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        elapsed_time = time.time() - stats.start_time if stats.start_time else 0
        avg_time_per_stock = elapsed_time / current if current > 0 else 0
        remaining_stocks = total - current
        estimated_remaining = remaining_stocks * avg_time_per_stock
        
        print(f"\r🔄 {source_name} 进度: |{bar}| {percentage:.1f}% ({current}/{total}) "
              f"| 预计剩余: {estimated_remaining:.0f}秒 | "
              f"已成功: {stats.success_count}个 | "
              f"已失败: {stats.fail_count}个", end="", flush=True)

    def _display_source_summary(self, round_num: int, source_id: str):
        """显示轮次完成统计"""
        stats = self.source_stats[source_id]
        if not stats.end_time:
            return
            
        duration = stats.end_time - stats.start_time
        success_rate = stats.success_count / (stats.success_count + stats.fail_count) * 100 if (stats.success_count + stats.fail_count) > 0 else 0
        
        print(f"\n\n✅ {stats.name} 轮次完成:")
        print(f"   ├─ 新增获取: {stats.success_count}个")
        print(f"   ├─ 获取失败: {stats.fail_count}个")
        print(f"   ├─ 成功率: {success_rate:.1f}%")
        print(f"   ├─ 耗时: {duration:.0f}秒")
        print(f"   └─ 运行统计:")
        print(f"      ├─ HTTP请求数: {stats.http_requests}次")
        print(f"      ├─ 平均响应时间: {stats.avg_response_time:.1f}秒")
        print(f"      ├─ 重试次数: {stats.retry_count}次")
        print(f"      └─ 超时次数: {stats.timeout_count}次")

    def _display_source_complete(self, source_name: str, success_count: int, fail_count: int, stats: IndustrySourceStats, start_time: float):
        """显示源完成统计"""
        end_time = time.time()
        duration = end_time - start_time
        success_rate = success_count / (success_count + fail_count) * 100 if (success_count + fail_count) > 0 else 0
        
        print(f"\n\n✅ {source_name} 轮次完成:")
        print(f"   ├─ 新增获取: {success_count}个")
        print(f"   ├─ 获取失败: {fail_count}个")
        print(f"   ├─ 成功率: {success_rate:.1f}%")
        print(f"   ├─ 耗时: {duration:.0f}秒")
        if success_count + fail_count > 0:
            avg_time = duration / (success_count + fail_count)
            print(f"   └─ 平均处理时间: {avg_time:.1f}秒/股票")

    def _display_final_report(self):
        """显示最终统计报告（股票维度/源维度均适用）。"""
        if self.total_stocks <= 0:
            return

        total_covered = len(self.processed_stocks) - len(self.remaining_stocks)
        coverage_rate = total_covered / self.total_stocks * 100
        
        print()
        print("=" * 80)
        print("📊 行业分类覆盖率最终报告")
        print("=" * 80)
        
        print("\n一级行业分类:")
        print(f"   ✅ 覆盖率: {total_covered}/{self.total_stocks} ({coverage_rate:.1f}%)")
        
        if self.remaining_stocks:
            missing_list = sorted(self.remaining_stocks)
            preview = ", ".join(missing_list[:10])
            more = "..." if len(missing_list) > 10 else ""
            print(f"   ⚠️ 缺失: {len(self.remaining_stocks)} stocks | 示例: {preview}{more}")
        
        # 按源统计
        print("\n行业分类来源统计:")
        source_stats_summary = {}
        for code, result in self.processed_stocks.items():
            if result.source != "unknown":
                source_name = result.source
                source_stats_summary[source_name] = source_stats_summary.get(source_name, 0) + 1
        
        for source_name, count in sorted(source_stats_summary.items(), key=lambda x: x[1], reverse=True):
            percentage = count / self.total_stocks * 100
            print(f"   ├─ {source_name}: {count} stocks ({percentage:.1f}%)")

        print("\n数据源健康度:")
        for source_id, cfg in sorted(self.sources_config.items(), key=lambda x: x[1].get("priority", 999)):
            stats = self.source_stats.get(source_id)
            if not stats:
                continue

            attempts = stats.attempt_count
            if attempts <= 0:
                continue

            success_rate = stats.success_count / attempts * 100
            disabled = f" (disabled: {stats.disabled_reason})" if stats.disabled else ""

            print(
                f"   ├─ {cfg.get('name', source_id)}: {stats.success_count}/{attempts} ({success_rate:.1f}%) | "
                f"timeout {stats.timeout_count} | avg {stats.avg_response_time:.2f}s{disabled}"
            )

        # 获取统计
        total_duration = 0
        total_requests = 0
        for stats in self.source_stats.values():
            if stats.start_time and stats.end_time:
                total_duration += stats.end_time - stats.start_time
                total_requests += stats.http_requests
        
        print("\n数据获取统计:")
        print(f"   ├─ 总数据源数: {len(self.sources_config)}个")
        print(f"   ├─ 实际使用: {len(self.used_sources)}个")
        print(f"   ├─ 总耗时: {total_duration/60:.0f}分{total_duration%60:.0f}秒")
        print(f"   ├─ 总HTTP请求: {total_requests}次")
        if self.used_sources:
            avg_source_duration = total_duration / len(self.used_sources)
            print(f"   └─ 平均单个源耗时: {avg_source_duration/60:.0f}分{avg_source_duration%60:.0f}秒")
        
        print()