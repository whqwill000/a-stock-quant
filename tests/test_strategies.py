"""
测试策略模块

测试各类策略的功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.base import BaseStrategy, StrategyConfig, Signal
from strategies.trend_following.trend_strategy import (
    TrendFollowingStrategy, TrendFollowingConfig,
    DualThrustStrategy, DonchianChannelStrategy
)
from strategies.mean_reversion.mean_reversion_strategy import (
    MeanReversionStrategy, MeanReversionConfig,
    RSIMeanReversionStrategy, BollingerBandsStrategy
)
from strategies.multi_factor.multi_factor_strategy import (
    MultiFactorStrategy, MultiFactorConfig
)
from strategies.momentum.momentum_strategy import (
    MomentumStrategy, MomentumConfig,
    PriceMomentumStrategy
)


class TestBaseStrategy:
    """测试策略基类"""
    
    def test_signal_creation(self):
        """测试信号创建"""
        signal = Signal(
            stock_code="000001.SZ",
            signal_type="buy",
            price=10.5,
            strength=0.8,
            reason="测试信号"
        )
        
        assert signal.stock_code == "000001.SZ"
        assert signal.is_buy == True
        assert signal.is_sell == False
        assert signal.strength == 0.8
    
    def test_strategy_config(self):
        """测试策略配置"""
        config = StrategyConfig(
            name="TestStrategy",
            description="测试策略",
            params={"param1": 1, "param2": 2}
        )
        
        assert config.name == "TestStrategy"
        assert config.params["param1"] == 1


class TestTrendFollowingStrategy:
    """测试趋势跟踪策略"""
    
    @pytest.fixture
    def trend_data(self):
        """创建趋势行情数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
        np.random.seed(42)
        
        # 模拟上升趋势
        trend = np.linspace(10, 15, 100)
        noise = np.random.normal(0, 0.3, 100)
        prices = trend + noise
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
            'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
            'low': prices * (1 + np.random.uniform(-0.02, 0, 100)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })
        
        return {'000001.SZ': df}
    
    def test_trend_strategy_creation(self):
        """测试趋势策略创建"""
        config = TrendFollowingConfig(
            ma_short=5,
            ma_long=20
        )
        
        strategy = TrendFollowingStrategy(config)
        
        assert strategy.config.ma_short == 5
        assert strategy.config.ma_long == 20
    
    def test_trend_strategy_signals(self, trend_data):
        """测试趋势策略信号生成"""
        strategy = TrendFollowingStrategy()
        signals = strategy.generate_signals(trend_data)
        
        # 应该生成信号
        assert isinstance(signals, list)
    
    def test_dual_thrust_strategy(self, trend_data):
        """测试 Dual Thrust 策略"""
        strategy = DualThrustStrategy(n_days=4, k1=0.5, k2=0.5)
        signals = strategy.generate_signals(trend_data)
        
        assert isinstance(signals, list)
    
    def test_donchian_channel_strategy(self, trend_data):
        """测试唐奇安通道策略"""
        strategy = DonchianChannelStrategy(entry_period=20, exit_period=10)
        signals = strategy.generate_signals(trend_data)
        
        assert isinstance(signals, list)


class TestMeanReversionStrategy:
    """测试均值回归策略"""
    
    @pytest.fixture
    def range_data(self):
        """创建震荡行情数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
        np.random.seed(42)
        
        # 模拟震荡行情
        base = 10
        noise = np.random.normal(0, 0.5, 100)
        cycle = 2 * np.sin(np.linspace(0, 4*np.pi, 100))
        prices = base + cycle + noise
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
            'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
            'low': prices * (1 + np.random.uniform(-0.02, 0, 100)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })
        
        return {'000001.SZ': df}
    
    def test_mean_reversion_creation(self):
        """测试均值回归策略创建"""
        config = MeanReversionConfig(
            ma_period=20,
            entry_zscore=2.0
        )
        
        strategy = MeanReversionStrategy(config)
        
        assert strategy.config.ma_period == 20
        assert strategy.config.entry_zscore == 2.0
    
    def test_mean_reversion_signals(self, range_data):
        """测试均值回归策略信号生成"""
        strategy = MeanReversionStrategy()
        signals = strategy.generate_signals(range_data)
        
        assert isinstance(signals, list)
    
    def test_rsi_mean_reversion(self, range_data):
        """测试 RSI 均值回归策略"""
        strategy = RSIMeanReversionStrategy(
            rsi_period=14,
            oversold=30.0,
            overbought=70.0
        )
        signals = strategy.generate_signals(range_data)
        
        assert isinstance(signals, list)
    
    def test_bollinger_bands_strategy(self, range_data):
        """测试布林带策略"""
        strategy = BollingerBandsStrategy(period=20, std_dev=2.0)
        signals = strategy.generate_signals(range_data)
        
        assert isinstance(signals, list)


class TestMultiFactorStrategy:
    """测试多因子策略"""
    
    @pytest.fixture
    def multi_stock_data(self):
        """创建多股票数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
        np.random.seed(42)
        
        data = {}
        for i, code in enumerate(['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']):
            prices = 10 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
            
            df = pd.DataFrame({
                'date': dates,
                'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
                'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
                'low': prices * (1 + np.random.uniform(-0.02, 0, 100)),
                'close': prices,
                'volume': np.random.randint(100000, 1000000, 100),
                'amount': np.random.randint(1000000, 10000000, 100),
                'pe': np.random.uniform(10, 50, 100),
                'pb': np.random.uniform(1, 5, 100),
                'roe': np.random.uniform(0.05, 0.25, 100)
            })
            data[code] = df
        
        return data
    
    def test_multi_factor_creation(self):
        """测试多因子策略创建"""
        config = MultiFactorConfig(
            top_n=5,
            rebalance_freq=20
        )
        
        strategy = MultiFactorStrategy(config)
        
        assert strategy.config.top_n == 5
        assert strategy.config.rebalance_freq == 20
    
    def test_multi_factor_signals(self, multi_stock_data):
        """测试多因子策略信号生成"""
        strategy = MultiFactorStrategy()
        signals = strategy.generate_signals(multi_stock_data)
        
        assert isinstance(signals, list)


