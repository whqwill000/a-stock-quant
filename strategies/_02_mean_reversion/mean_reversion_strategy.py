"""
均值回归策略

基于价格偏离均值的均值回归策略
适用于震荡行情，价格围绕均值波动的市场环境

策略原理：
1. 价格偏离均值过大时会回归
2. 使用布林带、RSI等指标判断超买超卖
3. 在极端位置反向操作
4. 回归均值后平仓

使用方法:
    from strategies.mean_reversion import MeanReversionStrategy
    
    strategy = MeanReversionStrategy()
    signals = strategy.generate_signals(data)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# 导入项目模块
from strategies.base import BaseStrategy, StrategyConfig, Signal
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class MeanReversionConfig(StrategyConfig):
    """
    均值回归策略配置
    
    Attributes:
        ma_period: 均线周期
        std_period: 标准差周期
        entry_zscore: 入场Z-Score阈值
        exit_zscore: 出场Z-Score阈值
        rsi_period: RSI周期
        rsi_oversold: RSI超卖阈值
        rsi_overbought: RSI超买阈值
        bb_period: 布林带周期
        bb_std: 布林带标准差倍数
        max_holding_days: 最大持仓天数
    """
    
    name: str = "MeanReversion"
    description: str = "均值回归策略"
    ma_period: int = 20
    std_period: int = 20
    entry_zscore: float = 2.0
    exit_zscore: float = 0.5
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    bb_period: int = 20
    bb_std: float = 2.0
    max_holding_days: int = 10


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略
    
    基于布林带和RSI的均值回归策略
    
    买入条件：
    1. 价格触及布林带下轨
    2. RSI处于超卖区域
    3. Z-Score低于阈值
    
    卖出条件：
    1. 价格回归到布林带中轨
    2. RSI回归到中性区域
    3. Z-Score回归到零附近
    
    Attributes:
        config: 策略配置
        entry_dates: 入场日期记录
    """
    
    def __init__(self, config: Optional[MeanReversionConfig] = None):
        """
        初始化均值回归策略
        
        Args:
            config: 策略配置
        """
        super().__init__(config or MeanReversionConfig())
        
        # 入场日期记录
        self.entry_dates: Dict[str, int] = {}
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 数据字典 {股票代码: DataFrame}
            
        Returns:
            信号列表
        """
        signals = []
        
        for stock_code, df in data.items():
            if len(df) < self.config.ma_period + 10:
                continue
            
            # 计算指标
            indicators = self._calculate_indicators(df)
            
            if indicators is None:
                continue
            
            # 生成信号
            signal = self._generate_signal(stock_code, df, indicators)
            
            if signal:
                signals.append(signal)
        
        return signals
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        计算技术指标
        
        Args:
            df: K 线数据
            
        Returns:
            指标字典
        """
        try:
            close = df['close']
            
            # 计算布林带
            bb_upper, bb_middle, bb_lower = self.bollinger_bands(
                close, self.config.bb_period, self.config.bb_std
            )
            
            # 计算 RSI
            rsi = self.rsi(close, self.config.rsi_period)
            
            # 计算 Z-Score
            ma = close.rolling(self.config.ma_period).mean()
            std = close.rolling(self.config.std_period).std()
            zscore = (close - ma) / std
            
            # 计算价格在布林带中的位置
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)
            
            return {
                'close': close,
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower,
                'bb_position': bb_position,
                'rsi': rsi,
                'zscore': zscore,
                'ma': ma
            }
            
        except Exception as e:
            logger.error(f"计算指标失败: {e}")
            return None
    
    def _generate_signal(
        self,
        stock_code: str,
        df: pd.DataFrame,
        indicators: Dict
    ) -> Optional[Signal]:
        """
        生成单个股票的信号
        
        Args:
            stock_code: 股票代码
            df: K 线数据
            indicators: 指标字典
            
        Returns:
            交易信号
        """
        close = indicators['close']
        bb_upper = indicators['bb_upper']
        bb_middle = indicators['bb_middle']
        bb_lower = indicators['bb_lower']
        bb_position = indicators['bb_position']
        rsi = indicators['rsi']
        zscore = indicators['zscore']
        
        # 获取最新值
        current_price = close.iloc[-1]
        current_bb_pos = bb_position.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_zscore = zscore.iloc[-1]
        
        # 检查是否有持仓
        has_position = self.has_position(stock_code)
        
        if has_position:
            # 持仓情况：检查卖出信号
            return self._check_sell_signal(
                stock_code, df, indicators, current_price
            )
        else:
            # 空仓情况：检查买入信号
            return self._check_buy_signal(
                stock_code, df, indicators, current_price
            )
    
    def _check_buy_signal(
        self,
        stock_code: str,
        df: pd.DataFrame,
        indicators: Dict,
        current_price: float
    ) -> Optional[Signal]:
        """
        检查买入信号
        
        Args:
            stock_code: 股票代码
            df: K 线数据
            indicators: 指标字典
            current_price: 当前价格
            
        Returns:
            买入信号
        """
        bb_position = indicators['bb_position']
        rsi = indicators['rsi']
        zscore = indicators['zscore']
        bb_lower = indicators['bb_lower']
        
        current_bb_pos = bb_position.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_zscore = zscore.iloc[-1]
        
        # 条件1：价格触及或跌破布林带下轨
        touch_lower = current_bb_pos <= 0.1
        
        # 条件2：RSI 超卖
        rsi_oversold = current_rsi <= self.config.rsi_oversold
        
        # 条件3：Z-Score 过低
        zscore_low = current_zscore <= -self.config.entry_zscore
        
        # 综合判断（满足任意两个条件）
        conditions_met = sum([touch_lower, rsi_oversold, zscore_low])
        
        if conditions_met >= 2:
            # 记录入场
            self.entry_dates[stock_code] = len(df)
            
            reasons = []
            if touch_lower:
                reasons.append(f"触及布林带下轨")
            if rsi_oversold:
                reasons.append(f"RSI超卖({current_rsi:.1f})")
            if zscore_low:
                reasons.append(f"Z-Score过低({current_zscore:.2f})")
            
            return Signal(
                stock_code=stock_code,
                signal_type='buy',
                price=current_price,
                strength=min(1.0, abs(current_zscore) / 3),
                reason="; ".join(reasons)
            )
        
        return None
    
    def _check_sell_signal(
        self,
        stock_code: str,
        df: pd.DataFrame,
        indicators: Dict,
        current_price: float
    ) -> Optional[Signal]:
        """
        检查卖出信号
        
        Args:
            stock_code: 股票代码
            df: K 线数据
            indicators: 指标字典
            current_price: 当前价格
            
        Returns:
            卖出信号
        """
        bb_position = indicators['bb_position']
        rsi = indicators['rsi']
        zscore = indicators['zscore']
        bb_middle = indicators['bb_middle']
        bb_upper = indicators['bb_upper']
        
        current_bb_pos = bb_position.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_zscore = zscore.iloc[-1]
        
        # 检查持仓天数
        entry_idx = self.entry_dates.get(stock_code)
        if entry_idx:
            holding_days = len(df) - entry_idx
            if holding_days >= self.config.max_holding_days:
                # 清除记录
                del self.entry_dates[stock_code]
                
                return Signal(
                    stock_code=stock_code,
                    signal_type='sell',
                    price=current_price,
                    reason=f"达到最大持仓天数{self.config.max_holding_days}天"
                )
        
        # 条件1：价格回归到布林带中轨附近
        near_middle = 0.4 <= current_bb_pos <= 0.6
        
        # 条件2：RSI 回归中性
        rsi_neutral = 40 <= current_rsi <= 60
        
        # 条件3：Z-Score 回归零附近
        zscore_neutral = abs(current_zscore) <= self.config.exit_zscore
        
        # 条件4：价格触及布林带上轨（止盈）
        touch_upper = current_bb_pos >= 0.9
        
        # 综合判断
        should_sell = False
        reason = ""
        
        if near_middle or rsi_neutral or zscore_neutral:
            should_sell = True
            reasons = []
            if near_middle:
                reasons.append("回归布林带中轨")
            if rsi_neutral:
                reasons.append(f"RSI回归中性({current_rsi:.1f})")
            if zscore_neutral:
                reasons.append(f"Z-Score回归({current_zscore:.2f})")
            reason = "; ".join(reasons)
        
        elif touch_upper:
            should_sell = True
            reason = f"触及布林带上轨，止盈"
        
        if should_sell:
            # 清除记录
            if stock_code in self.entry_dates:
                del self.entry_dates[stock_code]
            
            return Signal(
                stock_code=stock_code,
                signal_type='sell',
                price=current_price,
                reason=reason
            )
        
        return None


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI 均值回归策略
    
    单纯基于 RSI 的均值回归策略
    
    买入条件：RSI 低于超卖线
    卖出条件：RSI 回归中性或进入超买
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        exit_low: float = 50.0,
        exit_high: float = 80.0
    ):
        """
        初始化 RSI 均值回归策略
        
        Args:
            rsi_period: RSI 周期
            oversold: 超卖阈值
            overbought: 超买阈值
            exit_low: 买入后出场阈值（下限）
            exit_high: 买入后出场阈值（上限）
        """
        config = StrategyConfig(
            name="RSIMeanReversion",
            description="RSI均值回归策略"
        )
        super().__init__(config)
        
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.exit_low = exit_low
        self.exit_high = exit_high
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        for stock_code, df in data.items():
            if len(df) < self.rsi_period + 1:
                continue
            
            # 计算 RSI
            rsi = self.rsi(df['close'], self.rsi_period)
            
            current_rsi = rsi.iloc[-1]
            current_price = df['close'].iloc[-1]
            
            has_position = self.has_position(stock_code)
            
            if not has_position:
                # RSI 超卖买入
                if current_rsi <= self.oversold:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=current_price,
                        strength=1 - current_rsi / self.oversold,
                        reason=f"RSI超卖({current_rsi:.1f})"
                    ))
            else:
                # RSI 回归卖出
                if current_rsi >= self.exit_low or current_rsi >= self.exit_high:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=current_price,
                        reason=f"RSI回归({current_rsi:.1f})"
                    ))
        
        return signals


