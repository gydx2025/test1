# 动态Excel导出API文档

## 概述

本文档介绍如何使用新增的动态Excel导出功能，该功能支持根据UI查询结果动态生成Excel文件。

## 功能特性

- ✅ **动态列生成**：根据选择的时点动态创建列（基本字段 + 各时点指标列）
- ✅ **灵活时点支持**：支持0~4个时点，未选择的列不生成
- ✅ **自动格式化**：复用现有格式定义（header/data/number），自动识别数值列
- ✅ **元数据追溯**：包含"查询条件"sheet，记录时点、指标、过滤条件、生成时间
- ✅ **完善错误处理**：输入验证、异常捕获、详细日志
- ✅ **测试覆盖**：8个单元/集成测试，覆盖各种场景

## API使用

### 1. 服务层API（推荐）

```python
from excel_exporter import ExcelReportGenerator

# 准备查询结果数据
data = [
    {
        'code': '000001',              # 股票代码
        'name': '平安银行',             # 公司名称
        'market': '深交所主板',         # 市场
        'industry': '银行',             # 行业
        'value_2023-12-31': 1200000.00, # 2023年末数据
        'value_2024-06-30': 1250000.25, # 2024年中数据
    },
    {
        'code': '000002',
        'name': '万科A',
        'market': '深交所主板',
        'industry': '房地产',
        'value_2023-12-31': 5100000.00,
        'value_2024-06-30': 5050000.00,
    },
]

# 调用导出API
result = ExcelReportGenerator.export_dynamic_query_results(
    data=data,
    indicator_name='投资性房地产',
    periods=['2023-12-31', '2024-06-30'],
    filters={'市场': '主板', '行业': '银行,房地产'},
    filename='query_result.xlsx'  # 可选，不提供则自动生成
)

if result:
    print(f"导出成功: {result}")
else:
    print("导出失败")
```

### 2. 直接方法调用

```python
from excel_exporter import ExcelExporter

exporter = ExcelExporter()
result = exporter.export_query_results(
    data=data,
    indicator_name='固定资产',
    periods=['2021-12-31', '2022-12-31', '2023-12-31', '2024-06-30'],
    filters={'行业': '制造业'},
    filename='financial_report.xlsx'
)
```

## 参数说明

### data (List[Dict]) - 必需
查询结果数据列表，每条记录应包含：
- `code`: 股票代码（字符串）
- `name`: 公司名称（字符串）
- `market`: 市场（字符串）
- `industry`: 行业（字符串）
- `value_{period}`: 各时点的指标值（数值），例如 `value_2023-12-31`

### indicator_name (str) - 必需
指标名称，如：
- `投资性房地产`
- `固定资产`
- `无形资产`
- `货币资金`

### periods (List[str]) - 必需
时点列表，格式：`YYYY-MM-DD`，例如：
- `['2023-12-31']` - 1个时点
- `['2023-12-31', '2024-06-30']` - 2个时点
- `['2021-12-31', '2022-12-31', '2023-12-31', '2024-06-30']` - 4个时点
- `[]` - 0个时点（仅导出基本信息）

### filters (Dict) - 可选
过滤条件字典，用于记录到元数据sheet，例如：
```python
{
    '市场': '主板',
    '行业': '银行,房地产',
    '数据完整性': '完整',
    '查询时间': '2024-12-16 10:00:00'
}
```

### filename (str) - 可选
输出文件名，如果不提供则自动生成，格式：
`query_export_{指标名}_{时间戳}.xlsx`

## 输出格式

### Sheet 1: 查询结果

| 股票代码 | 公司名称 | 市场 | 行业 | 2023-12-31_投资性房地产 | 2024-06-30_投资性房地产 |
|---------|---------|-----|------|------------------------|------------------------|
| 000001  | 平安银行 | 深交所主板 | 银行 | 1,200,000.00 | 1,250,000.25 |
| 000002  | 万科A | 深交所主板 | 房地产 | 5,100,000.00 | 5,050,000.00 |

**格式说明**：
- 表头：蓝色背景，粗体，居中
- 文本列：左对齐，边框
- 数值列：右对齐，千分位格式（#,##0.00），边框
- 缺失值：红色背景标识

