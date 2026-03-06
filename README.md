# A 股量化金融平台

> 一个完整的 A 股量化交易研究与回测平台，包含多种经典量化策略的独立实现

## 📖 项目简介

本项目是一个面向 A 股市场的量化金融平台，提供从理论学习、策略研究、回测验证到模拟交易的完整工作流。项目采用模块化设计，每个策略都是独立的子项目，便于学习和扩展。

### 核心特性

- 📚 **完整的文档体系** - 包含量化交易原理、策略详解、操作指南
- 🧩 **模块化架构** - 核心框架与策略分离，每个策略独立可运行
- 📊 **多种经典策略** - 趋势跟踪、均值回归、多因子、动量等 7 大类策略
- 🎮 **交易模拟器** - 完整的 A 股交易模拟，支持 T+1、涨跌停等规则
- 🔬 **回测引擎** - 高性能回测框架，支持多种绩效分析指标
- 📈 **可视化分析** - 收益曲线、风险指标、归因分析等

---

## 📁 项目结构

```
a-stock-quant/
├── README.md                     # 项目说明（本文件）
├── docs/                         # 文档目录
│   ├── 01-量化交易原理.md         # 量化交易基础理论
│   ├── 02-策略详解.md             # 各类策略详细说明
│   ├── 03-模拟器设计.md           # 交易模拟器架构设计
│   ├── 04-开发规范.md             # 代码规范与开发指南
│   ├── 05-快速开始.md             # 新手入门指南
│   └── 06-常见问题.md             # FAQ
│
├── core/                         # 核心框架（所有策略共享）✅
│   ├── data_fetch/               # 数据获取模块 ✅
│   │   ├── akshare_fetcher.py    # AKShare 数据接口
│   │   ├── tushare_fetcher.py    # Tushare 数据接口
│   │   └── data_cache.py         # 数据缓存管理
│   │
│   ├── backtest/                 # 回测引擎 ✅
│   │   ├── engine.py             # 回测主引擎
│   │   └── metrics.py            # 绩效指标计算
│   │
│   ├── simulator/                # 交易模拟器 ✅
│   │   ├── account.py            # 账户管理
│   │   ├── order.py              # 订单系统
│   │   ├── matching.py           # 撮合引擎
│   │   └── risk_control.py       # 风控模块
│   │
│   ├── analysis/                 # 分析模块 ✅
│   │   ├── performance.py        # 绩效分析
│   │   └── risk.py               # 风险分析
│   │
│   ├── utils/                    # 工具函数 ✅
│   │   ├── logger.py             # 日志工具
│   │   ├── config.py             # 配置管理
│   │   └── helpers.py            # 辅助函数
│   │
│   ├── rl/                       # 强化学习模块 ✅
│   │   └── multi_agent.py        # 多智能体强化学习
│   │
│   ├── ts_models/                # 时间序列模型 ✅
│   │   ├── __init__.py
│   │   ├── base.py               # 基础模型类
│   │   ├── patchtst.py           # PatchTST模型
│   │   ├── timesnet.py           # TimesNet模型
│   │   ├── itransformer.py       # iTransformer模型
│   │   └── factory.py            # 模型工厂
│   │
│   ├── llm/                      # 金融LLM模块 ✅
│   │   ├── __init__.py
│   │   └── finbert.py            # FinBERT情感分析
│   │
│   └── tabular/                  # 表格数据模型 ✅
│       ├── __init__.py
│       └── tabnet.py             # TabNet表格模型
│
├── strategies/                   # 策略目录（每个策略独立）✅
│   ├── base.py                   # 策略基类 ✅
│   ├── 01-trend-following/       # 策略 1: 趋势跟踪 ✅
│   │   ├── README.md             # 策略说明
│   │   ├── trend_strategy.py     # 策略实现
│   │   ├── config.yaml           # 策略配置
│   │   └── backtest.py           # 回测脚本
│   │
│   ├── 02-mean-reversion/        # 策略 2: 均值回归 ✅
│   │   ├── README.md
│   │   ├── mean_reversion_strategy.py
│   │   ├── config.yaml
│   │   └── backtest.py
│   │
│   ├── 03-multi-factor/          # 策略 3: 多因子选股 ✅
│   │   ├── README.md
│   │   ├── multi_factor_strategy.py
│   │   ├── config.yaml
│   │   └── backtest.py
│   │
│   ├── 04-momentum/              # 策略 4: 动量策略 ✅
│   │   ├── README.md
│   │   ├── momentum_strategy.py
│   │   ├── config.yaml
│   │   └── backtest.py
│   │
│   ├── 05-arbitrage/             # 策略 5: 套利策略 ✅
│   │   ├── README.md
│   │   ├── arbitrage_strategy.py
│   │   ├── config.yaml
│   │   └── backtest.py
│   │
│   ├── 06-event-driven/          # 策略 6: 事件驱动 ✅
│   │   ├── README.md
│   │   ├── event_driven_strategy.py
│   │   ├── config.yaml
│   │   └── backtest.py
│   │
│   └── 07-capital-flow/          # 策略 7: 资金流策略 ✅
│       ├── README.md
│       ├── capital_flow_strategy.py
│       ├── config.yaml
│       └── backtest.py
│
├── scripts/                      # 脚本目录 ✅
│   └── download_data.py          # 数据下载脚本 ✅
│
├── examples/                     # 示例目录 ✅
│   └── simple_backtest.py        # 回测示例 ✅
│
├── notebooks/                    # 公共 Jupyter 笔记 🔄
│   ├── 01-数据获取示例.ipynb
│   ├── 02-回测引擎使用.ipynb
│   └── 03-绩效分析示例.ipynb
│
├── config/                       # 全局配置 ✅
│   ├── default.yaml              # 默认配置
│   └── logging.yaml              # 日志配置
│
├── data/                         # 数据存储
│   ├── raw/                      # 原始数据
│   ├── processed/                # 处理后数据
│   └── cache/                    # 缓存数据
│
├── tests/                        # 测试目录 ✅
│   ├── test_utils.py             # 工具测试 ✅
│   ├── test_simulator.py         # 模拟器测试 ✅
│   ├── test_backtest.py          # 回测测试 ✅
│   └── test_strategies.py        # 策略测试 ✅
│
└── requirements.txt              # Python 依赖
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- pip 或 conda
- 推荐：Anaconda/Miniconda
- GPU（可选）：NVIDIA RTX 3060+ (6GB+ 显存)

### 2. 部署步骤

```bash
# 1. 克隆项目
cd /home/whqwill/code
git clone https://github.com/your-username/a-stock-quant.git
cd a-stock-quant

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 验证安装
python scripts/check_env.py

