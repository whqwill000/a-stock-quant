# Jupyter Notebook 示例

本目录包含交互式分析示例。

## 可用示例

| 文件 | 说明 | 状态 |
|------|------|------|
| 01-数据获取示例.ipynb | AKShare/Tushare 数据获取演示 | 📝 待创建 |
| 02-回测引擎使用.ipynb | 回测引擎使用演示 | 📝 待创建 |
| 03-绩效分析示例.ipynb | 绩效分析和可视化演示 | 📝 待创建 |

## 使用方法

```bash
# 启动 Jupyter Notebook
cd /home/whqwill/code/a-stock-quant
jupyter notebook

# 或使用 Jupyter Lab
jupyter lab
```

## 临时替代

在 Notebook 示例创建之前，可以参考以下代码示例：

- `examples/simple_backtest.py` - 回测示例
- `scripts/download_data.py` - 数据下载脚本
- `tests/` 目录下的测试文件

## 核心模块使用

```python
# 数据获取
from core.data_fetch.akshare_fetcher import AKShareFetcher
fetcher = AKShareFetcher()
data = fetcher.get_stock_daily("000001.SZ", "2023-01-01", "2023-12-31")

# 回测引擎
from core.backtest.engine import BacktestEngine
engine = BacktestEngine(initial_capital=1000000)

# 策略
from strategies.trend_following.trend_strategy import TrendFollowingStrategy
strategy = TrendFollowingStrategy()

# 运行回测
result = engine.run(data, strategy)
```