class BollingerBandsStrategy(BaseStrategy):
    """
    布林带均值回归策略
    
    单纯基于布林带的均值回归策略
    
    买入条件：价格触及下轨
    卖出条件：价格回归中轨或触及上轨
    """
    
    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0
    ):
        """
        初始化布林带策略
        
        Args:
            period: 周期
            std_dev: 标准差倍数
        """
        config = StrategyConfig(
            name="BollingerBands",
            description="布林带均值回归策略"
        )
        super().__init__(config)
        
        self.period = period
        self.std_dev = std_dev
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        for stock_code, df in data.items():
            if len(df) < self.period + 1:
                continue
            
            # 计算布林带
            upper, middle, lower = self.bollinger_bands(
                df['close'], self.period, self.std_dev
            )
            
            current_price = df['close'].iloc[-1]
            upper_val = upper.iloc[-1]
            middle_val = middle.iloc[-1]
            lower_val = lower.iloc[-1]
            
            has_position = self.has_position(stock_code)
            
            if not has_position:
                # 触及下轨买入
                if current_price <= lower_val:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=current_price,
                        reason=f"触及布林带下轨{lower_val:.2f}"
                    ))
            else:
                # 回归中轨或触及上轨卖出
                if current_price >= middle_val:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=current_price,
                        reason=f"回归布林带中轨{middle_val:.2f}"
                    ))
                elif current_price >= upper_val:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=current_price,
                        reason=f"触及布林带上轨{upper_val:.2f}"
                    ))
        
        return signals