class TestMomentumStrategy:
    """测试动量策略"""
    
    @pytest.fixture
    def momentum_data(self):
        """创建动量行情数据"""
        dates = pd.date_range(start='2023-01-01', periods=150, freq='B')
        np.random.seed(42)
        
        data = {}
        for i, code in enumerate(['000001.SZ', '000002.SZ', '600000.SH']):
            # 模拟不同强度的趋势
            trend = np.linspace(10, 10 * (1 + 0.3 * (i - 1)), 150)
            noise = np.random.normal(0, 0.5, 150)
            prices = trend + noise
            
            df = pd.DataFrame({
                'date': dates,
                'open': prices * (1 + np.random.uniform(-0.01, 0.01, 150)),
                'high': prices * (1 + np.random.uniform(0, 0.02, 150)),
                'low': prices * (1 + np.random.uniform(-0.02, 0, 150)),
                'close': prices,
                'volume': np.random.randint(100000, 1000000, 150)
            })
            data[code] = df
        
        return data
    
    def test_momentum_creation(self):
        """测试动量策略创建"""
        config = MomentumConfig(
            lookback_period=60,
            top_n=5
        )
        
        strategy = MomentumStrategy(config)
        
        assert strategy.config.lookback_period == 60
        assert strategy.config.top_n == 5
    
    def test_momentum_signals(self, momentum_data):
        """测试动量策略信号生成"""
        strategy = MomentumStrategy()
        signals = strategy.generate_signals(momentum_data)
        
        assert isinstance(signals, list)
    
    def test_price_momentum(self, momentum_data):
        """测试价格动量策略"""
        strategy = PriceMomentumStrategy(
            lookback_periods=[20, 60],
            weights=[0.4, 0.6]
        )
        signals = strategy.generate_signals(momentum_data)
        
        assert isinstance(signals, list)


class TestTechnicalIndicators:
    """测试技术指标计算"""
    
    @pytest.fixture
    def price_data(self):
        """创建价格数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
        np.random.seed(42)
        
        prices = 10 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'volume': np.random.randint(100000, 1000000, 100)
        })
        
        return df
    
    def test_sma(self, price_data):
        """测试 SMA 计算"""
        strategy = TrendFollowingStrategy()
        sma = strategy.sma(price_data['close'], 20)
        
        assert len(sma) == len(price_data)
        assert sma.iloc[-1] > 0
    
    def test_ema(self, price_data):
        """测试 EMA 计算"""
        strategy = TrendFollowingStrategy()
        ema = strategy.ema(price_data['close'], 20)
        
        assert len(ema) == len(price_data)
        assert ema.iloc[-1] > 0
    
    def test_rsi(self, price_data):
        """测试 RSI 计算"""
        strategy = TrendFollowingStrategy()
        rsi = strategy.rsi(price_data['close'], 14)
        
        assert len(rsi) == len(price_data)
        # RSI 应该在 0-100 之间
        assert 0 <= rsi.iloc[-1] <= 100
    
    def test_macd(self, price_data):
        """测试 MACD 计算"""
        strategy = TrendFollowingStrategy()
        macd, signal, hist = strategy.macd(price_data['close'])
        
        assert len(macd) == len(price_data)
        assert len(signal) == len(price_data)
        assert len(hist) == len(price_data)
    
    def test_bollinger_bands(self, price_data):
        """测试布林带计算"""
        strategy = TrendFollowingStrategy()
        upper, middle, lower = strategy.bollinger_bands(price_data['close'])
        
        assert len(upper) == len(price_data)
        # 上轨 > 中轨 > 下轨
        assert upper.iloc[-1] > middle.iloc[-1] > lower.iloc[-1]


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])