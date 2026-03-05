"""
趋势跟踪策略

基于均线、通道等趋势指标的趋势跟踪策略
适用于明显的上涨或下跌趋势行情

策略原理：
1. 使用均线判断趋势方向
2. 价格突破均线或通道时入场
3. 趋势反转时出场
4. 配合止损止盈控制风险

使用方法:
    from strategies.trend_following import TrendFollowingStrategy
    
    strategy = TrendFollowingStrategy()
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
class TrendFollowingConfig(StrategyConfig):
    """
    趋势跟踪策略配置
    
    Attributes:
        ma_short: 短期均线周期
        ma_long: 长期均线周期
        ma_type: 均线类型 ('sma', 'ema')
        stop_loss_ratio: 止损比例
        take_profit_ratio: 止盈比例
        atr_period: ATR 周期
        atr_multiplier: ATR 倍数（用于止损）
        use_trailing_stop: 是否使用移动止损
    """
    
    name: str = "TrendFollowing"
    description: str = "趋势跟踪策略"
    ma_short: int = 5
    ma_long: int = 20
    ma_type: str = "ema"
    stop_loss_ratio: float = 0.05
    take_profit_ratio: float = 0.15
    atr_period: int = 14
    atr_multiplier: float = 2.0
    use_trailing_stop: bool = True


class TrendFollowingStrategy(BaseStrategy):
    """
    趋势跟踪策略
    
    基于均线交叉的趋势跟踪策略
    
    买入条件：
    1. 短期均线上穿长期均线（金叉）
    2. 价格位于长期均线之上
    3. 成交量放大（可选）
    
    卖出条件：
    1. 短期均线下穿长期均线（死叉）
    2. 价格跌破长期均线
    3. 触发止损或止盈
    
    Attributes:
        config: 策略配置
        entry_prices: 入场价格记录
        highest_prices: 最高价记录（用于移动止损）
    """
    
    def __init__(self, config: Optional[TrendFollowingConfig] = None):
        """
        初始化趋势跟踪策略
        
        Args:
            config: 策略配置
        """
        super().__init__(config or TrendFollowingConfig())
        
        # 入场价格记录
        self.entry_prices: Dict[str, float] = {}
        
        # 最高价记录（用于移动止损）
        self.highest_prices: Dict[str, float] = {}
    
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
            if len(df) < self.config.ma_long + 10:
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
            high = df['high']
            low = df['low']
            
            # 计算均线
            if self.config.ma_type == 'ema':
                ma_short = self.ema(close, self.config.ma_short)
                ma_long = self.ema(close, self.config.ma_long)
            else:
                ma_short = self.sma(close, self.config.ma_short)
                ma_long = self.sma(close, self.config.ma_long)
            
            # 计算 ATR
            atr = self.atr(high, low, close, self.config.atr_period)
            
            # 计算趋势强度（ADX 简化版）
            trend_strength = self._calculate_trend_strength(df)
            
            return {
                'ma_short': ma_short,
                'ma_long': ma_long,
                'atr': atr,
                'trend_strength': trend_strength,
                'close': close,
                'high': high,
                'low': low
            }
            
        except Exception as e:
            logger.error(f"计算指标失败: {e}")
            return None
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """
        计算趋势强度（简化版 ADX）
        
        Args:
            df: K 线数据
            
        Returns:
            趋势强度序列
        """
        close = df['close']
        high = df['high']
        low = df['low']
        
        # 计算 +DM 和 -DM
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # 计算 ATR
        atr = self.atr(high, low, close, 14)
        
        # 计算 +DI 和 -DI
        plus_di = 100 * pd.Series(plus_dm).rolling(14).mean() / atr
        minus_di = 100 * pd.Series(minus_dm).rolling(14).mean() / atr
        
        # 计算 DX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
        
        return dx
    
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
        ma_short = indicators['ma_short']
        ma_long = indicators['ma_long']
        atr = indicators['atr']
        close = indicators['close']
        
        # 获取最新值
        current_price = close.iloc[-1]
        ma_short_val = ma_short.iloc[-1]
        ma_long_val = ma_long.iloc[-1]
        atr_val = atr.iloc[-1]
        
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
        ma_short = indicators['ma_short']
        ma_long = indicators['ma_long']
        trend_strength = indicators['trend_strength']
        
        # 条件1：金叉
        golden_cross = self.cross_above(ma_short, ma_long).iloc[-1]
        
        # 条件2：价格在长期均线之上
        above_ma = current_price > ma_long.iloc[-1]
        
        # 条件3：趋势强度足够（可选）
        strong_trend = trend_strength.iloc[-1] > 20 if not pd.isna(trend_strength.iloc[-1]) else True
        
        if golden_cross and above_ma and strong_trend:
            # 记录入场价格
            self.entry_prices[stock_code] = current_price
            self.highest_prices[stock_code] = current_price
            
            # 计算止损价
            atr = indicators['atr']
            stop_loss = current_price - self.config.atr_multiplier * atr.iloc[-1]
            
            return Signal(
                stock_code=stock_code,
                signal_type='buy',
                price=current_price,
                strength=min(1.0, trend_strength.iloc[-1] / 50) if not pd.isna(trend_strength.iloc[-1]) else 0.5,
                reason=f"均线金叉，MA{self.config.ma_short}上穿MA{self.config.ma_long}"
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
        ma_short = indicators['ma_short']
        ma_long = indicators['ma_long']
        close = indicators['close']
        
        entry_price = self.entry_prices.get(stock_code, current_price)
        highest_price = self.highest_prices.get(stock_code, current_price)
        
        # 更新最高价
        if current_price > highest_price:
            self.highest_prices[stock_code] = current_price
            highest_price = current_price
        
        # 条件1：死叉
        death_cross = self.cross_below(ma_short, ma_long).iloc[-1]
        
        # 条件2：价格跌破长期均线
        below_ma = current_price < ma_long.iloc[-1]
        
        # 条件3：固定止损
        stop_loss_triggered = current_price <= entry_price * (1 - self.config.stop_loss_ratio)
        
        # 条件4：固定止盈
        take_profit_triggered = current_price >= entry_price * (1 + self.config.take_profit_ratio)
        
        # 条件5：移动止损
        trailing_stop_triggered = False
        if self.config.use_trailing_stop:
            trailing_stop_price = highest_price * (1 - self.config.stop_loss_ratio)
            trailing_stop_triggered = current_price <= trailing_stop_price
        
        # 判断是否卖出
        should_sell = False
        reason = ""
        
        if death_cross:
            should_sell = True
            reason = f"均线死叉，MA{self.config.ma_short}下穿MA{self.config.ma_long}"
        elif below_ma:
            should_sell = True
            reason = "价格跌破长期均线"
        elif stop_loss_triggered:
            should_sell = True
            reason = f"触发止损，亏损{(current_price/entry_price-1)*100:.2f}%"
        elif take_profit_triggered:
            should_sell = True
            reason = f"触发止盈，盈利{(current_price/entry_price-1)*100:.2f}%"
        elif trailing_stop_triggered:
            should_sell = True
            reason = f"触发移动止损，最高盈利{(highest_price/entry_price-1)*100:.2f}%"
        
        if should_sell:
            # 清除记录
            if stock_code in self.entry_prices:
                del self.entry_prices[stock_code]
            if stock_code in self.highest_prices:
                del self.highest_prices[stock_code]
            
            return Signal(
                stock_code=stock_code,
                signal_type='sell',
                price=current_price,
                reason=reason
            )
        
        return None


class DualThrustStrategy(BaseStrategy):
    """
    Dual Thrust 策略
    
    经典的日内突破策略，适合趋势行情
    
    策略原理：
    1. 根据前N日的最高价、最低价、收盘价计算区间
    2. 突破上轨买入，跌破下轨卖出
    3. 收盘前平仓（日内策略）
    
    Attributes:
        config: 策略配置
    """
    
    def __init__(
        self,
        n_days: int = 4,
        k1: float = 0.5,
        k2: float = 0.5
    ):
        """
        初始化 Dual Thrust 策略
        
        Args:
            n_days: 回溯天数
            k1: 上轨系数
            k2: 下轨系数
        """
        config = StrategyConfig(
            name="DualThrust",
            description="Dual Thrust 突破策略"
        )
        super().__init__(config)
        
        self.n_days = n_days
        self.k1 = k1
        self.k2 = k2
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        for stock_code, df in data.items():
            if len(df) < self.n_days + 1:
                continue
            
            # 计算区间
            hh = df['high'].rolling(self.n_days).max().iloc[-1]
            hc = df['close'].rolling(self.n_days).max().iloc[-1]
            lc = df['close'].rolling(self.n_days).min().iloc[-1]
            ll = df['low'].rolling(self.n_days).min().iloc[-1]
            
            range_val = max(hh - lc, hc - ll)
            
            # 计算上下轨
            open_price = df['open'].iloc[-1]
            upper = open_price + self.k1 * range_val
            lower = open_price - self.k2 * range_val
            
            current_price = df['close'].iloc[-1]
            current_high = df['high'].iloc[-1]
            current_low = df['low'].iloc[-1]
            
            # 判断信号
            has_position = self.has_position(stock_code)
            
            if not has_position:
                # 突破上轨买入
                if current_high > upper:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=current_price,
                        reason=f"突破上轨 {upper:.2f}"
                    ))
            else:
                # 跌破下轨卖出
                if current_low < lower:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=current_price,
                        reason=f"跌破下轨 {lower:.2f}"
                    ))
        
        return signals


class DonchianChannelStrategy(BaseStrategy):
    """
    唐奇安通道策略
    
    经典的趋势跟踪策略，海龟交易法则的核心
    
    策略原理：
    1. 计算N日最高价和最低价形成通道
    2. 突破上轨买入
    3. 跌破下轨卖出
    
    Attributes:
        entry_period: 入场周期
        exit_period: 出场周期
    """
    
    def __init__(
        self,
        entry_period: int = 20,
        exit_period: int = 10
    ):
        """
        初始化唐奇安通道策略
        
        Args:
            entry_period: 入场周期（突破周期）
            exit_period: 出场周期（止损周期）
        """
        config = StrategyConfig(
            name="DonchianChannel",
            description="唐奇安通道策略"
        )
        super().__init__(config)
        
        self.entry_period = entry_period
        self.exit_period = exit_period
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        for stock_code, df in data.items():
            if len(df) < self.entry_period + 1:
                continue
            
            # 计算通道
            upper = df['high'].rolling(self.entry_period).max()
            lower = df['low'].rolling(self.exit_period).min()
            
            current_price = df['close'].iloc[-1]
            upper_val = upper.iloc[-1]
            lower_val = lower.iloc[-1]
            
            has_position = self.has_position(stock_code)
            
            if not has_position:
                # 突破上轨买入
                if current_price >= upper_val:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=current_price,
                        reason=f"突破{self.entry_period}日高点 {upper_val:.2f}"
                    ))
            else:
                # 跌破下轨卖出
                if current_price <= lower_val:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=current_price,
                        reason=f"跌破{self.exit_period}日低点 {lower_val:.2f}"
                    ))
        
        return signals


if __name__ == "__main__":
    # 测试趋势跟踪策略
    print("=" * 60)
    print("测试趋势跟踪策略")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    np.random.seed(42)
    
    # 模拟趋势行情
    trend = np.linspace(10, 15, 100)
    noise = np.random.normal(0, 0.5, 100)
    prices = trend + noise
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
        'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
        'low': prices * (1 + np.random.uniform(-0.02, 0, 100)),
        'close': prices,
        'volume': np.random.randint(100000, 1000000, 100)
    })
    
    data = {'000001.SZ': df}
    
    # 测试趋势跟踪策略
    print("\n【测试趋势跟踪策略】")
    strategy = TrendFollowingStrategy()
    signals = strategy.generate_signals(data)
    
    print(f"生成信号数量: {len(signals)}")
    for signal in signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    # 测试唐奇安通道策略
    print("\n【测试唐奇安通道策略】")
    dc_strategy = DonchianChannelStrategy(entry_period=20, exit_period=10)
    dc_signals = dc_strategy.generate_signals(data)
    
    print(f"生成信号数量: {len(dc_signals)}")
    for signal in dc_signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    print("\n" + "=" * 60)
    print("趋势跟踪策略测试完成！")
    print("=" * 60)