class PairTradingStrategy(BaseStrategy):
    """
    配对交易策略
    
    两种相关性较高的资产之间的均值回归策略
    
    策略原理：
    1. 找到相关性高的配对
    2. 计算价差或比率
    3. 价差偏离时做空高估、做多低估
    4. 价差回归时平仓
    """
    
    def __init__(
        self,
        lookback: int = 30,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.5
    ):
        """
        初始化配对交易策略
        
        Args:
            lookback: 回溯期
            entry_threshold: 入场阈值（标准差倍数）
            exit_threshold: 出场阈值
        """
        config = StrategyConfig(
            name="PairTrading",
            description="配对交易策略"
        )
        super().__init__(config)
        
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        生成交易信号
        
        注意：配对交易需要两只股票的数据
        """
        signals = []
        
        # 获取股票列表
        stock_codes = list(data.keys())
        
        if len(stock_codes) < 2:
            return signals
        
        # 简化：只处理第一对股票
        stock1, stock2 = stock_codes[0], stock_codes[1]
        
        df1, df2 = data[stock1], data[stock2]
        
        if len(df1) < self.lookback or len(df2) < self.lookback:
            return signals
        
        # 计算价格比率
        ratio = df1['close'] / df2['close']
        
        # 计算 Z-Score
        mean = ratio.rolling(self.lookback).mean()
        std = ratio.rolling(self.lookback).std()
        zscore = (ratio - mean) / std
        
        current_zscore = zscore.iloc[-1]
        current_price1 = df1['close'].iloc[-1]
        current_price2 = df2['close'].iloc[-1]
        
        # 判断信号
        if current_zscore > self.entry_threshold:
            # ratio 过高，做空 stock1，做多 stock2
            signals.append(Signal(
                stock_code=stock1,
                signal_type='sell',
                price=current_price1,
                reason=f"配对交易：做空，Z-Score={current_zscore:.2f}"
            ))
            signals.append(Signal(
                stock_code=stock2,
                signal_type='buy',
                price=current_price2,
                reason=f"配对交易：做多，Z-Score={current_zscore:.2f}"
            ))
        
        elif current_zscore < -self.entry_threshold:
            # ratio 过低，做多 stock1，做空 stock2
            signals.append(Signal(
                stock_code=stock1,
                signal_type='buy',
                price=current_price1,
                reason=f"配对交易：做多，Z-Score={current_zscore:.2f}"
            ))
            signals.append(Signal(
                stock_code=stock2,
                signal_type='sell',
                price=current_price2,
                reason=f"配对交易：做空，Z-Score={current_zscore:.2f}"
            ))
        
        elif abs(current_zscore) < self.exit_threshold:
            # 回归均值，平仓
            if self.has_position(stock1):
                signals.append(Signal(
                    stock_code=stock1,
                    signal_type='sell',
                    price=current_price1,
                    reason="配对交易：平仓"
                ))
            if self.has_position(stock2):
                signals.append(Signal(
                    stock_code=stock2,
                    signal_type='sell',
                    price=current_price2,
                    reason="配对交易：平仓"
                ))
        
        return signals


if __name__ == "__main__":
    # 测试均值回归策略
    print("=" * 60)
    print("测试均值回归策略")
    print("=" * 60)
    
    # 创建测试数据（震荡行情）
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
    
    data = {'000001.SZ': df}
    
    # 测试均值回归策略
    print("\n【测试均值回归策略】")
    strategy = MeanReversionStrategy()
    signals = strategy.generate_signals(data)
    
    print(f"生成信号数量: {len(signals)}")
    for signal in signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    # 测试布林带策略
    print("\n【测试布林带策略】")
    bb_strategy = BollingerBandsStrategy()
    bb_signals = bb_strategy.generate_signals(data)
    
    print(f"生成信号数量: {len(bb_signals)}")
    for signal in bb_signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    print("\n" + "=" * 60)
    print("均值回归策略测试完成！")
    print("=" * 60)