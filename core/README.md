# 核心模块

本目录包含 A 股量化金融平台的核心模块代码。

## 模块结构

```
core/
├── __init__.py           # 包初始化
├── data_fetch/           # 数据获取模块 ✅
│   ├── __init__.py
│   ├── akshare_fetcher.py    # AKShare 数据接口 ✅
│   ├── tushare_fetcher.py    # Tushare 数据接口 ✅
│   └── data_cache.py         # 数据缓存管理 ✅
│
├── backtest/             # 回测引擎模块 ✅
│   ├── __init__.py
│   ├── engine.py             # 回测主引擎 ✅
│   └── metrics.py            # 绩效指标计算 ✅
│
├── simulator/            # 交易模拟器模块 ✅
│   ├── __init__.py
│   ├── account.py            # 账户管理（支持T+1）✅
│   ├── order.py              # 订单系统 ✅
│   ├── matching.py           # 撮合引擎（涨跌停规则）✅
│   └── risk_control.py       # 风控模块 ✅
│
├── analysis/             # 分析模块 ✅
│   ├── __init__.py
│   ├── performance.py        # 绩效分析 ✅
│   └── risk.py               # 风险分析 ✅
│
└── utils/                # 工具模块 ✅
    ├── __init__.py
    ├── logger.py             # 日志工具 ✅
    ├── config.py             # 配置管理 ✅
    └── helpers.py            # 辅助函数 ✅
```

## 实现状态

| 模块 | 状态 | 说明 |
|------|------|------|
| data_fetch | ✅ 已完成 | AKShare/Tushare 数据接口、数据缓存 |
| backtest | ✅ 已完成 | 事件驱动回测引擎、绩效指标计算 |
| simulator | ✅ 已完成 | 账户管理、订单系统、撮合引擎、风控 |
| analysis | ✅ 已完成 | 绩效分析、风险分析 |
| utils | ✅ 已完成 | 日志、配置、辅助函数 |

## 核心功能

### 数据获取模块 (data_fetch)
- **AKShare 接口**: 免费 A 股数据，支持行情、财务、资金流等
- **Tushare 接口**: 专业数据源，需要 token
- **数据缓存**: 本地缓存减少网络请求

### 回测引擎 (backtest)
- **事件驱动架构**: 按时间顺序处理数据
- **完整交易成本**: 佣金万2.5、印花税0.05%、过户费
- **绩效指标**: 年化收益、夏普比率、最大回撤等

### 交易模拟器 (simulator)
- **T+1 规则**: 当日买入次日才能卖出
- **涨跌停限制**: 涨跌停价格限制
- **风控管理**: 仓位控制、止损止盈

### 分析模块 (analysis)
- **绩效分析**: 收益分析、风险分析
- **风险指标**: VaR、波动率、回撤分析

## 设计文档

详细设计请参考：
- [模拟器设计文档](../docs/03-模拟器设计.md)
- [策略详解](../docs/02-策略详解.md)

## 使用示例

```python
from core.data_fetch.akshare_fetcher import AKShareFetcher
from core.backtest.engine import BacktestEngine
from strategies.trend_following.trend_strategy import TrendFollowingStrategy

# 获取数据
fetcher = AKShareFetcher()
data = fetcher.get_stock_daily("000001.SZ", "2023-01-01", "2023-12-31")

# 创建策略
strategy = TrendFollowingStrategy()

# 运行回测
engine = BacktestEngine(initial_capital=1000000)
result = engine.run(data, strategy)
```
