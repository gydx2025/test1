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

# 请求配置
REQUEST_CONFIG = {
    'delay_between_requests': (0.5, 2.0),  # 请求间隔范围(秒) - 随机延迟
    'max_retries': 5,  # 最大重试次数
    'retry_delay': 2,  # 重试基础间隔(秒) - 使用指数退避
    'timeout': 30,  # 默认超时时间
    'use_exponential_backoff': True,  # 是否使用指数退避算法
    'backoff_factor': 2,  # 指数退避因子
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
    'enabled': False,  # 是否启用缓存
    'cache_dir': './cache',
    'cache_duration': 3600,  # 缓存时间(秒)
    'clean_on_start': False  # 启动时是否清理缓存
}

# 测试配置
TEST_CONFIG = {
    'max_stocks_for_test': 10,  # 测试时最大股票数量
    'mock_data': True,  # 是否使用模拟数据
    'skip_network_requests': False,  # 是否跳过网络请求
    'save_intermediate_results': True  # 是否保存中间结果
}