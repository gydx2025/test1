# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import requests
from bs4 import BeautifulSoup


MakeRequestFunc = Callable[[str, Optional[dict], str, Optional[str]], Optional[requests.Response]]


@dataclass(frozen=True)
class IndustryResult:
    shenwan_level1: str
    shenwan_level2: str
    shenwan_level3: str
    industry: str
    source: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "shenwan_level1": self.shenwan_level1,
            "shenwan_level2": self.shenwan_level2,
            "shenwan_level3": self.shenwan_level3,
            "industry": self.industry,
            "source": self.source,
        }


class IndustryClassificationFetcher:
    """多数据源行业分类获取器（以申万分类字段输出，必要时做推断补全）。

    说明：
    - 该获取器会优先返回“可验证”的行业分类（至少一级行业非空）。
    - 仅缓存成功结果（避免把空值/未分类写入持久缓存导致后续无法补全）。
    """

    VALID_SHENWAN_L1: Tuple[str, ...] = (
        "农林牧渔",
        "煤炭",
        "石油石化",
        "钢铁",
        "有色金属",
        "基础化工",
        "建筑材料",
        "建筑装饰",
        "电力设备",
        "机械设备",
        "国防军工",
        "汽车",
        "商贸零售",
        "社会服务",
        "交通运输",
        "房地产",
        "公用事业",
        "环保",
        "纺织服饰",
        "轻工制造",
        "美容护理",
        "医药生物",
        "食品饮料",
        "家用电器",
        "电子",
        "计算机",
        "通信",
        "传媒",
        "银行",
        "非银金融",
        "综合",
    )

    def __init__(
        self,
        make_request: MakeRequestFunc,
        cache: Dict[str, Dict[str, str]],
        sources_config: Optional[Dict[str, Dict]] = None,
        logger=None,
    ):
        self._make_request = make_request
        self.cache = cache
        self.failed: Dict[str, str] = {}
        self.sources_config = sources_config or {}
        self.logger = logger

        self._enabled_sources = self._build_sources_in_priority_order()

    def purge_invalid_cache_entries(self) -> int:
        invalid_keys: List[str] = []
        for code, info in list(self.cache.items()):
            if not self.is_cache_entry_valid(info):
                invalid_keys.append(code)
        for code in invalid_keys:
            self.cache.pop(code, None)
        if invalid_keys and self.logger:
            self.logger.info(f"🧹 已清理无效行业缓存: {len(invalid_keys)} 条")
        return len(invalid_keys)

    @classmethod
    def is_cache_entry_valid(cls, info: object) -> bool:
        if not isinstance(info, dict):
            return False
        l1 = str(info.get("shenwan_level1", "") or "").strip()
        l2 = str(info.get("shenwan_level2", "") or "").strip()
        l3 = str(info.get("shenwan_level3", "") or "").strip()
        source = str(info.get("source", "") or "").strip()

        if not source or source in {"unknown", "error"}:
            return False
        if not l1 or l1 in {"未分类", "错误"}:
            return False
        if l1 not in cls.VALID_SHENWAN_L1:
            return False
        return bool(l2 and l3)

    def get_industry(
        self,
        stock_code: str,
        stock_name: str = "",
        base_industry: str = "",
    ) -> Dict[str, str]:
        if stock_code in self.cache and self.is_cache_entry_valid(self.cache[stock_code]):
            return self.cache[stock_code]

        if stock_code in self.failed:
            return self._fallback_result(source="unknown").as_dict()

        for source_name, get_func in self._enabled_sources:
            try:
                result = get_func(stock_code, stock_name, base_industry)
                if result and self.validate_industry_data(result.as_dict()):
                    self.cache[stock_code] = result.as_dict()
                    return result.as_dict()
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"行业数据源{source_name}获取异常: {e}")
                continue

        self.failed[stock_code] = "all_sources_failed"
        return self._fallback_result(source="unknown").as_dict()

    def batch_get_industries(self, stocks: Sequence[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
        """批量获取行业分类并自动补全。

        参数 stocks 的元素形如：{"code": "000001", "name": "平安银行", "industry": ""}
        """

        results: Dict[str, Dict[str, str]] = {}
        remaining: Set[str] = {s.get("code", "") for s in stocks if s.get("code")}

        for code in list(remaining):
            cached = self.cache.get(code)
            if cached and self.is_cache_entry_valid(cached):
                results[code] = cached
                remaining.remove(code)

        if not remaining:
            return results

        # 第一轮：如果启用，使用东方财富“行业板块-成分股”批量映射（高覆盖，低请求数）
        board_cfg = self.sources_config.get("eastmoney_industry_board", {})
        min_batch_size = int(board_cfg.get("min_batch_size", 300))
        use_board_mapping = bool(board_cfg.get("enabled", True)) and len(remaining) >= min_batch_size
        if use_board_mapping:
            before = len(remaining)
            mapped = self._batch_from_eastmoney_industry_board(remaining)
            results.update(mapped)
            remaining -= set(mapped.keys())
            if self.logger:
                self.logger.info(
                    f"✅ eastmoney_industry_board 批量映射完成: 本轮成功 {before - len(remaining)} / {before}，剩余 {len(remaining)}"
                )
        elif self.logger and board_cfg.get("enabled", True):
            self.logger.info(
                f"⏭️ 跳过 eastmoney_industry_board 批量映射（待补全股票数 {len(remaining)} < min_batch_size {min_batch_size}）"
            )

        # 后续轮：逐个数据源补全
        for source_name, get_func in self._enabled_sources:
            if not remaining:
                break

            if source_name == "eastmoney_industry_board":
                continue

            before = len(remaining)
            for s in stocks:
                code = s.get("code", "")
                if not code or code not in remaining:
                    continue

                name = s.get("name", "")
                base_industry = s.get("industry", "")

                try:
                    res = get_func(code, name, base_industry)
                    if res and self.validate_industry_data(res.as_dict()):
                        results[code] = res.as_dict()
                        self.cache[code] = res.as_dict()
                        remaining.remove(code)
                except Exception:
                    continue

            if self.logger:
                self.logger.info(
                    f"源 {source_name} 获取完毕，成功 {before - len(remaining)} / {before}，剩余 {len(remaining)}"
                )

        for code in remaining:
            results[code] = self._fallback_result(source="unknown").as_dict()

        return results

    def validate_industry_data(self, data: Dict[str, str]) -> bool:
        required = ["shenwan_level1", "shenwan_level2", "shenwan_level3", "industry", "source"]
        if not all(k in data for k in required):
            return False

        l1 = str(data.get("shenwan_level1", "")).strip()
        l2 = str(data.get("shenwan_level2", "")).strip()
        l3 = str(data.get("shenwan_level3", "")).strip()
        source = str(data.get("source", "")).strip()

        if not source or source in {"unknown", "error"}:
            return False

        if not l1 or l1 in {"未分类", "错误"}:
            return False

        if l1 not in self.VALID_SHENWAN_L1:
            return False

        if not l2 or not l3:
            return False

        return True

    # -----------------
    # 数据源构建
    # -----------------

    def _build_sources_in_priority_order(self) -> List[Tuple[str, Callable]]:
        sources: List[Tuple[str, Callable]] = [
            ("sina_shenwan", self._get_from_sina_shenwan),
            ("eastmoney_f10", self._get_from_eastmoney_f10),
            ("eastmoney_quote", self._get_from_eastmoney_quote),
            ("tencent_quote", self._get_from_tencent_quote),
            ("netease_f10", self._get_from_netease_f10),
        ]

        def weight(name: str) -> int:
            return int(self.sources_config.get(name, {}).get("weight", 0))

        enabled_sources = []
        for name, func in sources:
            if self.sources_config.get(name, {}).get("enabled", True):
                enabled_sources.append((name, func))

        enabled_sources.sort(key=lambda x: weight(x[0]), reverse=True)
        return enabled_sources

    # -----------------
    # 数据源实现
    # -----------------

    def _get_from_eastmoney_f10(self, stock_code: str, _: str, __: str) -> Optional[IndustryResult]:
        code = self._to_eastmoney_f10_code(stock_code)
        if not code:
            return None

        url = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax"
        resp = self._make_request(url, {"code": code}, "GET", "https://emweb.securities.eastmoney.com/")
        if not resp:
            return None

        try:
            data = resp.json()
        except Exception:
            return None

        industry = str((data.get("jbzl") or {}).get("sshy") or "").strip()
        if not industry:
            return None

        l1, l2, l3 = self._infer_shenwan_levels(industry)
        return IndustryResult(l1, l2, l3, industry, "eastmoney_f10")

    def _get_from_eastmoney_quote(self, stock_code: str, _: str, __: str) -> Optional[IndustryResult]:
        secid = self._to_eastmoney_secid(stock_code)
        if not secid:
            return None

        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields": "f57,f58,f127",
        }
        resp = self._make_request(url, params, "GET", "https://quote.eastmoney.com/")
        if not resp:
            return None

        try:
            data = resp.json().get("data") or {}
        except Exception:
            return None

        industry = str(data.get("f127") or "").strip()
        # 该字段有时为空或为"-"
        if not industry or industry == "-":
            return None

        l1, l2, l3 = self._infer_shenwan_levels(industry)
        return IndustryResult(l1, l2, l3, industry, "eastmoney_quote")

    def _get_from_sina_shenwan(self, stock_code: str, _: str, __: str) -> Optional[IndustryResult]:
        url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCI_CorpOtherInfo/stockid/{stock_code}/menu_num/2.phtml"
        resp = self._make_request(url, None, "GET", "https://vip.stock.finance.sina.com.cn/")
        if not resp:
            return None

        text = resp.text
        soup = BeautifulSoup(text, "lxml")

        # 定位“所属行业板块”表格，并读取首行行业名称。
        tables = soup.select("table.comInfo1")
        for table in tables:
            title_cell = table.select_one("tr td")
            if not title_cell:
                continue
            if "所属行业板块" not in title_cell.get_text(strip=True):
                continue

            rows = table.select("tr")
            # 0: 标题行, 1: 表头行, 2: 数据行
            if len(rows) < 3:
                continue

            cells = rows[2].select("td")
            if not cells:
                continue

            industry = cells[0].get_text(strip=True)
            if not industry:
                continue

            l1, l2, l3 = self._infer_shenwan_levels(industry)
            return IndustryResult(l1, l2, l3, industry, "sina_shenwan")

        return None

    def _get_from_tencent_quote(self, stock_code: str, _: str, __: str) -> Optional[IndustryResult]:
        # 腾讯行情接口主要返回行情字段，行业信息不稳定；本源作为兜底尝试。
        symbol = ("sh" if stock_code.startswith("6") else "sz") + stock_code
        url = f"https://qt.gtimg.cn/q={symbol}"
        resp = self._make_request(url, None, "GET", "https://gu.qq.com/")
        if not resp:
            return None

        text = resp.text
        # 若未来接口在尾部增加行业字段，可以在此处补充解析。
        # 当前仅尝试从响应中提取可疑的中文行业短语（低可靠性）。
        m = re.search(r"行业[:：]\s*([^~;\"\n]{2,20})", text)
        if not m:
            return None

        industry = m.group(1).strip()
        if not industry:
            return None

        l1, l2, l3 = self._infer_shenwan_levels(industry)
        return IndustryResult(l1, l2, l3, industry, "tencent_quote")

    def _get_from_netease_f10(self, stock_code: str, _: str, __: str) -> Optional[IndustryResult]:
        # 网易财经在部分网络环境会返回502，这里保留为低优先级源并做容错。
        url = f"https://quotes.money.163.com/f10/gszl_{stock_code}.html"
        resp = self._make_request(url, None, "GET", "https://quotes.money.163.com/")
        if not resp:
            return None

        if resp.status_code >= 400:
            return None

        text = resp.text
        m = re.search(r"所属行业</span>\s*<span[^>]*>\s*(?:<a[^>]*>)?([^<]+)", text)
        if not m:
            return None

        industry = m.group(1).strip()
        if not industry:
            return None

        l1, l2, l3 = self._infer_shenwan_levels(industry)
        return IndustryResult(l1, l2, l3, industry, "netease_f10")

    # -----------------
    # 批量源：东方财富行业板块 -> 成分股
    # -----------------

    def _batch_from_eastmoney_industry_board(self, remaining: Set[str]) -> Dict[str, Dict[str, str]]:
        results: Dict[str, Dict[str, str]] = {}

        boards = self._get_eastmoney_industry_boards()
        if not boards:
            return results

        for board_code, board_name in boards:
            if not remaining:
                break

            members = self._get_eastmoney_board_members(board_code)
            if not members:
                continue

            l1, l2, l3 = self._infer_shenwan_levels(board_name)
            for code in members:
                if code not in remaining:
                    continue

                res = IndustryResult(l1, l2, l3, board_name, "eastmoney_industry_board")
                if self.validate_industry_data(res.as_dict()):
                    results[code] = res.as_dict()
                    self.cache[code] = res.as_dict()
                    remaining.remove(code)

        return results

    def _get_eastmoney_industry_boards(self) -> List[Tuple[str, str]]:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 200,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": "m:90 t:2",
            "fields": "f12,f14",
        }

        resp = self._make_request(url, params, "GET", "https://quote.eastmoney.com/")
        if not resp:
            return []

        try:
            diff = (resp.json().get("data") or {}).get("diff") or []
        except Exception:
            return []

        boards: List[Tuple[str, str]] = []
        for item in diff:
            code = str(item.get("f12") or "").strip()
            name = str(item.get("f14") or "").strip()
            if code and name and code.startswith("BK"):
                boards.append((code, name))

        return boards

    def _get_eastmoney_board_members(self, board_code: str) -> Set[str]:
        url = "https://push2.eastmoney.com/api/qt/clist/get"

        members: Set[str] = set()
        page = 1
        page_size = 5000

        while True:
            params = {
                "pn": page,
                "pz": page_size,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": f"b:{board_code}",
                "fields": "f12,f14",
            }

            resp = self._make_request(url, params, "GET", "https://quote.eastmoney.com/")
            if not resp:
                break

            try:
                data = resp.json().get("data") or {}
                diff = data.get("diff") or []
                total = int(data.get("total") or 0)
            except Exception:
                break

            for item in diff:
                code = str(item.get("f12") or "").strip()
                if re.fullmatch(r"\d{6}", code):
                    members.add(code)

            if len(members) >= total or len(diff) < page_size:
                break

            page += 1

        return members

    # -----------------
    # 推断与格式化
    # -----------------

    def _infer_shenwan_levels(self, raw_industry: str) -> Tuple[str, str, str]:
        industry = self._clean_industry_text(raw_industry)
        if not industry:
            return "综合", "综合", "综合"

        l1 = self._infer_shenwan_l1(industry)
        # 目前外部公开接口很难稳定提供SW二级/三级；
        # 这里采用“可解释的补全策略”：用获取到的行业名称同时填充二级/三级。
        l2 = industry
        l3 = industry

        return l1, l2, l3

    def _infer_shenwan_l1(self, industry: str) -> str:
        s = industry
        rules: List[Tuple[str, str]] = [
            (r"银行", "银行"),
            (r"证券|保险|期货|信托|金融", "非银金融"),
            (r"房地产|物业", "房地产"),
            (r"医药|医疗|生物|疫苗|器械", "医药生物"),
            (r"白酒|啤酒|葡萄酒|饮料|乳业|食品|酿酒", "食品饮料"),
            (r"家电|空调|冰箱|厨电", "家用电器"),
            (r"半导体|芯片|元件|电子|光学|面板|显示", "电子"),
            (r"计算机|软件|IT|信息技术|云计算|大数据|网络安全", "计算机"),
            (r"通信|运营商|光通信|5G", "通信"),
            (r"传媒|影视|游戏|出版|广告", "传媒"),
            (r"汽车|整车|汽配|新能源车", "汽车"),
            (r"电池|光伏|风电|电网|储能|电力设备|电气设备", "电力设备"),
            (r"机械|机床|设备", "机械设备"),
            (r"军工|航空|航天|兵器|船舶", "国防军工"),
            (r"煤炭", "煤炭"),
            (r"石油|天然气|油服", "石油石化"),
            (r"钢铁", "钢铁"),
            (r"有色|贵金属|稀土|锂|钴|镍", "有色金属"),
            (r"化工|农药|化学|塑料|橡胶", "基础化工"),
            (r"建筑材料|水泥|玻璃", "建筑材料"),
            (r"建筑装饰|装修|工程", "建筑装饰"),
            (r"商贸|零售|百货|超市|电商", "商贸零售"),
            (r"酒店|旅游|餐饮|景区|航空服务", "社会服务"),
            (r"交通|运输|物流|航运|港口|机场|铁路", "交通运输"),
            (r"电力|燃气|水务|公用", "公用事业"),
            (r"环保|污水|固废", "环保"),
            (r"纺织|服装|鞋帽", "纺织服饰"),
            (r"轻工|造纸|包装|家居", "轻工制造"),
            (r"美容|护理|化妆品", "美容护理"),
            (r"农|牧|渔|种植", "农林牧渔"),
        ]

        for pattern, l1 in rules:
            if re.search(pattern, s):
                return l1

        return "综合"

    @staticmethod
    def _clean_industry_text(text: str) -> str:
        s = str(text or "").strip()
        s = re.sub(r"\s+", " ", s)
        s = s.replace("行业", "") if len(s) <= 10 else s
        return s.strip()

    def _fallback_result(self, source: str) -> IndustryResult:
        return IndustryResult("未分类", "未分类", "未分类", "未分类", source)

    @staticmethod
    def _to_eastmoney_secid(stock_code: str) -> Optional[str]:
        if not re.fullmatch(r"\d{6}", stock_code):
            return None
        return ("1." if stock_code.startswith("6") else "0.") + stock_code

    @staticmethod
    def _to_eastmoney_f10_code(stock_code: str) -> Optional[str]:
        if not re.fullmatch(r"\d{6}", stock_code):
            return None
        return ("SH" if stock_code.startswith("6") else "SZ") + stock_code
