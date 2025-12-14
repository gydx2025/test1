"""
配置文件
用于设置A股数据收集器的各种参数
"""

# 数据源配置
# 优先级：cninfo(官方，反爬虫温和) > eastmoney(需要严格反爬虫) > sina(备选)
DATA_SOURCES = {
    'cninfo': {
        'enabled': True,  # 巨潮资讯网 - 官方数据源，反爬虫相对温和
        'base_url': 'http://www.cninfo.com.cn',
        'timeout': 20,
        'weight': 3  # 优先级权重，数字越大优先级越高
    },
    'eastmoney': {
        'enabled': True,  # 东方财富网 - 需要严格的反爬虫处理
        'base_url': 'https://push2.eastmoney.com',
        'timeout': 30,
        'weight': 2
    },
    'sina': {
        'enabled': True,  # 新浪财经 - 备选方案
        'base_url': 'https://money.finance.sina.com.cn',
        'timeout': 15,
        'weight': 1
    }
}

# 行业分类数据源配置（申万行业分类）
# 说明：不同平台对“行业”口径不同，这里统一输出到 shenwan_level1/2/3 字段，
# 并记录 source 便于追溯。
INDUSTRY_SOURCES = {
    'eastmoney_industry_board': {
        'enabled': True,
        'base_url': 'https://push2.eastmoney.com',
        'timeout': 20,
        'weight': 5,
        'min_batch_size': 300,
    },
    'sina_shenwan': {
        'enabled': True,
        'base_url': 'https://vip.stock.finance.sina.com.cn',
        'timeout': 20,
        'weight': 4,
    },
    'eastmoney_f10': {
        'enabled': True,
        'base_url': 'https://emweb.securities.eastmoney.com',
        'timeout': 20,
        'weight': 3,
    },
    'eastmoney_quote': {
        'enabled': True,
        'base_url': 'https://push2.eastmoney.com',
        'timeout': 20,
        'weight': 2,
    },
    'tencent_quote': {
        'enabled': True,
        'base_url': 'https://qt.gtimg.cn',
        'timeout': 15,
        'weight': 1,
    },
    'netease_f10': {
        'enabled': True,
        'base_url': 'https://quotes.money.163.com',
        'timeout': 15,
        'weight': 0,
    },
    # 旧版数据源（保留配置项以兼容历史文档/代码路径）
    'tushare': {
        'enabled': False,
        'timeout': 15,
        'weight': 0,
    },
    'eastmoney_detailed': {
        'enabled': False,
        'base_url': 'https://quote.eastmoney.com',
        'timeout': 20,
        'weight': 0,
    },
    'sina_industry': {
        'enabled': False,
        'base_url': 'https://money.finance.sina.com.cn',
        'timeout': 15,
        'weight': 0,
    },
}

# 请求配置 [优化版本]
REQUEST_CONFIG = {
    'delay_between_requests': (0.2, 0.5),  # 请求间隔范围(秒) - 随机延迟 [优化：降低延迟]
    'max_retries': 2,  # 最大重试次数 [优化：从5降到2]
    'retry_delay': 1,  # 重试基础间隔(秒) - 使用指数退避 [优化：从2降到1]
    'timeout': 10,  # 默认超时时间 [优化：从30降到10]
    'use_exponential_backoff': True,  # 是否使用指数退避算法
    'backoff_factor': 2,  # 指数退避因子
}

# 并发获取配置 [NEW]
CONCURRENT_CONFIG = {
    'enabled': True,  # 是否启用并发获取
    'max_workers': 5,  # 并发线程数（建议5-10，平衡速度和反爬虫）
    'batch_size': 100,  # 每批处理的股票数
    'use_fast_fail': True,  # 是否使用快速失败策略
    'consecutive_fail_threshold': 3,  # 连续失败次数达到此值后跳过
}

# 快速失败策略配置 [NEW]
FAST_FAIL_CONFIG = {
    'enabled': True,  # 启用快速失败策略
    'request_timeout': 10,  # 单个请求超时（秒）
    'max_retries': 2,  # 最大重试次数
    'retry_delays': [1, 2],  # 重试延迟，总计3秒
    'min_success_rate': 0.05,  # 最小成功率阈值，低于此的源放弃处理
}

# 反爬虫配置 - User-Agent轮换池
USER_AGENT_POOL = [
    # Chrome on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    # Chrome on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    # Firefox on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    # Firefox on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    # Edge on Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
    # Safari on macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
]

