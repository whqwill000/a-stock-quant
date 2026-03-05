# 文档索引

> A 股量化金融平台完整文档目录

---

## 📚 文档导航

### 入门指南

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [项目说明](../README.md) | 项目介绍和快速导航 | 所有人 |
| [快速开始](05-快速开始.md) | 环境配置和第一个策略 | 新手 |
| [常见问题](06-常见问题.md) | FAQ 和故障排除 | 所有人 |

### 理论学习

| 文档 | 说明 | 难度 |
|------|------|------|
| [量化交易原理](01-量化交易原理.md) | 量化交易基础理论和核心概念 | ⭐⭐ |
| [策略详解](02-策略详解.md) | 7 大类策略的原理与实现方法 | ⭐⭐⭐ |

### 技术文档

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [模拟器设计](03-模拟器设计.md) | 交易模拟器的架构设计与实现 | 开发者 |
| [开发规范](04-开发规范.md) | 代码规范、开发流程和最佳实践 | 开发者 |
| [前沿技术与模型参考](08-前沿技术与模型参考.md) | 量化领域最新技术、开源项目、预训练模型汇总 | 所有人 |

### 策略文档

每个策略子目录都有独立的文档：

| 策略 | 文档 | 难度 |
|------|------|------|
| 趋势跟踪 | [strategies/01-trend-following/README.md](../strategies/01-trend-following/README.md) | ⭐⭐ |
| 均值回归 | [strategies/02-mean-reversion/README.md](../strategies/02-mean-reversion/README.md) | ⭐⭐ |
| 多因子选股 | [strategies/03-multi-factor/README.md](../strategies/03-multi-factor/README.md) | ⭐⭐⭐⭐ |
| 动量策略 | [strategies/04-momentum/README.md](../strategies/04-momentum/README.md) | ⭐⭐ |
| 套利策略 | [strategies/05-arbitrage/README.md](../strategies/05-arbitrage/README.md) | ⭐⭐⭐⭐⭐ |
| 事件驱动 | [strategies/06-event-driven/README.md](../strategies/06-event-driven/README.md) | ⭐⭐⭐ |
| 资金流策略 | [strategies/07-capital-flow/README.md](../strategies/07-capital-flow/README.md) | ⭐⭐ |

---

## 🗺️ 学习路径

### 新手入门

```
1. 阅读 [项目说明](../README.md)
       ↓
2. 阅读 [快速开始](05-快速开始.md)
       ↓
3. 配置环境，运行第一个策略
       ↓
4. 阅读 [量化交易原理](01-量化交易原理.md)
       ↓
5. 阅读 [策略详解](02-策略详解.md)
       ↓
6. 修改策略参数，观察结果变化
```

### 策略开发

```
1. 阅读 [策略详解](02-策略详解.md)
       ↓
2. 选择感兴趣的策略类型
       ↓
3. 阅读对应策略的子目录文档
       ↓
4. 参考 [策略模板](../strategies/STRATEGY_TEMPLATE/README.md)
       ↓
5. 开发自己的策略
       ↓
6. 回测验证
```

### 核心开发

```
1. 阅读 [开发规范](04-开发规范.md)
       ↓
2. 阅读 [模拟器设计](03-模拟器设计.md)
       ↓
3. 了解核心模块架构
       ↓
4. 参与核心模块开发
```

---

## 📖 文档结构

```
docs/
├── 01-量化交易原理.md      # 量化交易基础理论
├── 02-策略详解.md          # 各类策略详细说明
├── 03-模拟器设计.md        # 交易模拟器架构设计
├── 04-开发规范.md          # 代码规范与开发指南
├── 05-快速开始.md          # 新手入门指南
├── 06-常见问题.md          # FAQ
└── INDEX.md                # 文档索引（本文件）
```

---

## 🔗 外部资源

### 数据源

- [AKShare 文档](https://akshare.akfamily.xyz/)
- [Tushare 文档](https://tushare.pro/document/2)

### 学习资源

- [Pandas 文档](https://pandas.pydata.org/docs/)
- [Matplotlib 文档](https://matplotlib.org/stable/contents.html)
- [Scikit-learn 文档](https://scikit-learn.org/stable/)

### 社区

- [聚宽社区](https://www.joinquant.com/)
- [量化投资与量化交易知乎专栏](https://www.zhihu.com/topic/19578823)

---

## 📝 文档贡献

欢迎贡献文档！请遵循 [开发规范](04-开发规范.md#6-文档规范) 中的文档规范。

### 文档更新记录

| 日期 | 文档 | 更新内容 |
|------|------|---------|
| 2024-01-01 | 所有文档 | 初始版本 |

---

**如有文档相关问题或建议，请提交 Issue。**
