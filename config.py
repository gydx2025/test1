"""
配置文件
用于设置A股数据收集器的各种参数
"""

# 数据源配置
DATA_SOURCES = {
    'eastmoney': {
        'enabled': True,
        'base_url': 'https://push2.eastmoney.com',
        'timeout': 30,
        'weight': 1  # 优先级权重，数字越大优先级越高
    },
    'sina': {
        'enabled': True,
        'base_url': 'https://money.finance.sina.com.cn',
        'timeout': 15,
        'weight': 2
    },
    'cninfo': {
        'enabled': False,  # 巨潮资讯网暂时禁用，因为需要更复杂的API调用
        'base_url': 'http://www.cninfo.com.cn',
        'timeout': 20,
        'weight': 3
    }
}

# 请求配置
REQUEST_CONFIG = {
    'delay_between_requests': 0.5,  # 请求间隔(秒)
    'max_retries': 3,  # 最大重试次数
    'retry_delay': 2,  # 重试间隔(秒)
    'timeout': 30,  # 默认超时时间
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
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