"""
策略基类模块

定义所有策略的基类和通用接口

使用方法:
    from strategies.base import BaseStrategy
    
    class MyStrategy(BaseStrategy):
        def generate_signals(self, data):
            # 实现信号生成逻辑
            pass
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np

# 导入项目模块
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class Signal:
    """
    交易信号数据类
    
    存储单个交易信号的信息
    
    Attributes:
        stock_code: 股票代码
        signal_type: 信号类型 ('buy', 'sell', 'hold')
        price: 信号价格
        strength: 信号强度 (0-1)
        reason: 信号原因
        timestamp: 信号时间
    """
    
    stock_code: str
    signal_type: str
    price: float = 0.0
    strength: float = 1.0
    reason: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def is_buy(self) -> bool:
        """是否为买入信号"""
        return self.signal_type == 'buy'
    
    @property
    def is_sell(self) -> bool:
        """是否为卖出信号"""
        return self.signal_type == 'sell'
    
    @property
    def is_hold(self) -> bool:
        """是否为持有信号"""
        return self.signal_type == 'hold'
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'signal_type': self.signal_type,
            'price': self.price,
            'strength': self.strength,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class StrategyConfig:
    """
    策略配置数据类
    
    存储策略的参数配置
    
    Attributes:
        name: 策略名称
        description: 策略描述
        version: 策略版本
        author: 作者
        params: 策略参数字典
    """
    
    name: str = "BaseStrategy"
    description: str = "策略基类"
    version: str = "1.0.0"
    author: str = ""
    params: Dict[str, Any] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.params is None:
            self.params = {}


class BaseStrategy(ABC):
    """
    策略基类
    
    所有策略必须继承此类并实现相关方法
    
    主要方法：
    - init(): 策略初始化
    - generate_signals(): 生成交易信号
    - on_bar(): K 线事件处理
    - on_tick(): Tick 事件处理
    
    Attributes:
        config: 策略配置
        data: 策略数据
        signals: 信号列表
    """
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        """
        初始化策略
        
        Args:
            config: 策略配置
        """
        self.config = config or StrategyConfig()
        self.data: Dict[str, pd.DataFrame] = {}
        self.signals: List[Signal] = []
        self.positions: Dict[str, int] = {}  # 当前持仓
        
        logger.info(f"策略初始化: {self.config.name} v{self.config.version}")
    
    def init(self) -> None:
        """
        策略初始化
        
        在回测开始前调用，用于准备数据等
        子类可以重写此方法
        """
        logger.info(f"策略 {self.config.name} 初始化完成")
    
    @abstractmethod
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        生成交易信号
        
        子类必须实现此方法
        
        Args:
            data: 数据字典 {股票代码: DataFrame}
            
        Returns:
            信号列表
        """
        pass
    
    def on_bar(self, bar: pd.Series) -> Optional[Signal]:
        """
        K 线事件处理
        
        每根 K 线到达时调用
        
        Args:
            bar: K 线数据
            
        Returns:
            交易信号（可选）
        """
        return None
    
    def on_tick(self, tick: Dict) -> Optional[Signal]:
        """
        Tick 事件处理
        
        每个 Tick 到达时调用
        
        Args:
            tick: Tick 数据
            
        Returns:
            交易信号（可选）
        """
        return None
    
    def on_order_filled(self, order: Dict) -> None:
        """
        订单成交事件处理
        
        Args:
            order: 成交订单信息
        """
        pass
    
    def on_order_cancelled(self, order: Dict) -> None:
        """
        订单撤销事件处理
        
        Args:
            order: 撤销订单信息
        """
        pass
    
    def set_data(self, data: Dict[str, pd.DataFrame]) -> None:
        """
        设置策略数据
        
        Args:
            data: 数据字典
        """
        self.data = data
    
    def add_signal(self, signal: Signal) -> None:
        """
        添加信号
        
        Args:
            signal: 交易信号
        """
        self.signals.append(signal)
        logger.debug(f"添加信号: {signal.signal_type} {signal.stock_code}")
    
    def clear_signals(self) -> None:
        """清空信号列表"""
        self.signals.clear()
    
    def get_signals(self) -> List[Signal]:
        """
        获取信号列表
        
        Returns:
            信号列表
        """
        return self.signals
    
    def get_buy_signals(self) -> List[Signal]:
        """
        获取买入信号
        
        Returns:
            买入信号列表
        """
        return [s for s in self.signals if s.is_buy]
    
    def get_sell_signals(self) -> List[Signal]:
        """
        获取卖出信号
        
        Returns:
            卖出信号列表
        """
        return [s for s in self.signals if s.is_sell]
    
    def update_position(self, stock_code: str, volume: int) -> None:
        """
        更新持仓
        
        Args:
            stock_code: 股票代码
            volume: 持仓数量（正数买入，负数卖出）
        """
        if stock_code not in self.positions:
            self.positions[stock_code] = 0
        
        self.positions[stock_code] += volume
        
        # 如果持仓为 0，删除记录
        if self.positions[stock_code] == 0:
            del self.positions[stock_code]
    
    def get_position(self, stock_code: str) -> int:
        """
        获取持仓数量
        
        Args:
            stock_code: 股票代码
            
        Returns:
            持仓数量
        """
        return self.positions.get(stock_code, 0)
    
    def has_position(self, stock_code: str) -> bool:
        """
        是否持有某股票
        
        Args:
            stock_code: 股票代码
            
        Returns:
            是否持有
        """
        return self.get_position(stock_code) > 0
    
    # ============================================================
    # 技术指标计算方法（供子类使用）
    # ============================================================
    
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """
        简单移动平均线
        
        Args:
            series: 数据序列
            period: 周期
            
        Returns:
            SMA 序列
        """
        return series.rolling(window=period).mean()
    
    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """
        指数移动平均线
        
        Args:
            series: 数据序列
            period: 周期
            
        Returns:
            EMA 序列
        """
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        相对强弱指标 (RSI)
        
        Args:
            series: 价格序列
            period: 周期
            
        Returns:
            RSI 序列
        """
        delta = series.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def macd(
        series: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD 指标
        
        Args:
            series: 价格序列
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            (MACD线, 信号线, 柱状图)
        """
        ema_fast = series.ewm(span=fast_period, adjust=False).mean()
        ema_slow = series.ewm(span=slow_period, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(
        series: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        布林带
        
        Args:
            series: 价格序列
            period: 周期
            std_dev: 标准差倍数
            
        Returns:
            (上轨, 中轨, 下轨)
        """
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        return upper, middle, lower
    
    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        平均真实波幅 (ATR)
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            period: 周期
            
        Returns:
            ATR 序列
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def kdj(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        KDJ 指标
        
        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            n: RSV 周期
            m1: K 值平滑周期
            m2: D 值平滑周期
            
        Returns:
            (K值, D值, J值)
        """
        # 计算 RSV
        low_n = low.rolling(window=n).min()
        high_n = high.rolling(window=n).max()
        
        rsv = (close - low_n) / (high_n - low_n) * 100
        
        # 计算 K、D、J
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        return k, d, j
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        能量潮指标 (OBV)
        
        Args:
            close: 收盘价序列
            volume: 成交量序列
            
        Returns:
            OBV 序列
        """
        direction = np.where(close > close.shift(1), 1, 
                            np.where(close < close.shift(1), -1, 0))
        obv = (volume * direction).cumsum()
        
        return pd.Series(obv, index=close.index)
    
    @staticmethod
    def cross_above(series1: pd.Series, series2: pd.Series) -> pd.Series:
        """
        金叉判断
        
        判断 series1 是否上穿 series2
        
        Args:
            series1: 第一条线
            series2: 第二条线
            
        Returns:
            布尔序列，True 表示发生金叉
        """
        return (series1.shift(1) <= series2.shift(1)) & (series1 > series2)
    
    @staticmethod
    def cross_below(series1: pd.Series, series2: pd.Series) -> pd.Series:
        """
        死叉判断
        
        判断 series1 是否下穿 series2
        
        Args:
            series1: 第一条线
            series2: 第二条线
            
        Returns:
            布尔序列，True 表示发生死叉
        """
        return (series1.shift(1) >= series2.shift(1)) & (series1 < series2)


# 导入 Tuple
from typing import Tuple


if __name__ == "__main__":
    # 测试策略基类
    print("=" * 60)
    print("测试策略基类模块")
    print("=" * 60)
    
    # 创建测试策略
    class TestStrategy(BaseStrategy):
        def generate_signals(self, data):
            signals = []
            
            for stock_code, df in data.items():
                if len(df) < 20:
                    continue
                
                # 计算 SMA
                sma5 = self.sma(df['close'], 5)
                sma20 = self.sma(df['close'], 20)
                
                # 金叉买入
                if self.cross_above(sma5, sma20).iloc[-1]:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=df['close'].iloc[-1],
                        reason='SMA5 上穿 SMA20'
                    ))
                
                # 死叉卖出
                if self.cross_below(sma5, sma20).iloc[-1]:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=df['close'].iloc[-1],
                        reason='SMA5 下穿 SMA20'
                    ))
            
            return signals
    
    # 创建策略实例
    config = StrategyConfig(
        name="TestStrategy",
        description="测试策略",
        params={'sma_short': 5, 'sma_long': 20}
    )
    
    strategy = TestStrategy(config)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    np.random.seed(42)
    
    prices = 10 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
    df = pd.DataFrame({
        'date': dates,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
        'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
        'low': prices * (1 + np.random.uniform(-0.02, 0, 100)),
        'close': prices,
        'volume': np.random.randint(100000, 1000000, 100)
    })
    
    data = {'000001.SZ': df}
    
    # 生成信号
    signals = strategy.generate_signals(data)
    
    print(f"\n生成信号数量: {len(signals)}")
    for signal in signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
    
    print("\n" + "=" * 60)
    print("策略基类模块测试完成！")
    print("=" * 60)