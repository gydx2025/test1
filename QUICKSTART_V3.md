# A股数据采集系统 v3.0 - 快速开始指南

## 🚀 一分钟快速开始

### 方式A：图形界面（最简单，推荐） 🖥️

```bash
# 1. 进入项目目录
cd /home/engine/project

# 2. 启动图形界面
chmod +x run_gui.sh
./run_gui.sh

# 3. 在GUI中操作
# - 选择采集模式（测试/完整/自定义）
# - 配置查询参数（可选）
# - 点击"开始采集"按钮
# - 采集完成后点击"导出Excel"

# 4. 获得Excel文件
# 文件位置：GUI中显示的导出路径
```

### 方式B：命令行界面（适合自动化）

```bash
# 1. 进入项目目录
cd /home/engine/project

# 2. 运行脚本
python astock_real_estate_collector.py

# 3. 选择选项
# 当提示时选择：2（完整模式）

# 4. 等待完成
# 预计时间：1.5-2小时

# 5. 获得Excel文件
# 文件位置：当前目录下的 A股非经营性房地产资产_*.xlsx
```

## 🖥️ 图形界面 (GUI) 使用指南

### 启动图形界面

```bash
# 方法1：使用启动脚本（推荐）
chmod +x run_gui.sh
./run_gui.sh

# 方法2：直接运行
python3 astock_real_estate_collector_gui.py
```

### GUI 五大核心功能

#### 1️⃣ 数据采集配置
- **采集模式选择**：测试模式（10只）/ 完整模式（全部）/ 自定义数量
- **数据源配置**：选择优先使用的数据源（巨潮、东财、同花顺等）
- **并发设置**：配置线程数和批处理大小（默认4线程）
- **重试策略**：设置最大重试次数和超时时间

#### 2️⃣ 高级查询参数
- **时点选择** 📅
  - 仅2023年末数据
  - 仅2024年末数据  
  - 两个时点对比（默认）
  
- **指标校验** ✅
  - 启用数据范围检查（确保数值合理性）
  - 启用格式验证（股票代码、公司名称格式）
  - 启用完整性检查（必填字段验证）
  
- **股票/市场过滤** 🔍
  - 按股票代码筛选（如：600000-600999）
  - 按公司名称关键词筛选
  - 按市场筛选：沪市主板、深市主板、创业板、科创板、北交所
  - 按行业筛选：申万一级/二级/三级行业分类

#### 3️⃣ 实时进度监控
- **进度可视化**：实时进度条显示采集百分比
- **详细统计**：已处理/成功/失败数量实时更新
- **日志输出**：滚动日志窗口显示详细操作记录
- **时间估算**：动态显示预计剩余时间
- **可中断操作**：支持随时暂停或停止采集

#### 4️⃣ 数据预览与验证
- **表格预览**：采集完成后自动显示数据表格
- **质量评分**：显示数据质量等级（A+、A、B+、B、C、D）
- **缺失数据高亮**：红色标注缺失或异常数据
- **统计信息**：显示总数、覆盖率、完整度等指标
- **数据筛选**：支持在预览表格中搜索和过滤

#### 5️⃣ 灵活导出选项
- **格式选择**：Excel（推荐）/ CSV / JSON
- **字段自定义**：勾选需要导出的字段
- **文件命名**：自定义文件名或使用默认时间戳
- **导出范围**：全部数据 / 仅筛选结果 / 分表导出
- **导出确认**：弹窗提示导出成功及文件路径

### GUI 截图说明（功能描述）

虽然此处未提供实际截图，但 GUI 界面主要包含以下区域：

- **顶部菜单栏**：文件、编辑、视图、帮助
- **左侧配置面板**：采集模式、查询参数、过滤条件
- **中部主工作区**：进度监控、日志输出、数据预览（多标签页切换）
- **右侧统计面板**：实时统计、质量评分、数据概览
- **底部操作栏**：开始采集、暂停/继续、停止、导出等按钮

## 📋 三种运行模式（CLI）

### 模式1：测试模式（10只股票）
```bash
python astock_real_estate_collector.py
# 选择：1
# 预计时间：1-2分钟
# 用途：快速验证系统是否正常
```

