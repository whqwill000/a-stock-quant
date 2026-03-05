"""
简单回测示例

演示如何使用回测引擎进行策略回测

运行方式:
    python examples/simple_backtest.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime

# 导入项目模块
from core.backtest.engine import BacktestEngine, BacktestConfig
from core.backtest.metrics import MetricsCalculator
from strategies.trend_following.trend_strategy import TrendFollowingStrategy
from strategies.mean_reversion.mean_reversion_strategy import MeanReversionStrategy


def generate_sample_data(start_date='2023-01-01', periods=252, n_stocks=5):
    """
    生成示例数据
    
    Args:
        start_date: 开始日期
        periods: 数据条数
        n_stocks: 股票数量
        
    Returns:
        数据字典
    """
    dates = pd.date_range(start=start_date, periods=periods, freq='B')
    np.random.seed(42)
    
    stock_codes = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000651.SZ'][:n_stocks]
    
    data = {}
    for i, code in enumerate(stock_codes):
        # 模拟不同特性的股票
        # 趋势强度不同
        trend_strength = 0.3 * (i - n_stocks // 2)
        trend = np.linspace(10, 10 * (1 + trend_strength), periods)
        noise = np.random.normal(0, 0.5, periods)
        prices = trend + noise
        
        # 确保价格为正
        prices = np.maximum(prices, 1)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, periods)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, periods))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, periods))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, periods),
            'amount': np.random.randint(1000000, 10000000, periods)
        })
        
        data[code] = df
    
    return data


def run_trend_following_backtest():
    """
    运行趋势跟踪策略回测
    """
    print("=" * 60)
    print("趋势跟踪策略回测")
    print("=" * 60)
    
    # 生成数据
    print("\n【生成测试数据】")
    data = generate_sample_data(periods=252, n_stocks=5)
    print(f"股票数量: {len(data)}")
    print(f"数据条数: {len(list(data.values())[0])}")
    
    # 配置回测
    config = BacktestConfig(
        initial_cash=1000000,
        start_date="2023-01-01",
        end_date="2023-12-31",
        commission_rate=0.00025,
        stamp_tax_rate=0.0005
    )
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 加载数据
    engine.load_data(data)
    
    # 创建策略
    strategy = TrendFollowingStrategy()
    
    # 定义策略函数
    def trend_strategy(engine, date, data):
        """趋势跟踪策略"""
        # 每月第一个交易日调仓
        if date.day <= 5 and date.weekday() < 5:
            # 获取当前持仓
            positions = list(engine.account.positions.keys())
            
            # 卖出不在信号中的持仓
            for stock_code in positions:
                if engine.get_position(stock_code) > 0:
                    engine.sell(stock_code, engine.get_position(stock_code))
            
            # 生成信号
            signals = strategy.generate_signals(data)
            
            # 买入信号股票
            for signal in signals:
                if signal.is_buy:
                    # 计算买入金额（等权重）
                    cash_per_stock = engine.get_cash() * 0.9 / len(signals)
                    volume = int(cash_per_stock / signal.price / 100) * 100
                    
                    if volume > 0:
                        engine.buy(signal.stock_code, volume, signal.price)
    
    # 运行回测
    print("\n【运行回测】")
    result = engine.run(trend_strategy)
    
    # 打印结果
    print(result.summary())
    
    return result


def run_mean_reversion_backtest():
    """
    运行均值回归策略回测
    """
    print("\n" + "=" * 60)
    print("均值回归策略回测")
    print("=" * 60)
    
    # 生成数据（震荡行情）
    print("\n【生成测试数据】")
    dates = pd.date_range(start='2023-01-01', periods=252, freq='B')
    np.random.seed(42)
    
    data = {}
    for i, code in enumerate(['000001.SZ', '000002.SZ', '600000.SH']):
        # 模拟震荡行情
        base = 10 + i
        cycle = 2 * np.sin(np.linspace(0, 8*np.pi, 252))
        noise = np.random.normal(0, 0.3, 252)
        prices = base + cycle + noise
        prices = np.maximum(prices, 1)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, 252)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, 252))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, 252))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 252)
        })
        data[code] = df
    
    print(f"股票数量: {len(data)}")
    
    # 配置回测
    config = BacktestConfig(
        initial_cash=1000000,
        start_date="2023-01-01",
        end_date="2023-12-31"
    )
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    engine.load_data(data)
    
    # 创建策略
    strategy = MeanReversionStrategy()
    
    # 定义策略函数
    def mr_strategy(engine, date, data):
        """均值回归策略"""
        signals = strategy.generate_signals(data)
        
        for signal in signals:
            if signal.is_buy:
                cash = engine.get_cash() * 0.3
                volume = int(cash / signal.price / 100) * 100
                if volume > 0:
                    engine.buy(signal.stock_code, volume, signal.price)
            elif signal.is_sell:
                position = engine.get_position(signal.stock_code)
                if position > 0:
                    engine.sell(signal.stock_code, position, signal.price)
    
    # 运行回测
    print("\n【运行回测】")
    result = engine.run(mr_strategy)
    
    # 打印结果
    print(result.summary())
    
    return result


def compare_strategies():
    """
    比较不同策略的表现
    """
    print("\n" + "=" * 60)
    print("策略比较")
    print("=" * 60)
    
    # 生成相同的数据
    data = generate_sample_data(periods=252, n_stocks=5)
    
    results = {}
    
    # 1. 趋势跟踪策略
    config = BacktestConfig(initial_cash=1000000)
    engine = BacktestEngine(config)
    engine.load_data(data)
    
    strategy = TrendFollowingStrategy()
    
    def trend_func(engine, date, data):
        signals = strategy.generate_signals(data)
        for signal in signals:
            if signal.is_buy and not engine.has_position(signal.stock_code):
                volume = int(engine.get_cash() * 0.2 / signal.price / 100) * 100
                if volume > 0:
                    engine.buy(signal.stock_code, volume, signal.price)
            elif signal.is_sell and engine.has_position(signal.stock_code):
                engine.sell(signal.stock_code, engine.get_position(signal.stock_code), signal.price)
    
    results['趋势跟踪'] = engine.run(trend_func)
    
    # 2. 均值回归策略
    engine = BacktestEngine(config)
    engine.load_data(data)
    
    strategy = MeanReversionStrategy()
    
    def mr_func(engine, date, data):
        signals = strategy.generate_signals(data)
        for signal in signals:
            if signal.is_buy and not engine.has_position(signal.stock_code):
                volume = int(engine.get_cash() * 0.3 / signal.price / 100) * 100
                if volume > 0:
                    engine.buy(signal.stock_code, volume, signal.price)
            elif signal.is_sell and engine.has_position(signal.stock_code):
                engine.sell(signal.stock_code, engine.get_position(signal.stock_code), signal.price)
    
    results['均值回归'] = engine.run(mr_func)
    
    # 3. 买入持有策略
    engine = BacktestEngine(config)
    engine.load_data(data)
    
    def buy_hold(engine, date, data):
        if date == engine.trading_days[0]:
            stock_codes = list(data.keys())
            cash_per_stock = engine.get_cash() / len(stock_codes)
            for code in stock_codes:
                price = data[code]['close'].iloc[0]
                volume = int(cash_per_stock / price / 100) * 100
                if volume > 0:
                    engine.buy(code, volume, price)
    
    results['买入持有'] = engine.run(buy_hold)
    
    # 打印比较结果
    print("\n策略表现比较:")
    print("-" * 60)
    print(f"{'策略':<12} {'总收益':<12} {'年化收益':<12} {'最大回撤':<12} {'夏普比率':<10}")
    print("-" * 60)
    
    for name, result in results.items():
        print(f"{name:<12} "
              f"{result.metrics.total_return*100:>10.2f}% "
              f"{result.metrics.annual_return*100:>10.2f}% "
              f"{result.metrics.max_drawdown*100:>10.2f}% "
              f"{result.metrics.sharpe_ratio:>10.2f}")
    
    print("-" * 60)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("A股量化交易平台 - 回测示例")
    print("=" * 60)
    
    # 运行趋势跟踪策略回测
    run_trend_following_backtest()
    
    # 运行均值回归策略回测
    run_mean_reversion_backtest()
    
    # 比较策略
    compare_strategies()
    
    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()