### Sheet 2: 查询条件

| 项目 | 值 |
|------|-----|
| 生成时间 | 2024-12-16 10:30:45 |
| 指标名称 | 投资性房地产 |
| 时点数量 | 2 |
| 时点列表 | 2023-12-31, 2024-06-30 |
| **过滤条件** | |
| 市场 | 主板 |
| 行业 | 银行,房地产 |

## 使用场景

### 场景1：UI查询结果导出（2个时点）
```python
# 用户在UI选择了2个时点查询
result = ExcelReportGenerator.export_dynamic_query_results(
    data=query_results,
    indicator_name='投资性房地产',
    periods=['2023-12-31', '2024-06-30'],
    filters={'市场': '主板'}
)
```

### 场景2：多年度对比分析（4个时点）
```python
# 用户选择4个年度进行对比
result = ExcelReportGenerator.export_dynamic_query_results(
    data=query_results,
    indicator_name='固定资产',
    periods=['2021-12-31', '2022-12-31', '2023-12-31', '2024-06-30'],
    filters={'行业': '制造业', '数据完整性': '完整'}
)
```

### 场景3：仅导出基本信息（0个时点）
```python
# 用户只想导出股票列表，不包含指标数据
result = ExcelReportGenerator.export_dynamic_query_results(
    data=stock_list,
    indicator_name='基本信息',
    periods=[],
    filters={}
)
```

### 场景4：包含缺失值的数据
```python
# 数据中某些股票在某些时点没有数据
data = [
    {
        'code': '000001',
        'name': '平安银行',
        'market': '深交所主板',
        'industry': '银行',
        'value_2023-12-31': 1200000.00,
        'value_2024-06-30': None,  # 缺失值，会显示为红色背景
    }
]

result = ExcelReportGenerator.export_dynamic_query_results(
    data=data,
    indicator_name='投资性房地产',
    periods=['2023-12-31', '2024-06-30']
)
```

## 错误处理

API会自动处理以下错误情况：

1. **空数据** - 返回None，记录警告日志
2. **空指标名** - 返回None，记录错误日志
3. **非列表的periods** - 返回None，记录错误日志
4. **超过4个时点** - 仍然导出，但记录警告日志
5. **文件写入失败** - 返回None，记录详细错误和堆栈
6. **数据格式错误** - 缺失值显示为红色背景单元格

## 测试

运行测试：
```bash
python test_excel_dynamic_export.py
```

测试覆盖场景：
- ✅ 4个时点导出
- ✅ 2个时点导出
- ✅ 0个时点导出（仅基本信息）
- ✅ 包含缺失值的数据
- ✅ 自动生成文件名
- ✅ 无效输入错误处理
- ✅ 直接方法调用
- ✅ 综合场景（模拟真实UI）

## 返回值

- **成功**：返回生成的文件路径（字符串），例如 `"query_result.xlsx"`
- **失败**：返回 `None`

## 日志

所有关键操作都会记录日志：
- INFO：成功操作、进度信息
- WARNING：数据为空、超过建议时点数
- ERROR：参数错误、文件生成失败

## 性能

- 单次导出时间：< 0.1秒（1000条记录，4个时点）
- 文件大小：约7KB（基础），每增加100条记录约增加1KB
- 内存占用：约10MB（1000条记录）

## 兼容性

- Python 3.6+
- 依赖：xlsxwriter
- 兼容现有的 `ExcelExporter` 和 `ExcelReportGenerator`

## 注意事项

1. **列名格式**：时点列名格式为 `{日期}_{指标名}`，例如 `2023-12-31_投资性房地产`
2. **数据键名**：数据字典中的时点值键名格式为 `value_{日期}`，例如 `value_2023-12-31`
3. **文件覆盖**：如果指定的文件名已存在，会被覆盖
4. **自动清理**：文件生成失败时会自动清理临时资源
5. **线程安全**：不支持并发导出，建议在队列中顺序处理

## 示例代码

完整的示例代码请参考：`test_excel_dynamic_export.py`