### 模式2：完整模式（全部股票）
```bash
python astock_real_estate_collector.py
# 选择：2
# 预计时间：1.5-2小时
# 用途：生产环境完整数据采集
```

### 模式3：自定义数量
```bash
python astock_real_estate_collector.py
# 选择：3
# 输入：要处理的股票数（如：100）
# 预计时间：根据数量而定
# 用途：中等规模数据采集
```

## 📊 系统特性

### ✅ v3.0新增功能

1. **数据验证** - 3层验证机制确保数据正确
2. **数据清洗** - 自动清洗和标准化
3. **本地存储** - SQLite数据库 + CSV备份
4. **质量评分** - A+到D的6级评分系统
5. **断点续传** - 支持中断后继续运行
6. **标准Excel** - 5个专业工作表输出
7. **自动监控** - 实时质量监控告警

### 🔄 多源自动转移

系统拥有7+个数据源，单一源失败自动转移：

```
优先级顺序：
股票列表：巨潮 > 同花顺 > 新浪 > AkShare > 本地
行业分类：新浪 > 东方财富 > 腾讯 > 同花顺 > 其他
财务数据：巨潮 > 东方财富 > 同花顺 > 新浪 > 其他
```

### 🛡️ 反爬虫能力

- ✅ User-Agent自动轮换（20+浏览器标识）
- ✅ 随机请求延迟（0.5-3秒）
- ✅ 指数退避重试（最多5次）
- ✅ 完整HTTP请求头
- ✅ 代理IP支持（可选）
- ✅ 429/403自动处理

## 📁 输出文件说明

### Excel文件包含内容

#### 工作表1：基础信息
```
列：股票代码、公司名称、市场、上市日期、数据源
行：5434+只股票
```

#### 工作表2：行业分类
```
列：股票代码、一级行业、二级行业、三级行业、数据源
行：所有有行业分类的股票
```

#### 工作表3：财务数据
```
列：代码、名称、一级行业、2023年资产、2024年资产
行：所有有财务数据的股票
格式：千位分隔、缺失数据用红色高亮
```

#### 工作表4：汇总统计
```
内容：
- 总公司数
- 行业分类覆盖数
- 2023年数据覆盖数
- 2024年数据覆盖数
- 各项完整度百分比
- 数据质量评分（A+ ~ D）
```

#### 工作表5：元数据
```
内容：
- 采集日期和时间
- 版本号
- 数据来源
- 处理时长
- 备注说明
```

## 🎯 使用场景

### 场景1：数据分析师
```bash
# 快速获取最新数据
python astock_real_estate_collector.py
# 选择2 - 完整模式
# 等待完成后直接在Excel中分析
```

### 场景2：系统集成
```python
# 在代码中调用
from astock_real_estate_collector import AStockRealEstateDataCollector

collector = AStockRealEstateDataCollector()
output_file = collector.run(max_stocks=0)
print(f"数据已保存至: {output_file}")
```

### 场景3：定期自动采集
```bash
# 每天凌晨运行
0 1 * * * cd /path/to/project && python astock_real_estate_collector.py << EOF
2
EOF
```

## ⚙️ 配置调整

### 如果遇到网络问题

编辑 `config.py`：

```python
# 增加延迟
REQUEST_CONFIG['delay_between_requests'] = (2.0, 5.0)

# 增加重试次数
REQUEST_CONFIG['max_retries'] = 10

# 使用代理
PROXY_CONFIG = {
    'enabled': True,
    'proxies': ['http://proxy:8080'],
    'rotate_on_failure': True,
}
```

### 如果内存不足

```python
# 在 astock_real_estate_collector.py 中调整
# 批处理大小（每批处理的股票数）
BATCH_SIZE = 50  # 默认100，减小此值以降低内存占用
```

### 如果想跳过某个数据源

```python
# 编辑 config.py
DATA_SOURCES['eastmoney']['enabled'] = False  # 跳过东方财富
```

## 📊 预期结果

### 数据完整性指标

```
股票总数：5434+ 只（99%+ 覆盖）
行业分类覆盖：95%+
2023年财务数据：90%+
2024年财务数据：90%+
综合质量评分：A+ (95分以上)
```

### 时间指标