# 5. 运行示例
python examples/simple_backtest.py
```

### 3. 运行第一个策略

```bash
# 运行回测示例
python examples/simple_backtest.py

# 或在 Jupyter 中研究
jupyter notebook notebooks/
```

### 4. 配置说明

- **全局配置**：`config/default.yaml`
- **策略配置**：`config/strategies/`
- **日志配置**：`config/logging.yaml`

详细配置说明请参考：[配置说明文档](docs/13-配置说明.md)

### 5. GPU 配置（可选）

如果需要使用 GPU 加速训练，请参考：[GPU/CUDA 环境配置指南](docs/09-GPU环境配置指南.md)


---

## 📊 策略概览

| 策略 | 难度 | 资金需求 | 预期年化 | 适合市场 |
|------|------|---------|---------|---------|
| [趋势跟踪](strategies/01-trend-following/) | ⭐⭐ | 低 | 20%-50% | 趋势市 |
| [均值回归](strategies/02-mean-reversion/) | ⭐⭐ | 低 | 15%-40% | 震荡市 |
| [多因子选股](strategies/03-multi-factor/) | ⭐⭐⭐⭐ | 中 | 15%-30% | 所有 |
| [动量策略](strategies/04-momentum/) | ⭐⭐ | 低 | 20%-50% | 牛市 |
| [套利策略](strategies/05-arbitrage/) | ⭐⭐⭐⭐⭐ | 高 | 8%-20% | 所有 |
| [事件驱动](strategies/06-event-driven/) | ⭐⭐⭐ | 中 | 15%-40% | 所有 |
| [资金流策略](strategies/07-capital-flow/) | ⭐⭐ | 低 | 20%-50% | 所有 |

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [量化交易原理](docs/01-量化交易原理.md) | 量化交易基础理论、核心概念 |
| [策略详解](docs/02-策略详解.md) | 7 大类策略的原理与实现细节 |
| [模拟器设计](docs/03-模拟器设计.md) | 交易模拟器的架构与设计 |
| [开发规范](docs/04-开发规范.md) | 代码规范、开发流程 |
| [快速开始](docs/05-快速开始.md) | 新手入门指南 |
| [常见问题](docs/06-常见问题.md) | FAQ |
| [部署与运行指南](docs/12-部署与运行指南.md) | 环境部署、运行流程、配置说明 ⭐ |
| [模拟器操作指南](docs/10-模拟器操作指南.md) | 模拟器使用、策略选择、回测操作 ⭐ |
| [策略操作手册](docs/11-策略操作手册.md) | 7 大类策略详细操作指南 ⭐ |
| [配置说明](docs/13-配置说明.md) | 全局配置、策略配置、风控配置 ⭐ |
| [GPU/CUDA 环境配置指南](docs/09-GPU环境配置指南.md) | GPU 加速、CUDA 配置、国产芯片适配 ⭐ |
| [前沿技术与模型参考](docs/08-前沿技术与模型参考.md) | 量化领域最新技术、开源项目、预训练模型汇总 ⭐ |

---

## 🛠️ 核心模块说明

### 数据获取模块 (data_fetch)

支持多种数据源：
- **AKShare** - 免费开源，数据全面
- **Tushare Pro** - 专业数据，需要积分

### 回测引擎 (backtest)

核心功能：
- 事件驱动回测
- 支持多种订单类型
- 完整的交易成本计算
- 多种绩效指标

### 交易模拟器 (simulator)

模拟 A 股真实交易环境：
- T+1 交易规则
- 涨跌停限制
- 印花税与佣金
- 仓位风控

### 分析模块 (analysis)

提供全面的分析工具：
- 收益曲线
- 风险指标
- 归因分析
- 最大回撤

---

## 📝 开发计划

### 第一阶段：基础框架 ✅
- [x] 项目结构设计
- [x] 文档体系建立
- [x] 核心框架实现
- [x] 数据获取模块

### 第二阶段：策略实现 ✅
- [x] 趋势跟踪策略
- [x] 均值回归策略
- [x] 多因子选股策略
- [x] 动量策略
- [x] 套利策略
- [x] 事件驱动策略
- [x] 资金流策略

### 第三阶段：完善优化 🔄
- [x] 交易模拟器
- [x] 测试用例
- [x] 脚本和示例
- [ ] 可视化界面
- [ ] 性能优化
- [ ] 实盘对接

---

## 🤝 贡献指南

欢迎贡献代码、文档或建议！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## ⚠️ 免责声明

本项目仅供学习和研究使用，不构成任何投资建议。量化交易存在风险，实盘交易请谨慎。

---

## 📧 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件至：[your-email@example.com]

---

**祝你量化交易学习愉快！🎉**
