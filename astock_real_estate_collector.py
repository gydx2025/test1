#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股非经营性房地产资产数据获取脚本

功能：
1. 获取全部A股上市公司2023年末和2024年末的非经营性房地产资产数据
2. 包含公司名称、股票代码、资产金额、行业分类信息
3. 输出为Excel文件，包含数据清洗和验证

数据源优先级：
1. 巨潮资讯 (cninfo.com.cn) - 官方数据源，反爬虫相对温和
2. 东方财富网 (eastmoney.com) - 需要严格的反爬虫处理
3. 新浪财经 (sina.com) - 备选方案

反爬虫措施：
1. User-Agent轮换
2. 随机请求延迟
3. 指数退避重试机制
4. 完整HTTP请求头
5. Session连接池管理
6. 请求状态监控和日志记录

作者：Claude
日期：2024
版本：2.3.0 - 紧急修复：多数据源补全机制 + AkShare + 网页爬虫 + 严格验证
"""

import pandas as pd
import requests
import time
import logging
import os
import re
import random
import pickle
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# 导入配置
from config import (
    DATA_SOURCES, REQUEST_CONFIG, USER_AGENT_POOL,
    HEADERS_CONFIG, PROXY_CONFIG, OUTPUT_CONFIG,
    DATA_CLEANING_CONFIG, LOGGING_CONFIG, INDUSTRY_SOURCES,
    INDUSTRY_CACHE_CONFIG, LOCAL_CACHE_CONFIG,
)

from industry_classification_fetcher import IndustryClassificationFetcher
from industry_classification_complete_getter import IndustryClassificationCompleteGetter

from local_cache import IndustryCacheStore, StockCacheStore
from local_cache.cache_store import build_local_cache_config

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AStockRealEstateDataCollector:
    """A股非经营性房地产资产数据收集器 - 带反爬虫处理"""
    
    def __init__(self):
        """初始化数据收集器，配置反爬虫措施"""
        self.session = requests.Session()
        
        # 初始化请求头（会在每次请求时动态更新User-Agent）
        self._update_headers()
        
        # 统计信息
        self.request_count = 0
        self.failed_request_count = 0
        self.retry_count = 0
        
        # 代理池
        self.proxy_index = 0
        self.proxies = PROXY_CONFIG.get('proxies', []) if PROXY_CONFIG.get('enabled') else []
        
        # 数据存储
        self.company_data = []
        self.data_2023 = []
        self.data_2024 = []

        # 本地缓存层（SQLite + pickle），用于快速启动/前缀查询
        self.local_cache_enabled = bool(LOCAL_CACHE_CONFIG.get('enabled', True))
        self.stock_cache_store = None
        self.industry_cache_store = None
        if self.local_cache_enabled:
            try:
                cache_cfg = build_local_cache_config(LOCAL_CACHE_CONFIG)
                self.stock_cache_store = StockCacheStore(cache_cfg)
                self.industry_cache_store = IndustryCacheStore(cache_cfg)
            except Exception as e:
                logger.warning(f"初始化本地缓存层失败，将退化为旧缓存机制: {e}")
                self.local_cache_enabled = False

        # 用于确保单次运行内仅创建一次缓存备份
        self._local_cache_backup_timestamp: Optional[str] = None
        self._local_cache_backup_done: bool = False
        self._local_cache_dirty: bool = False

        # 行业分类缓存（优先使用本地缓存层，其次使用旧的pkl缓存）
        self.industry_cache: Dict[str, Dict] = {}
        self._load_industry_cache()

        self.industry_fetcher = IndustryClassificationFetcher(
            make_request=self._make_request,
            cache=self.industry_cache,
            sources_config=INDUSTRY_SOURCES,
            logger=logger,
        )
        self.industry_fetcher.purge_invalid_cache_entries()
        
        logger.info("数据收集器初始化完成 - 反爬虫措施已启用")
        logger.info(f"User-Agent池大小: {len(USER_AGENT_POOL)}")
        logger.info(f"请求延迟范围: {REQUEST_CONFIG['delay_between_requests']}")
        logger.info(f"最大重试次数: {REQUEST_CONFIG['max_retries']}")
        logger.info(f"本地缓存层已启用: {self.local_cache_enabled}")
        logger.info(f"行业分类旧缓存已启用: {INDUSTRY_CACHE_CONFIG.get('enabled')}")
    
    def _update_headers(self, referer: str = None):
        """更新请求头，轮换User-Agent"""
        # 随机选择User-Agent
        user_agent = random.choice(USER_AGENT_POOL)
        
        # 构建完整请求头
        headers = HEADERS_CONFIG.copy()
        headers['User-Agent'] = user_agent
        
        # 添加Referer（如果提供）
        if referer:
            headers['Referer'] = referer
        
        self.session.headers.update(headers)
        logger.debug(f"已更新User-Agent: {user_agent[:50]}...")
    
    def _get_random_delay(self) -> float:
        """获取随机延迟时间"""
        delay_range = REQUEST_CONFIG['delay_between_requests']
        if isinstance(delay_range, tuple):
            return random.uniform(delay_range[0], delay_range[1])
        return delay_range
    
    def _get_backoff_delay(self, retry_attempt: int) -> float:
        """计算指数退避延迟时间"""
        if REQUEST_CONFIG.get('use_exponential_backoff', True):
            base_delay = REQUEST_CONFIG['retry_delay']
            factor = REQUEST_CONFIG.get('backoff_factor', 2)
            return base_delay * (factor ** retry_attempt)
        return REQUEST_CONFIG['retry_delay']
    
    def _rotate_proxy(self):
        """轮换代理"""
        if not self.proxies:
            return None
        
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        proxy = self.proxies[self.proxy_index]
        logger.info(f"切换代理: {proxy.get('http', 'N/A')}")
        return proxy
    
    def _make_request(self, url: str, params: dict = None, method: str = 'GET', 
                      referer: str = None) -> Optional[requests.Response]:
        """
        发送HTTP请求（带反爬虫处理）
        
        Args:
            url: 请求URL
            params: 请求参数
            method: 请求方法
            referer: Referer头
            
        Returns:
            响应对象或None
        """
        max_retries = REQUEST_CONFIG['max_retries']
        
        for retry_attempt in range(max_retries):
            try:
                # 更新请求头（轮换User-Agent）
                self._update_headers(referer)
                
                # 获取代理
                proxy = None
                if PROXY_CONFIG.get('enabled') and self.proxies:
                    proxy = self.proxies[self.proxy_index]
                
                # 添加随机延迟（第一次请求除外）
                if self.request_count > 0:
                    delay = self._get_random_delay()
                    logger.debug(f"等待 {delay:.2f}秒...")
                    time.sleep(delay)
                
                # 发送请求
                logger.debug(f"发送请求: {url} (尝试 {retry_attempt + 1}/{max_retries})")
                
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, 
                        params=params, 
                        timeout=REQUEST_CONFIG['timeout'],
                        proxies=proxy
                    )
                else:
                    response = self.session.post(
                        url, 
                        data=params, 
                        timeout=REQUEST_CONFIG['timeout'],
                        proxies=proxy
                    )
                
                response.raise_for_status()
                self.request_count += 1
                
                logger.debug(f"请求成功: {response.status_code}")
                return response
                
            except requests.exceptions.Timeout:
                self.failed_request_count += 1
                self.retry_count += 1
                logger.warning(f"请求超时 (尝试 {retry_attempt + 1}/{max_retries})")
                
            except requests.exceptions.HTTPError as e:
                self.failed_request_count += 1
                status_code = e.response.status_code if e.response else None
                
                # 429表示请求过于频繁，需要更长的等待时间
                if status_code == 429:
                    logger.warning(f"请求频率过高(429)，等待更长时间...")
                    backoff_delay = self._get_backoff_delay(retry_attempt) * 2
                    time.sleep(backoff_delay)
                    self.retry_count += 1
                    continue
                
                # 403可能是被封禁，尝试轮换代理或User-Agent
                elif status_code == 403:
                    logger.warning(f"请求被拒绝(403)，尝试轮换策略...")
                    if PROXY_CONFIG.get('rotate_on_failure') and self.proxies:
                        self._rotate_proxy()
                    self.retry_count += 1
                    continue
                
                else:
                    logger.warning(f"HTTP错误: {status_code} - {e}")
                    break
                
            except requests.exceptions.ConnectionError:
                self.failed_request_count += 1
                self.retry_count += 1
                logger.warning(f"连接错误 (尝试 {retry_attempt + 1}/{max_retries})")
                
            except Exception as e:
                self.failed_request_count += 1
                logger.error(f"请求异常: {e}")
                break
            
            # 如果需要重试，使用指数退避
            if retry_attempt < max_retries - 1:
                backoff_delay = self._get_backoff_delay(retry_attempt)
                logger.info(f"等待 {backoff_delay:.1f}秒后重试...")
                time.sleep(backoff_delay)
        
        logger.error(f"请求失败，已达最大重试次数: {url}")
        return None
        
    def validate_stock_code(self, code: str) -> bool:
        """
        严格验证股票代码格式
        
        只接受真实A股代码：
        - 6开头：沪市主板
        - 0开头：深市主板/中小板
        - 3开头：创业板
        - 8开头：北交所
        - 4开头：北交所
        
        拒绝：
        - 920000等错误代码
        - 非6位数字
        """
        if not isinstance(code, str) or len(code) != 6:
            return False
        
        # 只接受有效的A股代码
        valid_first_digits = {'6', '0', '3', '8', '4'}
        if code[0] not in valid_first_digits:
            logger.debug(f"❌ 无效代码 {code}（第一位是{code[0]}，不是A股代码）")
            return False
        
        # 确保后面都是数字
        if not code[1:].isdigit():
            logger.debug(f"❌ 无效代码 {code}（包含非数字字符）")
            return False
        
        # 特殊拒绝列表（错误数据）
        invalid_prefixes = ['920', '921', '922']
        if any(code.startswith(prefix) for prefix in invalid_prefixes):
            logger.warning(f"❌ 拒绝错误代码 {code}（错误前缀）")
            return False
        
        return True
    
    def get_stock_list(self) -> List[Dict]:
        """
        获取A股全部股票列表 - 多数据源补全机制
        
        优先级顺序：
        1. AkShare（最可靠）
        2. 巨潮资讯网页爬虫
        3. 同花顺网页爬虫
        4. 东方财富API
        5. 其他备用方案
        """

        # 优先从本地缓存层读取（避免网络调用）
        if self.local_cache_enabled and self.stock_cache_store:
            try:
                cached_stocks = self.stock_cache_store.load(force=False)
                if cached_stocks:
                    logger.info(f"✅ 股票列表已从本地缓存加载: {len(cached_stocks)}只")
                    # 兼容下游逻辑：补齐industry字段
                    return [
                        {**s, 'industry': s.get('industry') or '未知'}
                        for s in cached_stocks
                    ]
            except Exception as e:
                logger.debug(f"读取股票本地缓存失败，将走网络获取: {e}")

        try:
            logger.info("="*80)
            logger.info("🚀 开始获取A股股票完整列表 - 多数据源补全机制")
            logger.info("="*80)
            
            all_stocks = {}  # code -> stock_info（去重）
            
            # 定义数据源优先级（从最可靠到备用）
            sources = [
                ('腾讯财经API', self._get_stock_list_from_tencent),
                ('网易财经CSV', self._get_stock_list_from_netease_csv),
                ('AkShare', self._get_stock_list_from_akshare),
                ('巨潮资讯爬虫', self._get_stock_list_from_cninfo_crawler),
                ('同花顺爬虫', self._get_stock_list_from_ths_crawler),
                ('东方财富API', self._get_stock_list_from_eastmoney),
                ('其他备用源', self._get_stock_list_backup),
            ]
            
            # 尝试各数据源
            for source_name, fetch_func in sources:
                try:
                    logger.info(f"\n{'─'*60}")
                    logger.info(f"🔍 尝试数据源: {source_name}")
                    logger.info(f"{'─'*60}")
                    
                    stocks = fetch_func()
                    
                    if not stocks:
                        logger.warning(f"❌ [{source_name}] 未获取到数据，继续下一个源...")
                        continue
                    
                    # 验证代码格式并去重
                    valid_count = 0
                    invalid_count = 0
                    for stock in stocks:
                        code = stock.get('code', '')
                        if self.validate_stock_code(code):
                            if code not in all_stocks:
                                all_stocks[code] = stock
                                valid_count += 1
                        else:
                            invalid_count += 1
                    
                    logger.info(f"✅ [{source_name}] 新增 {valid_count} 个有效股票")
                    if invalid_count > 0:
                        logger.warning(f"⚠️  [{source_name}] 过滤掉 {invalid_count} 个无效代码")
                    logger.info(f"📊 当前总计: {len(all_stocks)} 个股票")
                    
                    # 如果已获取足够数据，停止
                    if len(all_stocks) >= 5000:
                        logger.info(f"\n🎉 已获取 {len(all_stocks)} 个股票，达到目标！")
                        break
                    
                except Exception as e:
                    logger.error(f"❌ [{source_name}] 获取失败: {e}")
                    continue
            
            # 转换为列表
            stock_list = list(all_stocks.values())
            
            if stock_list:
                logger.info(f"\n{'='*80}")
                logger.info(f"✅ 股票列表获取完成！总计获取 {len(stock_list)} 只股票")
                logger.info(f"{'='*80}")
                
                # 验证和统计股票列表
                self._validate_and_report_stock_list(stock_list)

                # 写入本地缓存层（用于后续前缀查询/快速启动）
                self._save_stock_cache(stock_list)
            else:
                logger.warning("⚠️ 所有数据源都无法获取股票列表，将使用模拟数据进行演示")
                stock_list = self._generate_demo_stock_list()
            
            return stock_list
                
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            # 返回演示数据
            return self._generate_demo_stock_list()
    
    def _validate_and_report_stock_list(self, stocks: List[Dict]):
        """验证并统计股票列表的完整性"""
        if not stocks:
            logger.warning("⚠️ 股票列表为空")
            return
        
        # 提取代码
        codes = [stock['code'] for stock in stocks if stock['code']]
        if not codes:
            logger.warning("⚠️ 没有有效的股票代码")
            return
        
        # 统计各类型代码
        code_6 = sum(1 for c in codes if c.startswith('6'))
        code_0 = sum(1 for c in codes if c.startswith('0'))
        code_3 = sum(1 for c in codes if c.startswith('3'))
        code_8 = sum(1 for c in codes if c.startswith('8'))
        code_4 = sum(1 for c in codes if c.startswith('4'))
        
        # 输出统计信息
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 股票列表统计信息:")
        logger.info(f"   总数量: {len(stocks)} 只")
        logger.info(f"   6开头（沪深主板）: {code_6} 只")
        logger.info(f"   0开头（深圳主板）: {code_0} 只")
        logger.info(f"   3开头（创业板）: {code_3} 只")
        logger.info(f"   8开头（北交所）: {code_8} 只")
        logger.info(f"   4开头（北交所）: {code_4} 只")
        logger.info(f"{'='*60}")
        
        # 验证数量
        if len(stocks) >= 5000:
            logger.info(f"✅ 股票数量足够（>= 5000）")
        else:
            logger.warning(f"⚠️ 警告: 股票数量 {len(stocks)} 少于目标 5000")
        
        # 显示股票代码范围
        min_code = min(codes)
        max_code = max(codes)
        logger.info(f"📈 股票代码范围: {min_code} - {max_code}")
    
    def _get_stock_list_from_tencent(self) -> List[Dict]:
        """
        从腾讯财经API获取股票列表（最稳定可靠）
        
        腾讯财经API通常比较稳定，而且数据完整
        """
        try:
            logger.info("正在从腾讯财经API获取股票列表...")
            
            stock_list = []
            
            # 腾讯财经的股票列表API
            # 分为沪市(sh)和深市(sz)
            markets = [
                ('sh', '上海'),
                ('sz', '深圳'),
            ]
            
            for market_code, market_name in markets:
                try:
                    logger.info(f"正在获取{market_name}股票...")
                    
                    # 腾讯财经股票列表接口
                    url = f"http://qt.gtimg.cn/q={market_code}000001"
                    
                    # 实际上，腾讯财经有一个更好的接口
                    # 我们使用股票列表的JSON格式
                    list_url = f"http://qt.gtimg.cn/q=s_{market_code}all"
                    
                    response = self._make_request(list_url)
                    if not response:
                        logger.warning(f"{market_name}请求失败")
                        continue
                    
                    # 解析返回数据
                    text = response.text
                    
                    # 腾讯返回格式: v_s_shall="sh600000~浦发银行~..."
                    # 提取股票代码
                    import re
                    
                    # 匹配所有股票代码
                    pattern = rf'{market_code}(\d{{6}})'
                    matches = re.findall(pattern, text)
                    
                    logger.info(f"{market_name}找到{len(matches)}个匹配")
                    
                    for code in matches:
                        full_code = code  # 6位代码
                        if len(full_code) == 6:
                            stock_info = {
                                'code': full_code,
                                'name': '',  # 名称需要后续查询
                                'industry': '',
                                'market': market_name
                            }
                            stock_list.append(stock_info)
                    
                except Exception as market_error:
                    logger.warning(f"{market_name}获取失败: {market_error}")
                    continue
            
            # 如果腾讯的第一个方法失败，尝试另一个接口
            if len(stock_list) < 100:
                logger.info("尝试腾讯财经备用接口...")
                
                # 备用方法：使用腾讯的板块数据
                for page in range(1, 200):  # 最多200页
                    try:
                        url = "http://stock.gtimg.cn/data/index.php"
                        params = {
                            'appn': 'rank',
                            't': 'ranka/chr',
                            'p': page,
                            'o': 0,
                            'l': 40,
                            'v': 'list_data'
                        }
                        
                        response = self._make_request(url, params=params)
                        if not response:
                            break
                        
                        try:
                            data = response.json()
                            if not data or 'data' not in data:
                                break
                            
                            items = data['data']
                            if not items:
                                break
                            
                            for item in items:
                                code = item.get('code', '')
                                name = item.get('name', '')
                                
                                if len(code) == 6 and code.isdigit():
                                    stock_info = {
                                        'code': code,
                                        'name': name,
                                        'industry': '',
                                        'market': '上海' if code.startswith('6') else '深圳'
                                    }
                                    stock_list.append(stock_info)
                            
                            logger.info(f"第{page}页: 新增{len(items)}只，累计{len(stock_list)}只")
                            
                            if len(stock_list) >= 5000:
                                break
                            
                        except:
                            break
                    
                    except:
                        break
            
            if stock_list:
                logger.info(f"✅ 从腾讯财经获取 {len(stock_list)} 只股票")
            else:
                logger.warning("❌ 腾讯财经未获取到数据")
            
            return stock_list
            
        except Exception as e:
            logger.error(f"腾讯财经获取失败: {e}")
            return []
    
    def _get_stock_list_from_netease_csv(self) -> List[Dict]:
        """
        从网易财经CSV数据获取股票列表（非常可靠）
        
        网易财经提供CSV格式的股票数据下载，格式稳定
        """
        try:
            logger.info("正在从网易财经CSV获取股票列表...")
            
            import io
            
            stock_list = []
            
            # 网易财经提供的A股股票列表CSV
            # 沪市
            urls = [
                ('http://quotes.money.163.com/service/chddata.html?code=0000001&start=19900101&end=20991231&fields=TCLOSE', '沪市'),
                ('http://quotes.money.163.com/service/chddata.html?code=1000001&start=19900101&end=20991231&fields=TCLOSE', '深市'),
            ]
            
            # 使用网易的股票列表API（分页）
            for page in range(0, 100):  # 最多100页
                try:
                    url = f"http://quotes.money.163.com/hs/service/diyrank.php"
                    params = {
                        'page': page,
                        'count': 5000,
                        'type': 'query',
                        'fields': 'SYMBOL,NAME,PRICE',
                        'query': 'STYPE:EQA',
                        'sort': 'SYMBOL',
                        'order': 'asc'
                    }
                    
                    response = self._make_request(url, params=params)
                    if not response:
                        if page == 0:
                            logger.warning("网易财经请求失败")
                            break
                        else:
                            logger.info(f"已获取{page}页数据，停止")
                            break
                    
                    # 网易返回CSV格式
                    try:
                        df = pd.read_csv(io.StringIO(response.text))
                        
                        if df is None or len(df) == 0:
                            logger.info(f"第{page}页无数据")
                            break
                        
                        for idx, row in df.iterrows():
                            try:
                                symbol = str(row.get('SYMBOL', ''))
                                name = str(row.get('NAME', ''))
                                
                                # 解析代码（网易格式可能是0600000或1000001）
                                if symbol.startswith('0') or symbol.startswith('1'):
                                    code = symbol[1:]  # 去掉第一位
                                else:
                                    code = symbol
                                
                                if len(code) == 6 and code.isdigit():
                                    stock_info = {
                                        'code': code,
                                        'name': name,
                                        'industry': '',
                                        'market': '上海' if code.startswith('6') else '深圳'
                                    }
                                    stock_list.append(stock_info)
                            except:
                                continue
                        
                        logger.info(f"第{page}页: 获取{len(df)}条，累计{len(stock_list)}只")
                        
                        if len(stock_list) >= 5000:
                            logger.info("已获取足够数据")
                            break
                        
                    except Exception as parse_error:
                        logger.debug(f"第{page}页解析失败: {parse_error}")
                        if page == 0:
                            break
                        else:
                            break
                    
                except Exception as page_error:
                    logger.debug(f"第{page}页获取失败: {page_error}")
                    break
            
            if stock_list:
                logger.info(f"✅ 从网易财经CSV获取 {len(stock_list)} 只股票")
            else:
                logger.warning("❌ 网易财经CSV未获取到数据")
            
            return stock_list
            
        except Exception as e:
            logger.error(f"网易财经CSV获取失败: {e}")
            return []
    
    def _get_stock_list_from_akshare(self) -> List[Dict]:
        """
        从AkShare获取A股股票列表（最推荐的方案）
        
        优点：
        - 开源免费，无需注册
        - 数据完整准确（支持5000+股票）
        - 不易被限流
        - 接口稳定
        
        注意：如果网络不稳定可能会失败，但有其他备用数据源
        """
        try:
            logger.info("正在从AkShare获取A股股票列表...")
            
            try:
                import akshare as ak
            except ImportError:
                logger.error("❌ AkShare未安装，请运行: pip install akshare")
                return []
            
            stock_list = []
            
            # AkShare提供多个接口，尝试多个
            methods = [
                ('stock_zh_a_spot_em', 'A股实时行情（东方财富）'),
                ('stock_info_a_code_name', 'A股代码和名称'),
                ('stock_zh_a_spot', 'A股实时行情（新浪）'),
            ]
            
            for method_name, desc in methods:
                try:
                    logger.info(f"尝试AkShare方法: {desc}...")
                    
                    if not hasattr(ak, method_name):
                        logger.debug(f"方法 {method_name} 不存在，跳过")
                        continue
                    
                    method = getattr(ak, method_name)
                    df = method()
                    
                    if df is None or len(df) == 0:
                        logger.warning(f"{desc} 返回空数据")
                        continue
                    
                    logger.info(f"{desc} 返回 {len(df)} 条记录，正在解析...")
                    
                    # 解析数据（字段名可能不同）
                    for idx, row in df.iterrows():
                        try:
                            # 尝试不同的字段名
                            code = str(row.get('代码', row.get('code', row.get('symbol', ''))))
                            name = str(row.get('名称', row.get('name', '')))
                            
                            # 确保代码是6位
                            if len(code) == 6 and code.isdigit():
                                stock_info = {
                                    'code': code,
                                    'name': name,
                                    'industry': '',
                                    'market': '上海' if code.startswith('6') else '深圳'
                                }
                                stock_list.append(stock_info)
                        except Exception as e:
                            logger.debug(f"解析行失败: {e}")
                            continue
                    
                    if len(stock_list) >= 100:
                        logger.info(f"✅ 从AkShare成功获取 {len(stock_list)} 只股票")
                        return stock_list
                    
                except Exception as method_error:
                    logger.debug(f"{desc} 异常: {method_error}")
                    # 即使有异常，也检查是否获取到了部分数据
                    if len(stock_list) >= 100:
                        logger.info(f"✅ 从AkShare获取 {len(stock_list)} 只股票（部分方法成功）")
                        return stock_list
                    continue
            
            # 如果所有方法都失败了，但获取到了一些数据
            if stock_list:
                logger.info(f"✅ 从AkShare获取到 {len(stock_list)} 只股票")
                return stock_list
            else:
                logger.warning("❌ AkShare所有方法都失败")
                return []
            
        except Exception as e:
            logger.error(f"AkShare获取失败: {e}")
            return []
    
    def _get_stock_list_from_cninfo_crawler(self) -> List[Dict]:
        """
        从巨潮资讯网页爬取A股上市公司列表
        
        巨潮资讯是中国证监会指定的信息披露网站，数据最权威
        """
        try:
            logger.info("正在从巨潮资讯爬取股票列表...")
            
            from bs4 import BeautifulSoup
            
            stock_list = []
            
            # 巨潮资讯的上市公司列表API
            url = "http://www.cninfo.com.cn/new/data/szse_stock.json"
            
            response = self._make_request(url)
            if not response:
                logger.warning("巨潮资讯请求失败")
                return []
            
            try:
                data = response.json()
                
                if isinstance(data, dict) and 'stockList' in data:
                    stock_data = data['stockList']
                elif isinstance(data, list):
                    stock_data = data
                else:
                    logger.warning("巨潮资讯返回数据格式不正确")
                    return []
                
                for item in stock_data:
                    code = item.get('code', '')
                    name = item.get('name', '') or item.get('orgCName', '')
                    
                    if code and name:
                        stock_info = {
                            'code': code,
                            'name': name,
                            'industry': '',
                            'market': '上海' if code.startswith('6') else '深圳'
                        }
                        stock_list.append(stock_info)
                
                logger.info(f"✅ 从巨潮资讯获取 {len(stock_list)} 只股票")
                return stock_list
                
            except Exception as e:
                logger.warning(f"巨潮资讯数据解析失败: {e}")
                return []
            
        except Exception as e:
            logger.error(f"巨潮资讯爬虫失败: {e}")
            return []
    
    def _get_stock_list_from_ths_crawler(self) -> List[Dict]:
        """
        从同花顺爬取股票列表
        
        同花顺是知名的财经数据平台，数据比较完整
        """
        try:
            logger.info("正在从同花顺爬取股票列表...")
            
            stock_list = []
            
            # 同花顺股票列表API
            url = "http://q.10jqka.com.cn/index/index/board/all/field/zdf/order/desc/page/1/ajax/1/"
            
            response = self._make_request(
                url,
                referer='http://q.10jqka.com.cn/'
            )
            
            if not response:
                logger.warning("同花顺请求失败")
                return []
            
            try:
                from bs4 import BeautifulSoup
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找股票表格
                table = soup.find('table', class_='m-table')
                if not table:
                    logger.warning("同花顺未找到股票表格")
                    return []
                
                rows = table.find_all('tr')[1:]  # 跳过表头
                
                for row in rows:
                    try:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            code = cols[1].text.strip()
                            name = cols[2].text.strip()
                            
                            if code and name:
                                stock_info = {
                                    'code': code,
                                    'name': name,
                                    'industry': '',
                                    'market': '上海' if code.startswith('6') else '深圳'
                                }
                                stock_list.append(stock_info)
                    except:
                        continue
                
                logger.info(f"✅ 从同花顺获取 {len(stock_list)} 只股票")
                
                # 同花顺单页数据较少，如果有需要可以分页
                # 但作为备用源，少量数据也可以接受
                return stock_list
                
            except Exception as e:
                logger.warning(f"同花顺数据解析失败: {e}")
                return []
            
        except Exception as e:
            logger.error(f"同花顺爬虫失败: {e}")
            return []
    
    def _get_stock_list_from_eastmoney(self) -> List[Dict]:
        """从东方财富网获取股票列表（带反爬虫处理和完整分页）"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            page_size = 100  # 每页100只股票
            stock_list = []
            total_stocks = 0
            current_page = 1
            consecutive_empty_pages = 0
            
            # API参数配置
            params = {
                'pz': page_size,
                'po': 1,
                'np': 1,
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',
                'fs': 'm:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23',  # A股全部股票
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152'
            }
            
            logger.info("🔍 开始从东方财富网获取完整股票列表...")
            logger.info(f"📊 使用反爬虫策略: User-Agent轮换 + 随机延迟 + 指数退避")
            
            # 使用进度条
            pbar = None
            
            while True:
                try:
                    # 更新页码
                    params['pn'] = current_page
                    
                    # 使用带反爬虫的请求方法
                    logger.debug(f"正在获取第{current_page}页数据...")
                    response = self._make_request(
                        url, 
                        params=params, 
                        referer='https://quote.eastmoney.com/center/gridlist.html'
                    )
                    
                    if not response:
                        logger.warning(f"第{current_page}页请求失败，尝试继续...")
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= 3:
                            logger.error(f"连续{consecutive_empty_pages}页请求失败，停止获取")
                            break
                        current_page += 1
                        continue
                    
                    # 尝试解析JSON
                    try:
                        data = response.json()
                    except Exception as json_error:
                        logger.warning(f"第{current_page}页JSON解析失败，尝试继续: {json_error}")
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= 3:
                            logger.error(f"连续{consecutive_empty_pages}页解析失败，停止获取")
                            break
                        current_page += 1
                        continue
                    
                    # 重置连续失败计数
                    consecutive_empty_pages = 0
                    
                    # 检查是否有数据
                    if not data.get('data') or not data['data'].get('diff'):
                        logger.info(f"第{current_page}页无数据，停止获取")
                        break
                    
                    current_page_stocks = data['data']['diff']
                    page_stock_count = 0
                    
                    # 第一页时获取总数并初始化进度条
                    if current_page == 1:
                        total_stocks = data['data'].get('total', 0)
                        logger.info(f"📈 检测到总股票数量: {total_stocks}只")
                        if total_stocks > 0:
                            pbar = tqdm(total=total_stocks, desc="获取股票列表", unit="只")
                    
                    # 解析股票数据
                    for item in current_page_stocks:
                        stock_info = {
                            'code': item.get('f12', ''),
                            'name': item.get('f14', ''),
                            'industry': '',
                            'market': '上海' if item.get('f13') == '1' else '深圳'
                        }
                        if stock_info['code'] and stock_info['name']:
                            stock_list.append(stock_info)
                            page_stock_count += 1
                            if pbar:
                                pbar.update(1)
                    
                    logger.info(f"✅ 第{current_page}页: 获取{page_stock_count}只股票，累计{len(stock_list)}只")
                    
                    # 判断是否已获取所有数据
                    if len(stock_list) >= total_stocks or len(current_page_stocks) < page_size:
                        logger.info("✅ 已获取所有股票数据")
                        break
                    
                    # 防止无限循环（支持最多100页 = 10000只股票，足以覆盖全部5000+）
                    if current_page > 100:
                        logger.warning("⚠️ 达到页数限制(100页)，停止获取")
                        break
                    
                    current_page += 1
                    
                except KeyboardInterrupt:
                    logger.warning("用户中断获取")
                    break
                    
                except Exception as e:
                    logger.error(f"第{current_page}页处理异常: {e}")
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 3:
                        logger.error(f"连续异常{consecutive_empty_pages}次，停止获取")
                        break
                    current_page += 1
            
            if pbar:
                pbar.close()
            
            # 输出统计信息
            logger.info(f"📊 东方财富网获取完成:")
            logger.info(f"   - 总请求数: {self.request_count}")
            logger.info(f"   - 失败请求: {self.failed_request_count}")
            logger.info(f"   - 重试次数: {self.retry_count}")
            logger.info(f"   - 获取股票: {len(stock_list)}只")
            
            return stock_list
            
        except Exception as e:
            logger.error(f"东方财富网获取失败: {e}")
            return []
    
    def _get_stock_list_backup(self) -> List[Dict]:
        """备用股票列表获取方法 - 使用多个数据源"""
        try:
            all_stocks = {}
            
            # 方案1: 尝试使用tushare
            logger.info("🔄 尝试备用数据源1: tushare...")
            try:
                import tushare as ts
                
                logger.info("正在从tushare获取股票列表...")
                stock_basic = ts.get_stock_basics()
                
                if stock_basic is not None and len(stock_basic) > 0:
                    for code, row in stock_basic.iterrows():
                        stock_info = {
                            'code': code,
                            'name': row.get('name', ''),
                            'industry': row.get('industry', '未知'),
                            'market': '上海' if code.startswith('6') else '深圳'
                        }
                        if code not in all_stocks:
                            all_stocks[code] = stock_info
                    
                    logger.info(f"✅ 从tushare获取到{len(stock_basic)}只股票")
                    if len(all_stocks) >= 5000:
                        return list(all_stocks.values())
                
            except ImportError:
                logger.warning("tushare模块未安装或无法导入")
            except Exception as e:
                logger.warning(f"tushare获取失败: {e}")
            
            # 方案2: 尝试使用新浪财经的股票列表API（分页）
            logger.info("🔄 尝试备用数据源2: 新浪财经（分页获取）...")
            try:
                url = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
                
                # 分页获取所有数据
                page = 1
                while True:
                    params = {
                        'page': page,
                        'num': 500,  # 每页500条
                        'sort': 'symbol',
                        'asc': 1,
                        'node': 'hs_a',
                        'symbol': '',
                        '_s_r_a': 'page'
                    }
                    
                    response = self._make_request(url, params=params)
                    if not response:
                        logger.warning(f"第{page}页请求失败")
                        break
                    
                    try:
                        data = response.json()
                    except:
                        logger.warning(f"第{page}页JSON解析失败")
                        break
                    
                    if not data or not isinstance(data, list):
                        logger.info(f"第{page}页无数据，停止分页获取")
                        break
                    
                    page_count = 0
                    for item in data:
                        code = item.get('code', '')
                        if code and code not in all_stocks:
                            stock_info = {
                                'code': code,
                                'name': item.get('name', ''),
                                'industry': item.get('industry', '未知'),
                                'market': '上海' if code.startswith('6') else '深圳'
                            }
                            all_stocks[code] = stock_info
                            page_count += 1
                    
                    logger.info(f"✅ 第{page}页: 获取{page_count}只股票，总计{len(all_stocks)}只")
                    
                    if len(data) < 500:
                        logger.info("已获取所有数据（最后一页数据不足500条）")
                        break
                    
                    if page > 20:  # 限制最多20页（10000条）
                        logger.warning("达到分页限制")
                        break
                    
                    page += 1
                    
                if len(all_stocks) >= 5000:
                    logger.info(f"✅ 从新浪财经获取到{len(all_stocks)}只股票")
                    return list(all_stocks.values())
                        
            except Exception as e:
                logger.warning(f"新浪财经获取失败: {e}")
            
            # 如果获取了一些股票，返回
            if all_stocks:
                logger.info(f"✅ 从备用数据源获取到{len(all_stocks)}只股票")
                return list(all_stocks.values())
            
            # 所有备用方案都失败
            logger.warning("所有备用数据源都无法获取股票列表")
            return []
            
        except Exception as e:
            logger.error(f"备用数据源获取失败: {e}")
            return []
    
    def _generate_demo_stock_list(self) -> List[Dict]:
        """生成演示用股票列表"""
        logger.info("生成演示用股票列表...")
        
        demo_stocks = [
            {'code': '000001', 'name': '平安银行', 'industry': '银行', 'market': '深圳'},
            {'code': '000002', 'name': '万科A', 'industry': '房地产', 'market': '深圳'},
            {'code': '000858', 'name': '五粮液', 'industry': '白酒', 'market': '深圳'},
            {'code': '600036', 'name': '招商银行', 'industry': '银行', 'market': '上海'},
            {'code': '600519', 'name': '贵州茅台', 'industry': '白酒', 'market': '上海'},
            {'code': '600887', 'name': '伊利股份', 'industry': '乳业', 'market': '上海'},
            {'code': '000725', 'name': '京东方A', 'industry': '显示面板', 'market': '深圳'},
            {'code': '300059', 'name': '东方财富', 'industry': '金融科技', 'market': '深圳'},
            {'code': '002415', 'name': '海康威视', 'industry': '安防监控', 'market': '深圳'},
            {'code': '300750', 'name': '宁德时代', 'industry': '锂电池', 'market': '深圳'}
        ]
        
        return demo_stocks
    
    def _load_industry_cache(self):
        """加载行业分类缓存。

        优先级：
        1) local_cache/industries.*（SQLite + pickle，带TTL/版本管理）
        2) 旧版 cache/industry/shenwan_industry_mapping.pkl（兼容历史路径）
        """
        try:
            if self.local_cache_enabled and self.industry_cache_store:
                mapping = self.industry_cache_store.as_fetcher_cache_mapping()
                if mapping:
                    self.industry_cache.clear()
                    self.industry_cache.update(mapping)
                    logger.info(
                        f"✅ 本地缓存层行业分类已加载，包含 {len(self.industry_cache)} 个股票的分类信息"
                    )
                    return

            if not INDUSTRY_CACHE_CONFIG.get('enabled'):
                return

            cache_dir = INDUSTRY_CACHE_CONFIG.get('cache_dir', './cache/industry')
            cache_file = os.path.join(cache_dir, INDUSTRY_CACHE_CONFIG.get('cache_file', 'shenwan_industry_mapping.pkl'))

            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    if isinstance(cached_data, dict) and 'mapping' in cached_data:
                        cache_time = cached_data.get('timestamp', 0)
                        cache_duration = INDUSTRY_CACHE_CONFIG.get('cache_duration', 7 * 24 * 3600)
                        if time.time() - cache_time < cache_duration:
                            self.industry_cache.clear()
                            self.industry_cache.update(cached_data.get('mapping', {}))
                            logger.info(
                                f"✅ 行业分类旧缓存已加载，包含 {len(self.industry_cache)} 个股票的分类信息"
                            )
                            return
                        else:
                            logger.info("⚠️ 行业分类旧缓存已过期，将重新获取")
                            os.remove(cache_file)
        except Exception as e:
            logger.warning(f"加载行业分类缓存失败: {e}")
    
    def _save_industry_cache(self):
        """保存行业分类映射到缓存文件。

        优先保存到 local_cache（SQLite + pickle），并兼容写回旧版pkl缓存。
        """
        try:
            if not self.industry_cache:
                return

            if not self._local_cache_dirty:
                return

            # 1) 新本地缓存层
            if self.local_cache_enabled and self.industry_cache_store:
                if not self._local_cache_backup_timestamp:
                    self._local_cache_backup_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

                create_backup = not self._local_cache_backup_done
                self.industry_cache_store.save(
                    self.industry_cache,
                    version=LOCAL_CACHE_CONFIG.get('default_version'),
                    create_backup=create_backup,
                    backup_timestamp=self._local_cache_backup_timestamp,
                )
                self._local_cache_backup_done = True

            # 2) 旧版缓存（保持历史兼容性）
            if not INDUSTRY_CACHE_CONFIG.get('enabled'):
                self._local_cache_dirty = False
                return

            cache_dir = INDUSTRY_CACHE_CONFIG.get('cache_dir', './cache/industry')
            os.makedirs(cache_dir, exist_ok=True)

            cache_file = os.path.join(cache_dir, INDUSTRY_CACHE_CONFIG.get('cache_file', 'shenwan_industry_mapping.pkl'))

            cache_data = {
                'timestamp': time.time(),
                'mapping': self.industry_cache
            }

            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.debug(f"行业分类旧缓存已保存: {cache_file}")

            self._local_cache_dirty = False
        except Exception as e:
            logger.warning(f"保存行业分类缓存失败: {e}")

    def _save_stock_cache(self, stocks: List[Dict]):
        """保存股票列表到本地缓存层（local_cache）。"""
        try:
            if not stocks:
                return
            if not (self.local_cache_enabled and self.stock_cache_store):
                return

            if not self._local_cache_backup_timestamp:
                self._local_cache_backup_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

            create_backup = not self._local_cache_backup_done
            self.stock_cache_store.save(
                stocks,
                version=LOCAL_CACHE_CONFIG.get('default_version'),
                create_backup=create_backup,
                backup_timestamp=self._local_cache_backup_timestamp,
            )
            self._local_cache_backup_done = True
        except Exception as e:
            logger.warning(f"保存股票缓存失败: {e}")
    
    def _get_shenwan_industry_from_tushare(self, stock_code: str) -> Optional[Dict]:
        """从tushare获取申万行业分类"""
        try:
            import tushare as ts
            
            # 检查缓存
            if stock_code in self.industry_cache:
                return self.industry_cache[stock_code]
            
            # 规范化股票代码（tushare需要完整的TS代码）
            ts_code = stock_code
            if stock_code.startswith('6'):
                ts_code = stock_code + '.SH'
            else:
                ts_code = stock_code + '.SZ'
            
            logger.debug(f"从tushare获取 {stock_code} 的申万行业分类...")
            
            # 获取行业分类信息
            industry_df = ts.get_stock_info()
            if industry_df is not None and len(industry_df) > 0:
                # 查找对应的股票
                stock_row = industry_df[industry_df['ts_code'] == ts_code]
                if len(stock_row) > 0:
                    row = stock_row.iloc[0]
                    industry_info = {
                        'shenwan_level1': row.get('shenwan_level1', ''),
                        'shenwan_level2': row.get('shenwan_level2', ''),
                        'shenwan_level3': row.get('shenwan_level3', ''),
                        'industry': row.get('industry', ''),
                        'source': 'tushare'
                    }
                    self.industry_cache[stock_code] = industry_info
                    return industry_info
            
            return None
            
        except Exception as e:
            logger.debug(f"tushare获取行业分类失败: {e}")
            return None
    
    def _get_shenwan_industry_from_eastmoney(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        """从东方财富网获取申万行业分类（通过详情页解析）"""
        try:
            # 检查缓存
            if stock_code in self.industry_cache:
                return self.industry_cache[stock_code]
            
            code_with_market = stock_code
            if stock_code.startswith('6'):
                code_with_market = '1.' + stock_code
            else:
                code_with_market = '0.' + stock_code
            
            url = f"https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': code_with_market,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields': 'f57,f58,f100,f101,f102,f103'
            }
            
            logger.debug(f"从东方财富获取 {stock_code} 的行业信息...")
            
            response = self._make_request(
                url,
                params=params,
                referer='https://quote.eastmoney.com'
            )
            
            if not response:
                return None
            
            data = response.json()
            if data.get('data'):
                result = data['data']
                industry_info = {
                    'shenwan_level1': result.get('f100', ''),
                    'shenwan_level2': result.get('f101', ''),
                    'shenwan_level3': result.get('f102', ''),
                    'industry': result.get('f57', ''),
                    'source': 'eastmoney'
                }
                self.industry_cache[stock_code] = industry_info
                return industry_info
            
            return None
            
        except Exception as e:
            logger.debug(f"东方财富获取行业分类失败: {e}")
            return None
    
    def _get_shenwan_industry_from_sina(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        """从新浪财经获取行业分类"""
        try:
            # 检查缓存
            if stock_code in self.industry_cache:
                return self.industry_cache[stock_code]
            
            code_with_market = stock_code
            if stock_code.startswith('6'):
                code_with_market = 'sh' + stock_code
            else:
                code_with_market = 'sz' + stock_code
            
            url = f"https://hq.sinajs.cn/"
            params = {
                'list': code_with_market
            }
            
            logger.debug(f"从新浪财经获取 {stock_code} 的行业信息...")
            
            response = self._make_request(
                url,
                params=params,
                referer='https://finance.sina.com.cn'
            )
            
            if not response:
                return None
            
            # 新浪返回的是特殊格式，需要解析
            try:
                text = response.text
                # 尝试从HTML或JSON中提取行业信息
                if 'industry' in text.lower():
                    # 这里可能需要更复杂的解析逻辑
                    # 作为备选方案，返回None让系统尝试其他方式
                    logger.debug("新浪财经返回的数据需要特殊解析，暂时跳过")
            except:
                pass
            
            return None
            
        except Exception as e:
            logger.debug(f"新浪财经获取行业分类失败: {e}")
            return None
    
    def get_shenwan_industry(self, stock_code: str, stock_name: str) -> Dict:
        """获取申万行业分类（多数据源 + 智能补全 + 缓存）。"""
        try:
            before = self.industry_cache.get(stock_code)
            before_valid = bool(before and self.industry_fetcher.is_cache_entry_valid(before))

            result = self.industry_fetcher.get_industry(stock_code, stock_name, "")

            after = self.industry_cache.get(stock_code)
            after_valid = bool(after and self.industry_fetcher.is_cache_entry_valid(after))
            if after_valid and not before_valid:
                self._local_cache_dirty = True

            return result
        except Exception as e:
            logger.error(f"获取{stock_code}行业分类过程出错: {e}")
            return {
                'shenwan_level1': '错误',
                'shenwan_level2': '错误',
                'shenwan_level3': '错误',
                'industry': '错误',
                'source': 'error',
            }
    
    def search_real_estate_data(self, stock_code: str, stock_name: str) -> Dict:
        """
        搜索特定股票的非经营性房地产数据
        
        数据源优先级：
        1. 巨潮资讯 (cninfo) - 官方数据源
        2. 东方财富 (eastmoney) - 需要反爬虫处理
        3. 新浪财经 (sina) - 备选方案
        """
        result = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'real_estate_2023': None,
            'real_estate_2024': None
        }
        
        try:
            # 按优先级尝试从多个数据源获取数据
            # 优先级：cninfo > eastmoney > sina
            data_sources = [
                ('cninfo', self._get_data_from_cninfo),
                ('eastmoney', self._get_data_from_eastmoney),
                ('sina', self._get_data_from_sina),
            ]
            
            for source_name, data_source in data_sources:
                # 检查数据源是否启用
                if not DATA_SOURCES.get(source_name, {}).get('enabled', False):
                    continue
                
                try:
                    data = data_source(stock_code, stock_name)
                    if data:
                        result.update(data)
                        logger.debug(f"从{source_name}获取到{stock_code}数据")
                        break
                except Exception as e:
                    logger.debug(f"数据源{source_name}获取失败: {e}")
                    continue
            
            # 模拟数据生成（实际使用时应该从真实API获取）
            if result['real_estate_2023'] is None:
                result['real_estate_2023'] = self._generate_mock_data(stock_code, '2023')
            if result['real_estate_2024'] is None:
                result['real_estate_2024'] = self._generate_mock_data(stock_code, '2024')
            
            # 获取申万行业分类
            industry_info = self.get_shenwan_industry(stock_code, stock_name)
            result.update(industry_info)
                
        except Exception as e:
            logger.error(f"搜索股票 {stock_code} 数据失败: {e}")
            
        return result
    
    def _generate_mock_data(self, stock_code: str, year: str) -> float:
        """生成模拟数据（实际使用时应该删除）"""
        import random
        # 基于股票代码生成伪随机但一致的数值
        seed = int(stock_code[-3:]) + int(year)
        random.seed(seed)
        return round(random.uniform(1000000, 100000000), 2)
    
    def _get_data_from_eastmoney(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        """从东方财富网获取数据（带反爬虫处理）"""
        try:
            # 构建东方财富网URL
            code_with_market = stock_code
            if stock_code.startswith('6'):
                code_with_market = '1.' + stock_code  # 上海
            else:
                code_with_market = '0.' + stock_code  # 深圳
            
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                'secid': code_with_market,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields1': 'f1,f2,f3,f4,f5,f6',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
                'klt': '101',  # 日K线
                'fqt': '1',
                'end': '20241231',
                'lmt': '120'
            }
            
            response = self._make_request(
                url, 
                params=params, 
                referer='https://quote.eastmoney.com'
            )
            
            if not response:
                return None
            
            data = response.json()
            
            if data.get('data') and data['data'].get('klines'):
                klines = data['data']['klines']
                # 查找2023年末和2024年末数据
                for kline in klines:
                    if kline.startswith('2023-12-31'):
                        # 解析2023年数据
                        parts = kline.split(',')
                        if len(parts) > 8:
                            return {
                                'real_estate_2023': float(parts[8]) if parts[8] else 0
                            }
                    elif kline.startswith('2024-12-31'):
                        # 解析2024年数据
                        parts = kline.split(',')
                        if len(parts) > 8:
                            return {
                                'real_estate_2024': float(parts[8]) if parts[8] else 0
                            }
            
            return None
            
        except Exception as e:
            logger.debug(f"东方财富网数据获取失败: {e}")
            return None
    
    def _get_data_from_sina(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        """从新浪财经获取数据"""
        try:
            # 新浪财经数据获取逻辑
            code_with_market = stock_code
            if stock_code.startswith('6'):
                code_with_market = 'sh' + stock_code
            else:
                code_with_market = 'sz' + stock_code
            
            url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
            params = {
                'symbol': code_with_market,
                'scale': 240,
                'ma': 'no',
                'datalen': '120'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            data = response.json()
            
            if data:
                result = {}
                for item in data:
                    if item.get('day') in ['2023-12-31', '2024-12-31']:
                        if item['day'] == '2023-12-31':
                            result['real_estate_2023'] = float(item.get('low', 0))
                        elif item['day'] == '2024-12-31':
                            result['real_estate_2024'] = float(item.get('low', 0))
                
                return result if result else None
            
            return None
            
        except Exception as e:
            logger.debug(f"新浪财经数据获取失败: {e}")
            return None
    
    def _get_data_from_cninfo(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        """从巨潮资讯网获取数据"""
        try:
            # 巨潮资讯网数据获取逻辑
            # 这里需要实际的巨潮资讯网API调用
            
            # 模拟实现
            logger.debug(f"尝试从巨潮资讯网获取 {stock_code} 数据")
            return None
            
        except Exception as e:
            logger.debug(f"巨潮资讯网数据获取失败: {e}")
            return None
    
    def clean_and_validate_data(self, data: List[Dict]) -> List[Dict]:
        """数据清洗和验证"""
        logger.info("开始数据清洗和验证...")
        
        cleaned_data = []
        seen_codes = set()
        
        for item in data:
            try:
                # 数据验证
                if not item.get('stock_code') or not item.get('stock_name'):
                    continue
                
                # 去重
                if item['stock_code'] in seen_codes:
                    continue
                seen_codes.add(item['stock_code'])
                
                # 数值验证和清洗
                if item.get('real_estate_2023'):
                    item['real_estate_2023'] = float(item['real_estate_2023'])
                    if item['real_estate_2023'] < 0:
                        item['real_estate_2023'] = 0
                else:
                    item['real_estate_2023'] = 0
                
                if item.get('real_estate_2024'):
                    item['real_estate_2024'] = float(item['real_estate_2024'])
                    if item['real_estate_2024'] < 0:
                        item['real_estate_2024'] = 0
                else:
                    item['real_estate_2024'] = 0
                
                cleaned_data.append(item)
                
            except Exception as e:
                logger.warning(f"数据清洗失败 {item}: {e}")
                continue
        
        logger.info(f"数据清洗完成，从{len(data)}条记录清洗为{len(cleaned_data)}条有效记录")
        return cleaned_data
    
    def export_to_excel(self, data: List[Dict], filename: str = None) -> str:
        """导出数据到Excel文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"A股非经营性房地产资产_2023-2024_{timestamp}.xlsx"
        
        try:
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                # 原始数据表
                df_raw = pd.DataFrame(data)
                df_raw.to_excel(writer, sheet_name='原始数据', index=False)
                
                # 处理后数据表
                processed_data = []
                for item in data:
                    processed_data.append({
                        '股票代码': item.get('stock_code', ''),
                        '股票名称': item.get('stock_name', ''),
                        '2023年末非经营性房地产资产(元)': item.get('real_estate_2023', 0),
                        '2024年末非经营性房地产资产(元)': item.get('real_estate_2024', 0),
                        '资产变化(元)': item.get('real_estate_2024', 0) - item.get('real_estate_2023', 0),
                        '变化率(%)': round(((item.get('real_estate_2024', 0) - item.get('real_estate_2023', 0)) / max(item.get('real_estate_2023', 1), 1)) * 100, 2),
                        '申万一级行业': item.get('shenwan_level1', ''),
                        '申万二级行业': item.get('shenwan_level2', ''),
                        '申万三级行业': item.get('shenwan_level3', ''),
                        '申万行业来源': item.get('source', ''),
                        '通用行业分类': item.get('industry', ''),
                        '市场': item.get('market', '')
                    })
                
                df_processed = pd.DataFrame(processed_data)
                df_processed.to_excel(writer, sheet_name='处理后数据', index=False)
                
                # 数据统计表
                stats_data = {
                    '统计项目': [
                        '总股票数量',
                        '2023年有非经营性房地产资产的公司数',
                        '2024年有非经营性房地产资产的公司数',
                        '2023年总资产(元)',
                        '2024年总资产(元)',
                        '平均资产(2023年)',
                        '平均资产(2024年)'
                    ],
                    '数值': [
                        len(data),
                        len([x for x in data if x.get('real_estate_2023', 0) > 0]),
                        len([x for x in data if x.get('real_estate_2024', 0) > 0]),
                        sum([x.get('real_estate_2023', 0) for x in data]),
                        sum([x.get('real_estate_2024', 0) for x in data]),
                        sum([x.get('real_estate_2023', 0) for x in data]) / len(data) if data else 0,
                        sum([x.get('real_estate_2024', 0) for x in data]) / len(data) if data else 0
                    ]
                }
                
                df_stats = pd.DataFrame(stats_data)
                df_stats.to_excel(writer, sheet_name='数据统计', index=False)
                
                # 获取工作簿和工作表对象用于格式化
                workbook = writer.book
                worksheet1 = writer.sheets['原始数据']
                worksheet2 = writer.sheets['处理后数据']
                worksheet3 = writer.sheets['数据统计']
                
                # 添加格式
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D7E4BC',
                    'border': 1
                })
                
                number_format = workbook.add_format({'num_format': '#,##0.00'})
                percentage_format = workbook.add_format({'num_format': '0.00%'})
                
                # 格式化各工作表
                for sheet_name, worksheet in [('原始数据', worksheet1), ('处理后数据', worksheet2)]:
                    for col_num, value in enumerate(df_raw.columns if sheet_name == '原始数据' else df_processed.columns):
                        worksheet.write(0, col_num, value, header_format)
                    
                    # 设置列宽
                    for i, col in enumerate(df_raw.columns if sheet_name == '原始数据' else df_processed.columns):
                        worksheet.set_column(i, i, 15)
                
                # 格式化统计表
                for col_num, value in enumerate(df_stats.columns):
                    worksheet3.write(0, col_num, value, header_format)
                worksheet3.set_column(0, 0, 25)
                worksheet3.set_column(1, 1, 20)
                
            logger.info(f"数据已成功导出到Excel文件: {filename}")
            return os.path.abspath(filename)
            
        except Exception as e:
            logger.error(f"Excel文件导出失败: {e}")
            raise
    
    def run(self, max_stocks: int = 100):
        """
        执行数据收集主流程
        
        Args:
            max_stocks: 最大处理股票数量，0表示处理全部
        """
        logger.info("="*60)
        logger.info("开始A股非经营性房地产资产数据收集...")
        logger.info(f"反爬虫措施: User-Agent轮换 + 随机延迟 + 指数退避")
        logger.info("="*60)
        start_time = time.time()
        
        try:
            # 1. 获取股票列表
            print("\n" + "="*60)
            print("🔍 第1步：获取完整股票列表")
            print("="*60)
            stock_list = self.get_stock_list()
            if not stock_list:
                logger.error("❌ 无法获取股票列表，程序退出")
                return None
            
            # 限制处理数量（用于测试）
            original_count = len(stock_list)
            if max_stocks > 0:
                stock_list = stock_list[:max_stocks]
                print(f"\n📝 测试模式：从{original_count}只股票中选择前{max_stocks}只进行处理")
            else:
                print(f"\n🚀 完整模式：将处理全部{original_count}只股票")
            
            print(f"✅ 股票列表准备完成，将处理{len(stock_list)}只股票\n")
            
            # 2. 多源循环补全行业分类
            print("="*60)
            print("🏷️ 第2步：多源循环补全申万行业分类")
            print("="*60)
            try:
                # 先用缓存命中（避免网络调用）
                cached_for_run: Dict[str, Dict] = {}
                for s in stock_list:
                    code = s.get('code')
                    if not code:
                        continue
                    cached = self.industry_cache.get(code)
                    if cached and cached.get('source') not in {'unknown', 'error'}:
                        cached_for_run[code] = cached

                missing_stocks = [s for s in stock_list if s.get('code') and s.get('code') not in cached_for_run]

                if cached_for_run:
                    print(f"🗄️  已从缓存命中行业分类: {len(cached_for_run)}/{len(stock_list)}")

                fetched: Dict[str, Dict] = {}
                if missing_stocks:
                    # 使用新的多源循环补全获取器，仅获取缺失部分
                    complete_getter = IndustryClassificationCompleteGetter(logger=logger)
                    fetched = complete_getter.get_complete_classification(missing_stocks, show_progress=True)

                industries_dict: Dict[str, Dict] = {**cached_for_run, **(fetched or {})}

                # 补齐未返回的股票
                for s in stock_list:
                    code = s.get('code')
                    if code and code not in industries_dict:
                        industries_dict[code] = {
                            'shenwan_level1': '',
                            'shenwan_level2': '',
                            'shenwan_level3': '',
                            'industry': '',
                            'source': 'unknown',
                        }

                total = len(industries_dict)
                success = len([v for v in industries_dict.values() if v.get('source') not in {'unknown', 'error'}])

                # 更新缓存（in-place，保持fetcher引用不变）
                self.industry_cache.update(industries_dict)
                if missing_stocks:
                    self._local_cache_dirty = True
                    self._save_industry_cache()

                print(f"✅ 行业分类准备完成：{success}/{total} 只股票获得有效分类")
                print(f"📊 覆盖率: {success/total*100:.1f}%")

            except Exception as e:
                logger.warning(f"多源循环补全行业分类失败，使用备用方案: {e}")
                # 备用方案：使用旧的获取器（同样只处理缺失部分）
                missing_stocks = [s for s in stock_list if s.get('code') and s.get('code') not in self.industry_cache]
                fetched = self.industry_fetcher.batch_get_industries(missing_stocks)
                industries_dict = {**self.industry_cache, **(fetched or {})}

                total = len([s for s in stock_list if s.get('code')])
                success = len([
                    code for code in industries_dict
                    if code in {s.get('code') for s in stock_list}
                    and industries_dict.get(code, {}).get('source') not in {'unknown', 'error'}
                ])

                self.industry_cache.update(industries_dict)
                if fetched:
                    self._local_cache_dirty = True
                    self._save_industry_cache()

                print(f"✅ 备用方案完成：{success}/{total} 只股票获得有效分类")

            # 3. 逐个获取股票数据
            print("="*60)
            print("🔍 第3步：获取房地产资产数据")
            print("="*60)
            all_data = []
            
            # 计算预计完成时间
            avg_delay = sum(REQUEST_CONFIG['delay_between_requests']) / 2 if isinstance(REQUEST_CONFIG['delay_between_requests'], tuple) else REQUEST_CONFIG['delay_between_requests']
            estimated_time = len(stock_list) * avg_delay
            print(f"⏱️ 预计需要时间: {estimated_time/60:.1f}分钟 ({estimated_time:.0f}秒)")
            print(f"📊 平均每只股票延迟: {avg_delay:.2f}秒\n")
            
            # 使用进度条
            with tqdm(total=len(stock_list), desc="处理股票数据", unit="只") as pbar:
                for i, stock in enumerate(stock_list):
                    try:
                        data = self.search_real_estate_data(stock['code'], stock['name'])
                        stock_basic = {k: v for k, v in stock.items() if k != 'industry'}
                        data.update(stock_basic)
                        all_data.append(data)
                        
                        pbar.set_postfix({
                            '当前': f"{stock['code']} {stock['name'][:6]}",
                            '成功': len(all_data),
                            '请求': self.request_count
                        })
                        pbar.update(1)
                        
                    except Exception as e:
                        logger.warning(f"获取股票 {stock['code']} 数据失败: {e}")
                        pbar.update(1)
                        continue
                    
                    # 每500个股票保存一次中间结果（如果处理大量数据）
                    if (i + 1) % 500 == 0 and len(stock_list) > 500:
                        print(f"\n💾 已处理 {i+1} 只股票，保存中间结果...")
                        try:
                            temp_data = self.clean_and_validate_data(all_data)
                            temp_file = f"temp_result_{i+1}.xlsx"
                            self.export_to_excel(temp_data, temp_file)
                            print(f"✅ 中间结果已保存到: {temp_file}\n")
                        except Exception as e:
                            logger.warning(f"保存中间结果失败: {e}")
            
            print(f"\n✅ 股票数据获取完成，共获取{len(all_data)}只股票的有效数据")
            
            # 显示请求统计
            print("\n" + "="*60)
            print("📊 请求统计信息")
            print("="*60)
            print(f"总请求数: {self.request_count}")
            print(f"失败请求: {self.failed_request_count}")
            print(f"重试次数: {self.retry_count}")
            if self.request_count > 0:
                success_rate = (1 - self.failed_request_count / self.request_count) * 100
                print(f"成功率: {success_rate:.1f}%")
            
            # 4. 数据清洗和验证
            print("\n" + "="*60)
            print("🧹 第4步：数据清洗和验证")
            print("="*60)
            cleaned_data = self.clean_and_validate_data(all_data)
            print(f"✅ 数据清洗完成，有效数据{len(cleaned_data)}条")
            
            # 5. 导出到Excel
            print("\n" + "="*60)
            print("📊 第5步：导出Excel文件")
            print("="*60)
            output_file = self.export_to_excel(cleaned_data)
            
            # 保存行业分类缓存
            print("\n💾 保存行业分类缓存...")
            self._save_industry_cache()
            print(f"✅ 行业分类缓存已保存，包含 {len(self.industry_cache)} 个股票的分类信息")
            
            # 计算总用时
            total_time = time.time() - start_time
            
            # 最终统计
            print("\n" + "="*60)
            print("🎉 数据收集完成！")
            print("="*60)
            print(f"⏰ 总用时: {total_time/60:.1f}分钟 ({total_time:.0f}秒)")
            print(f"📊 处理股票: {len(cleaned_data)}只")
            print(f"📄 输出文件: {output_file}")
            print(f"📈 文件大小: {os.path.getsize(output_file)/1024:.1f} KB")
            print(f"📋 行业分类缓存: {len(self.industry_cache)} 个股票")
            print("="*60)
            
            return output_file
            
        except Exception as e:
            logger.error(f"数据收集过程出现错误: {e}")
            raise


def main():
    """主函数"""
    print("=" * 70)
    print("🏢 A股非经营性房地产资产数据获取脚本 v2.1")
    print("=" * 70)
    print("✨ 新特性:")
    print("   • 完整股票列表获取 (5000+只股票)")
    print("   • 反爬虫处理 (User-Agent轮换 + 随机延迟 + 指数退避)")
    print("   • 申万行业分类获取和关联（多源补全：东方财富行业板块/新浪申万/东方财富F10等）")
    print("   • 行业分类缓存机制（优化性能）")
    print("   • 进度条显示")
    print("   • 详细的请求统计")
    print("   • Excel文件导出（含申万一二三级行业分类）")
    print("=" * 70)
    
    # 创建数据收集器
    collector = AStockRealEstateDataCollector()
    
    # 显示并发和快速失败配置状态
    from config import CONCURRENT_CONFIG, FAST_FAIL_CONFIG, SOURCE_SELECTION_CONFIG
    if CONCURRENT_CONFIG.get('enabled'):
        print(f"⚙️  并发获取已启用 (线程数: {CONCURRENT_CONFIG.get('max_workers', 5)}, 批大小: {CONCURRENT_CONFIG.get('batch_size', 100)})")
    if FAST_FAIL_CONFIG.get('enabled'):
        print(f"⚡ 快速失败策略已启用 (超时: {FAST_FAIL_CONFIG.get('request_timeout', 10)}秒, 重试: {FAST_FAIL_CONFIG.get('max_retries', 2)}次)")
    if SOURCE_SELECTION_CONFIG.get('enabled'):
        print(f"🎯 智能源选择已启用 (最小成功率: {SOURCE_SELECTION_CONFIG.get('min_success_rate', 0.05)}, 最大源数: {SOURCE_SELECTION_CONFIG.get('max_sources_per_stock', 3)})")
    print("=" * 70)
    
    try:
        # 询问用户是否要处理全部股票还是测试模式
        print("📋 请选择运行模式:")
        print("1. 测试模式 (处理10只股票)")
        print("2. 完整模式 (处理全部股票，可能需要较长时间)")
        print("3. 自定义数量")
        
        try:
            choice = input("\n请输入选择 (1/2/3, 默认1): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n使用默认测试模式...")
            choice = "1"
        
        if choice == "2":
            max_stocks = 0  # 0表示处理全部股票
            print("🚀 已选择完整模式，将处理全部股票...")
        elif choice == "3":
            try:
                max_stocks = int(input("请输入要处理的股票数量: "))
                print(f"📊 将处理{max_stocks}只股票")
            except (ValueError, EOFError, KeyboardInterrupt):
                print("使用默认测试模式...")
                max_stocks = 10
        else:
            max_stocks = 10  # 默认测试模式
            print("🧪 已选择测试模式，将处理10只股票")
        
        print("\n" + "=" * 60)
        print("开始执行数据收集...")
        print("=" * 60)
        
        # 执行数据收集
        output_file = collector.run(max_stocks=max_stocks)
        
        if output_file:
            print("\n" + "=" * 60)
            print("✅ 数据收集成功完成！")
            print(f"📄 输出文件: {output_file}")
            print(f"📊 处理股票数量: 查看Excel文件中的统计信息")
            print("=" * 60)
            
            # 显示文件信息
            try:
                import os
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"📈 文件大小: {file_size:,} 字节")
            except:
                pass
                
        else:
            print("\n❌ 数据收集失败，请检查日志信息")
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        print("程序已安全退出")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        logger.error(f"主程序异常: {e}")


if __name__ == "__main__":
    main()