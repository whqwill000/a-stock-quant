# 核心模块

本目录包含 A 股量化金融平台的核心模块代码。

## 模块结构

```
core/
├── __init__.py           # 包初始化
├── data_fetch/           # 数据获取模块
│   ├── __init__.py
│   ├── akshare_fetcher.py    # AKShare 数据接口
│   ├── tushare_fetcher.py    # Tushare 数据接口
│   └── data_cache.py         # 数据缓存管理
│
├── backtest/             # 回测引擎模块
│   ├── __init__.py
│   ├── engine.py             # 回测主引擎
│   ├── portfolio.py          # 投资组合管理
│   └── metrics.py            # 绩效指标计算
│
├── simulator/            # 交易模拟器模块
│   ├── __init__.py
│   ├── account.py            # 账户管理
│   ├── order.py              # 订单系统
│   ├── matching.py           # 撮合引擎
│   └── risk_control.py       # 风控模块
│
├── analysis/             # 分析模块
│   ├── __init__.py
│   ├── performance.py        # 绩效分析
│   ├── attribution.py        # 收益归因
│   └── risk.py               # 风险分析
│
└── utils/                # 工具模块
    ├── __init__.py
    ├── logger.py             # 日志工具
    ├── config.py             # 配置管理
    └── helpers.py            # 辅助函数
```

## 实现状态

| 模块 | 状态 | 说明 |
|------|------|------|
| data_fetch | 📝 待实现 | 数据获取接口 |
| backtest | 📝 待实现 | 回测引擎 |
| simulator | 📝 待实现 | 交易模拟器 |
| analysis | 📝 待实现 | 分析工具 |
| utils | 📝 待实现 | 工具函数 |

## 设计文档

详细设计请参考：
- [模拟器设计文档](../docs/03-模拟器设计.md)

## 下一步

1. 实现数据获取模块 (AKShare)
2. 实现回测引擎
3. 实现交易模拟器
4. 实现分析模块
5. 编写单元测试
