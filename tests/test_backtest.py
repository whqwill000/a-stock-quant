"""
测试回测引擎模块

测试回测引擎、绩效指标等功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtest.metrics import MetricsCalculator, PerformanceMetrics
from core.backtest.engine import BacktestEngine, BacktestConfig, BacktestResult


class TestMetricsCalculator:
    """测试绩效指标计算器"""
    
    @pytest.fixture
    def sample_equity_curve(self):
        """创建示例权益曲线"""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='B')
        np.random.seed(42)
        
        # 模拟权益曲线
        returns = np.random.normal(0.001, 0.02, 252)
        equity = 1000000 * (1 + returns).cumprod()
        
        return pd.Series(equity, index=dates)
    
    @pytest.fixture
    def sample_benchmark_curve(self):
        """创建示例基准曲线"""
        dates = pd.date_range(start='2023-01-01', periods=252, freq='B')
        np.random.seed(43)
        
        returns = np.random.normal(0.0005, 0.015, 252)
        equity = 1000000 * (1 + returns).cumprod()
        
        return pd.Series(equity, index=dates)
    
    def test_calculate_total_return(self, sample_equity_curve):
        """测试总收益率计算"""
        calculator = MetricsCalculator()
        total_return = calculator._calculate_total_return(sample_equity_curve)
        
        # 总收益率应该是一个合理的数值
        assert -1 < total_return < 10
    
    def test_calculate_annual_return(self, sample_equity_curve):
        """测试年化收益率计算"""
        calculator = MetricsCalculator()
        annual_return = calculator._calculate_annual_return(sample_equity_curve)
        
        # 年化收益率应该是一个合理的数值
        assert -1 < annual_return < 10
    
    def test_calculate_volatility(self, sample_equity_curve):
        """测试波动率计算"""
        calculator = MetricsCalculator()
        returns = sample_equity_curve.pct_change().dropna()
        volatility = calculator._calculate_volatility(returns)
        
        # 波动率应该是正数
        assert volatility > 0
        # 年化波动率通常在 10%-50% 之间
        assert 0.1 < volatility < 0.5
    
    def test_calculate_max_drawdown(self, sample_equity_curve):
        """测试最大回撤计算"""
        calculator = MetricsCalculator()
        max_dd, duration = calculator._calculate_max_drawdown(sample_equity_curve)
        
        # 最大回撤应该在 0-1 之间
        assert 0 <= max_dd < 1
        # 持续期应该是正整数
        assert duration >= 0
    
    def test_calculate_sharpe_ratio(self, sample_equity_curve):
        """测试夏普比率计算"""
        calculator = MetricsCalculator()
        returns = sample_equity_curve.pct_change().dropna()
        sharpe = calculator._calculate_sharpe_ratio(returns)
        
        # 夏普比率通常在 -3 到 3 之间
        assert -5 < sharpe < 5
    
    def test_calculate_sortino_ratio(self, sample_equity_curve):
        """测试索提诺比率计算"""
        calculator = MetricsCalculator()
        returns = sample_equity_curve.pct_change().dropna()
        sortino = calculator._calculate_sortino_ratio(returns)
        
        # 索提诺比率可以是任意值，但不应该是 NaN
        assert not np.isnan(sortino)
    
    def test_calculate_var(self, sample_equity_curve):
        """测试 VaR 计算"""
        calculator = MetricsCalculator()
        returns = sample_equity_curve.pct_change().dropna()
        var = calculator._calculate_var(returns, 0.95)
        
        # VaR 应该是正数（表示损失）
        assert var > 0
    
    def test_calculate_cvar(self, sample_equity_curve):
        """测试 CVaR 计算"""
        calculator = MetricsCalculator()
        returns = sample_equity_curve.pct_change().dropna()
        cvar = calculator._calculate_cvar(returns, 0.95)
        
        # CVaR 应该是正数且大于等于 VaR
        var = calculator._calculate_var(returns, 0.95)
        assert cvar >= var
    
    def test_calculate_all_metrics(self, sample_equity_curve, sample_benchmark_curve):
        """测试计算所有指标"""
        calculator = MetricsCalculator()
        metrics = calculator.calculate(sample_equity_curve, sample_benchmark_curve)
        
        # 检查所有指标都已计算
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_return != 0
        assert metrics.volatility > 0
        assert 0 <= metrics.max_drawdown < 1


class TestBacktestEngine:
    """测试回测引擎"""
    
    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
        np.random.seed(42)
        
        data = {}
        for code in ['000001.SZ', '000002.SZ', '600000.SH']:
            prices = 10 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
            
            df = pd.DataFrame({
                'date': dates,
                'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
                'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
                'low': prices * (1 + np.random.uniform(-0.02, 0, 100)),
                'close': prices,
                'volume': np.random.randint(100000, 1000000, 100)
            })
            data[code] = df
        
        return data
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        config = BacktestConfig(
            initial_cash=1000000,
            start_date="2023-01-01",
            end_date="2023-12-31"
        )
        
        engine = BacktestEngine(config)
        
        assert engine.config.initial_cash == 1000000
        assert engine.account.initial_cash == 1000000
    
    def test_load_data(self, sample_data):
        """测试数据加载"""
        config = BacktestConfig()
        engine = BacktestEngine(config)
        
        engine.load_data(sample_data)
        
        assert len(engine.data) == 3
        assert len(engine.trading_days) == 100
    
    def test_run_backtest(self, sample_data):
        """测试运行回测"""
        config = BacktestConfig(
            initial_cash=1000000,
            start_date="2023-01-01",
            end_date="2023-05-31"
        )
        engine = BacktestEngine(config)
        engine.load_data(sample_data)
        
        # 定义简单策略
        def simple_strategy(engine, date, data):
            # 第一天买入
            if date == engine.trading_days[0]:
                for stock_code in list(data.keys())[:2]:
                    engine.buy(stock_code, 1000)
        
        result = engine.run(simple_strategy)
        
        assert isinstance(result, BacktestResult)
        assert not result.equity_curve.empty
        assert result.metrics is not None
    
    def test_buy_sell(self, sample_data):
        """测试买卖操作"""
        config = BacktestConfig()
        engine = BacktestEngine(config)
        engine.load_data(sample_data)
        
        # 设置当前日期
        engine.current_date = engine.trading_days[0]
        
        # 买入
        order = engine.buy("000001.SZ", 1000, 10.0)
        
        assert order is not None
        assert engine.account.get_position("000001.SZ").total_volume == 1000


class TestBacktestResult:
    """测试回测结果"""
    
    def test_result_summary(self):
        """测试结果摘要"""
        config = BacktestConfig()
        metrics = PerformanceMetrics(
            total_return=0.2,
            annual_return=0.15,
            max_drawdown=0.1,
            sharpe_ratio=1.5
        )
        
        result = BacktestResult(
            config=config,
            metrics=metrics,
            equity_curve=pd.Series([1000000, 1100000, 1200000])
        )
        
        summary = result.summary()
        
        assert "总收益率" in summary
        assert "20.00%" in summary


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])