```
完整模式处理时间：1.5-2小时
Excel文件生成：< 1分钟
总运行时间：1.5-2.5小时
```

## 🔍 查看进度和日志

### 实时进度显示

运行时会看到进度条：

```
获取股票列表: ████████████████████ 100% [5434/5434]
处理股票数据: ████████████████████ 100% [5434/5434]
生成行业分类: ████████████████████ 100% [5434/5434]
```

### 查看详细日志

```bash
# 查看最近的日志
tail -f astock_real_estate_collector.log

# 搜索错误信息
grep "ERROR" astock_real_estate_collector.log
```

## ❌ 常见问题解决

### Q1: "No module named 'xxx'"错误

```bash
# 重新安装依赖
pip install -r requirements.txt
```

### Q2: "连接超时"错误

```python
# 编辑config.py增加超时时间
REQUEST_CONFIG['timeout'] = 60  # 默认30秒
```

### Q3: 程序中断后如何恢复？

```python
# 使用断点续传
from checkpoint_manager import CheckpointManager
checkpoint_mgr = CheckpointManager()
progress = checkpoint_mgr.resume_from_checkpoint('stage_name')
```

### Q4: Excel文件很大（>10MB）怎么办？

```python
# 仅输出必要列
# 编辑excel_exporter.py，移除不需要的列
```

### Q5: 如何导入生成的数据到数据库？

```python
import pandas as pd
# 读取Excel
df = pd.read_excel('A股非经营性房地产资产_*.xlsx', sheet_name='财务数据')
# 导入数据库...
```

## 📚 详细文档

完整文档位置：

- **系统指南**: `COMPLETE_SYSTEM_GUIDE.md` - 系统的完整使用说明
- **新增功能**: `VERSION_3_0_FEATURES.md` - 所有新增功能详解
- **实现总结**: `IMPLEMENTATION_COMPLETE.md` - 项目完成情况说明
- **README**: `README.md` - 基本信息和快速开始
- **更新日志**: `CHANGELOG.md` - 版本历史

## 🧪 测试验证

### 快速自检

```bash
# 运行测试脚本验证所有模块
python test_new_modules.py
```

**预期输出**:
```
✅ 通过: 6
❌ 失败: 0
🎉 所有测试通过！
```

## 🎉 立即开始

```bash
# 1. 确保依赖安装
pip install -r requirements.txt

# 2. 运行完整版本
python astock_real_estate_collector.py

# 3. 选择：2（完整模式）

# 4. 耐心等待1.5-2小时

# 5. 获得完整的Excel数据文件！
```

## 💡 技巧和最佳实践

### 1. 定期更新数据
```bash
# 每周更新一次
# 使用增量更新功能，只获取最新变化
```

### 2. 备份重要数据
```python
# 生成本地SQLite数据库备份
db = LocalDatabase()
db.backup_stocks(stocks)
db.backup_industries(industries)
db.backup_financial_data(financial_data)
```

### 3. 监控数据质量
```python
# 查看质量报告
monitor = DataQualityMonitor()
result = monitor.monitor(data_stats)
print(monitor.generate_report(result))
```

### 4. 导入数据到其他系统
```python
# 转换为CSV便于导入
from local_storage import CSVBackupManager
CSVBackupManager.backup_to_csv(data, 'export.csv')
```

## 📞 获取帮助

### 如需帮助

1. **查看文档**: 首先查看相关的 .md 文档
2. **查看日志**: 检查运行日志中的错误信息
3. **运行测试**: 执行 `test_new_modules.py` 验证系统
4. **检查配置**: 确认 `config.py` 中的设置正确

## ✅ 系统要求

- **Python**: 3.8+
- **内存**: 4GB (推荐8GB)
- **磁盘**: 2GB (主要用于缓存和输出)
- **网络**: 稳定的互联网连接
- **操作系统**: Linux/Mac/Windows

## 🎯 下一步

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行测试
python test_new_modules.py

# 3. 启动完整版本
python astock_real_estate_collector.py
# 选择 2 - 完整模式

# 4. 等待完成后获得Excel文件

# 5. 在Excel中进行数据分析
```

---

**版本**: v3.0.0
**最后更新**: 2024年12月
**状态**: ✅ 生产就绪

🎉 **祝您使用愉快！**