# HTTP请求头配置
HEADERS_CONFIG = {
    'Accept': 'application/json, text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}

# 代理配置（可选）
PROXY_CONFIG = {
    'enabled': False,  # 是否启用代理
    'proxies': [
        # {'http': 'http://proxy1:port', 'https': 'https://proxy1:port'},
        # {'http': 'http://proxy2:port', 'https': 'https://proxy2:port'},
    ],
    'rotate_on_failure': True,  # 失败时是否轮换代理
}

# 输出配置
OUTPUT_CONFIG = {
    'default_filename': 'A股非经营性房地产资产_2023-2024.xlsx',
    'include_raw_data': True,  # 是否包含原始数据表
    'include_processed_data': True,  # 是否包含处理后数据表
    'include_statistics': True,  # 是否包含统计信息表
    'number_format': '#,##0.00',  # 数字格式
    'percentage_format': '0.00%'  # 百分比格式
}

# 数据清洗配置
DATA_CLEANING_CONFIG = {
    'remove_duplicates': True,  # 是否去重
    'handle_negative_values': True,  # 是否处理负值
    'negative_to_zero': True,  # 负值是否转为0
    'handle_missing_values': True,  # 是否处理缺失值
    'missing_to_zero': True,  # 缺失值是否转为0
    'validate_stock_codes': True,  # 是否验证股票代码格式
    'max_real_estate_value': 1e12,  # 最大资产值(1万亿)
    'min_real_estate_value': 0  # 最小资产值
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_logging': False,  # 是否启用文件日志
    'log_file': 'astock_collector.log',
    'max_file_size': 10 * 1024 * 1024,  # 最大日志文件大小(10MB)
    'backup_count': 5  # 日志文件备份数量
}

# 缓存配置
CACHE_CONFIG = {
    'enabled': True,  # 是否启用缓存
    'cache_dir': './cache',
    'cache_duration': 3600,  # 缓存时间(秒)
    'clean_on_start': False  # 启动时是否清理缓存
}

# 行业分类缓存配置
INDUSTRY_CACHE_CONFIG = {
    'enabled': True,  # 是否启用行业分类缓存
    'cache_dir': './cache/industry',
    'cache_file': 'shenwan_industry_mapping.pkl',  # 行业分类映射缓存文件
    'cache_duration': 7 * 24 * 3600,  # 缓存时间(秒，默认7天)
}

# ═══════════════════════════════════════════════════════
# 行业分类获取超时配置 [优化版本]
# ═══════════════════════════════════════════════════════
REQUEST_TIMEOUT = 10          # 单个HTTP请求超时 (秒) [优化：从20降到10]
API_SOURCE_TIMEOUT = 60       # 单个源的总超时 (秒) [优化：从300降到60]
MAX_RETRIES = 2               # 单个源内的最大重试次数 [优化：从3降到2]
BATCH_SIZE = 100              # 每批处理的股票数
PROGRESS_INTERVAL = 100       # 每处理100只股票显示一次进度

# 循环获取配置
MAX_RETRY_ROUNDS = 8          # 最多尝试8个源（等于源的个数）
RETRY_WAIT_TIME = 1           # 源之间的等待时间 (秒)

# 完整行业分类数据源配置（8个分层数据源）
COMPLETE_INDUSTRY_SOURCES = {
    # 第一级 - 高速源 (响应快，覆盖完整)
    'eastmoney_quote': {
        'enabled': True,
        'name': '东方财富行情',
        'priority': 1,
        'timeout': 15,
        'retry_count': 2,
        'description': '东方财富实时行情接口，快速可靠'
    },
    'eastmoney_f10': {
        'enabled': True,
        'name': '东方财富F10',
        'priority': 2,
        'timeout': 20,
        'retry_count': 3,
        'description': '东方财富F10页面，行业分类权威'
    },
    
    # 第二级 - 标准源 (官方或权威，覆盖全)
    'sina_shenwan': {
        'enabled': True,
        'name': '新浪财经',
        'priority': 3,
        'timeout': 20,
        'retry_count': 3,
        'description': '新浪财经申万行业板块，备用爬取源'
    },
    'akshare': {
        'enabled': True,
        'name': 'AkShare',
        'priority': 4,
        'timeout': 30,
        'retry_count': 2,
        'description': 'AkShare股票信息接口，快速可靠'
    },
    
    # 第三级 - 扩展源 (补全覆盖)
    'tencent_quote': {
        'enabled': True,
        'name': '腾讯财经',
        'priority': 5,
        'timeout': 15,
        'retry_count': 2,
        'description': '腾讯财经行业分类字段'
    },
    'netease_f10': {
        'enabled': True,
        'name': '网易财经',
        'priority': 6,
        'timeout': 15,
        'retry_count': 2,
        'description': '网易财经行业分类字段'
    },
    
    # 第四级 - 深度源 (最后补全)
    'cninfo': {
        'enabled': True,
        'name': '巨潮资讯',
        'priority': 7,
        'timeout': 30,
        'retry_count': 1,
        'description': '巨潮资讯上市公司分类'
    },
    'cache_mapping': {
        'enabled': True,
        'name': '缓存库映射',
        'priority': 8,
        'timeout': 5,
        'retry_count': 1,
        'description': '已知历史映射和手动映射'
    }
}

# 测试配置
TEST_CONFIG = {
    'max_stocks_for_test': 10,  # 测试时最大股票数量
    'mock_data': True,  # 是否使用模拟数据
    'skip_network_requests': False,  # 是否跳过网络请求
    'save_intermediate_results': True  # 是否保存中间结果
}