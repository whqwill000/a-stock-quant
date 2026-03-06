"""
套利策略

基于价格差异的套利交易策略
包括统计套利、期现套利、跨市场套利等

策略原理：
1. 发现价格偏离均衡关系的资产对
2. 做多低估资产，做空高估资产
3. 等待价格回归均衡时获利
4. 风险相对较低，收益稳定

使用方法:
    from strategies.arbitrage import StatisticalArbitrageStrategy
    
    strategy = StatisticalArbitrageStrategy()
    signals = strategy.generate_signals(data)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# 导入项目模块
from strategies.base import BaseStrategy, StrategyConfig, Signal
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class ArbitrageConfig(StrategyConfig):
    """
    套利策略配置
    
    Attributes:
        lookback: 回溯期
        entry_zscore: 入场Z-Score阈值
        exit_zscore: 出场Z-Score阈值
        max_holding_days: 最大持仓天数
        min_correlation: 最小相关性要求
    """
    
    name: str = "Arbitrage"
    description: str = "套利策略"
    lookback: int = 60
    entry_zscore: float = 2.0
    exit_zscore: float = 0.5
    max_holding_days: int = 20
    min_correlation: float = 0.7


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    统计套利策略
    
    基于协整关系的配对交易策略
    
    策略原理：
    1. 找到具有协整关系的股票对
    2. 计算价差或比率的Z-Score
    3. Z-Score偏离时开仓
    4. Z-Score回归时平仓
    
    Attributes:
        config: 策略配置
        pairs: 配对列表
        positions: 当前持仓
    """
    
    def __init__(self, config: Optional[ArbitrageConfig] = None):
        """
        初始化统计套利策略
        
        Args:
            config: 策略配置
        """
        super().__init__(config or ArbitrageConfig())
        
        # 配对列表
        self.pairs: List[Tuple[str, str]] = []
        
        # 入场记录
        self.entry_info: Dict[str, dict] = {}
    
    def find_pairs(
        self,
        data: Dict[str, pd.DataFrame],
        top_n: int = 5
    ) -> List[Tuple[str, str, float]]:
        """
        寻找配对
        
        基于相关性和协整关系筛选配对
        
        Args:
            data: 数据字典
            top_n: 返回前N对
            
        Returns:
            配对列表 [(股票1, 股票2, 相关性)]
        """
        pairs = []
        stock_codes = list(data.keys())
        
        for i in range(len(stock_codes)):
            for j in range(i + 1, len(stock_codes)):
                code1, code2 = stock_codes[i], stock_codes[j]
                
                df1, df2 = data[code1], data[code2]
                
                if len(df1) < self.config.lookback or len(df2) < self.config.lookback:
                    continue
                
                # 对齐日期
                common_idx = df1.index.intersection(df2.index)
                if len(common_idx) < self.config.lookback:
                    continue
                
                close1 = df1.loc[common_idx, 'close']
                close2 = df2.loc[common_idx, 'close']
                
                # 计算相关性
                correlation = close1.corr(close2)
                
                if correlation >= self.config.min_correlation:
                    # 检验协整关系（简化版）
                    spread = close1 / close2
                    # 使用ADF检验的简化版本：检查价差的均值回归特性
                    spread_std = spread.std()
                    spread_mean = spread.mean()
                    current_deviation = abs(spread.iloc[-1] - spread_mean) / spread_std
                    
                    pairs.append((code1, code2, correlation, current_deviation))
        
        # 按相关性排序
        pairs.sort(key=lambda x: x[2], reverse=True)
        
        return pairs[:top_n]
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 数据字典
            
        Returns:
            信号列表
        """
        signals = []
        
        # 如果没有配对，先寻找配对
        if not self.pairs:
            pairs_info = self.find_pairs(data)
            self.pairs = [(p[0], p[1]) for p in pairs_info]
        
        # 遍历每个配对
        for pair in self.pairs:
            code1, code2 = pair
            
            if code1 not in data or code2 not in data:
                continue
            
            df1, df2 = data[code1], data[code2]
            
            if len(df1) < self.config.lookback or len(df2) < self.config.lookback:
                continue
            
            # 计算价差
            spread = df1['close'] / df2['close']
            
            # 计算Z-Score
            mean = spread.rolling(self.config.lookback).mean()
            std = spread.rolling(self.config.lookback).std()
            zscore = (spread - mean) / std
            
            current_zscore = zscore.iloc[-1]
            current_price1 = df1['close'].iloc[-1]
            current_price2 = df2['close'].iloc[-1]
            
            pair_key = f"{code1}_{code2}"
            
            # 检查是否有持仓
            has_position = pair_key in self.entry_info
            
            if not has_position:
                # 开仓条件
                if current_zscore > self.config.entry_zscore:
                    # 价差过高，做空股票1，做多股票2
                    signals.append(Signal(
                        stock_code=code1,
                        signal_type='sell',
                        price=current_price1,
                        reason=f"配对套利: 做空，Z-Score={current_zscore:.2f}"
                    ))
                    signals.append(Signal(
                        stock_code=code2,
                        signal_type='buy',
                        price=current_price2,
                        reason=f"配对套利: 做多，Z-Score={current_zscore:.2f}"
                    ))
                    
                    self.entry_info[pair_key] = {
                        'entry_date': df1['date'].iloc[-1],
                        'entry_zscore': current_zscore,
                        'direction': 'short_spread'
                    }
                
                elif current_zscore < -self.config.entry_zscore:
                    # 价差过低，做多股票1，做空股票2
                    signals.append(Signal(
                        stock_code=code1,
                        signal_type='buy',
                        price=current_price1,
                        reason=f"配对套利: 做多，Z-Score={current_zscore:.2f}"
                    ))
                    signals.append(Signal(
                        stock_code=code2,
                        signal_type='sell',
                        price=current_price2,
                        reason=f"配对套利: 做空，Z-Score={current_zscore:.2f}"
                    ))
                    
                    self.entry_info[pair_key] = {
                        'entry_date': df1['date'].iloc[-1],
                        'entry_zscore': current_zscore,
                        'direction': 'long_spread'
                    }
            
            else:
                # 平仓条件
                entry = self.entry_info[pair_key]
                
                # 检查持有天数
                entry_date = entry['entry_date']
                current_date = df1['date'].iloc[-1]
                holding_days = (pd.to_datetime(current_date) - pd.to_datetime(entry_date)).days
                
                should_close = False
                close_reason = ""
                
                # Z-Score回归
                if abs(current_zscore) < self.config.exit_zscore:
                    should_close = True
                    close_reason = f"Z-Score回归: {current_zscore:.2f}"
                
                # 超过最大持仓天数
                elif holding_days >= self.config.max_holding_days:
                    should_close = True
                    close_reason = f"持有期满: {holding_days}天"
                
                # 止损：Z-Score继续扩大
                elif entry['direction'] == 'short_spread' and current_zscore > entry['entry_zscore'] * 1.5:
                    should_close = True
                    close_reason = f"止损: Z-Score扩大"
                
                elif entry['direction'] == 'long_spread' and current_zscore < entry['entry_zscore'] * 1.5:
                    should_close = True
                    close_reason = f"止损: Z-Score扩大"
                
                if should_close:
                    # 平仓
                    if entry['direction'] == 'short_spread':
                        signals.append(Signal(
                            stock_code=code1,
                            signal_type='buy',
                            price=current_price1,
                            reason=f"配对套利平仓: {close_reason}"
                        ))
                        signals.append(Signal(
                            stock_code=code2,
                            signal_type='sell',
                            price=current_price2,
                            reason=f"配对套利平仓: {close_reason}"
                        ))
                    else:
                        signals.append(Signal(
                            stock_code=code1,
                            signal_type='sell',
                            price=current_price1,
                            reason=f"配对套利平仓: {close_reason}"
                        ))
                        signals.append(Signal(
                            stock_code=code2,
                            signal_type='buy',
                            price=current_price2,
                            reason=f"配对套利平仓: {close_reason}"
                        ))
                    
                    del self.entry_info[pair_key]
        
        return signals


class ETFArbitrageStrategy(BaseStrategy):
    """
    ETF套利策略
    
    基于ETF与其成分股之间的套利机会
    
    策略原理：
    1. 计算ETF的净值（基于成分股价格）
    2. 比较ETF价格与净值
    3. 价格偏离时进行套利
    """
    
    def __init__(
        self,
        deviation_threshold: float = 0.01,
        min_profit: float = 0.005
    ):
        """
        初始化ETF套利策略
        
        Args:
            deviation_threshold: 偏离阈值
            min_profit: 最小利润要求
        """
        config = StrategyConfig(
            name="ETFArbitrage",
            description="ETF套利策略"
        )
        super().__init__(config)
        
        self.deviation_threshold = deviation_threshold
        self.min_profit = min_profit
    
    def generate_signals(
        self,
        etf_data: pd.DataFrame,
        component_data: Dict[str, pd.DataFrame],
        weights: Dict[str, float]
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            etf_data: ETF数据
            component_data: 成分股数据
            weights: 成分股权重
        """
        signals = []
        
        if etf_data.empty or not component_data:
            return signals
        
        # 计算ETF净值
        nav = 0
        for stock_code, weight in weights.items():
            if stock_code in component_data:
                price = component_data[stock_code]['close'].iloc[-1]
                nav += price * weight
        
        # 获取ETF价格
        etf_price = etf_data['close'].iloc[-1]
        
        # 计算偏离度
        deviation = (etf_price - nav) / nav
        
        if deviation > self.deviation_threshold:
            # ETF溢价，卖出ETF，买入成分股
            signals.append(Signal(
                stock_code='ETF',
                signal_type='sell',
                price=etf_price,
                reason=f"ETF溢价套利: 偏离{deviation*100:.2f}%"
            ))
            
            for stock_code, weight in weights.items():
                if stock_code in component_data:
                    price = component_data[stock_code]['close'].iloc[-1]
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=price,
                        reason=f"ETF溢价套利: 买入成分股"
                    ))
        
        elif deviation < -self.deviation_threshold:
            # ETF折价，买入ETF，卖出成分股
            signals.append(Signal(
                stock_code='ETF',
                signal_type='buy',
                price=etf_price,
                reason=f"ETF折价套利: 偏离{deviation*100:.2f}%"
            ))
            
            for stock_code, weight in weights.items():
                if stock_code in component_data:
                    price = component_data[stock_code]['close'].iloc[-1]
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=price,
                        reason=f"ETF折价套利: 卖出成分股"
                    ))
        
        return signals


class ConvertibleBondArbitrageStrategy(BaseStrategy):
    """
    可转债套利策略
    
    基于可转债与正股之间的套利机会
    
    策略原理：
    1. 计算可转债的转股价值
    2. 比较可转债价格与转股价值
    3. 存在套利空间时进行交易
    """
    
    def __init__(
        self,
        min_premium: float = -0.02,
        max_premium: float = 0.10
    ):
        """
        初始化可转债套利策略
        
        Args:
            min_premium: 最小溢价率（负值表示折价）
            max_premium: 最大溢价率
        """
        config = StrategyConfig(
            name="ConvertibleBondArbitrage",
            description="可转债套利策略"
        )
        super().__init__(config)
        
        self.min_premium = min_premium
        self.max_premium = max_premium
    
    def generate_signals(
        self,
        bond_data: pd.DataFrame,
        stock_data: pd.DataFrame,
        conversion_ratio: float
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            bond_data: 可转债数据
            stock_data: 正股数据
            conversion_ratio: 转股比例
        """
        signals = []
        
        if bond_data.empty or stock_data.empty:
            return signals
        
        # 计算转股价值
        stock_price = stock_data['close'].iloc[-1]
        conversion_value = stock_price * conversion_ratio
        
        # 获取可转债价格
        bond_price = bond_data['close'].iloc[-1]
        
        # 计算溢价率
        premium = (bond_price - conversion_value) / conversion_value
        
        if premium < self.min_premium:
            # 可转债折价，买入可转债，转股套利
            signals.append(Signal(
                stock_code='BOND',
                signal_type='buy',
                price=bond_price,
                reason=f"可转债折价套利: 溢价率{premium*100:.2f}%"
            ))
        
        elif premium > self.max_premium:
            # 可转债溢价过高，可以考虑卖出
            signals.append(Signal(
                stock_code='BOND',
                signal_type='sell',
                price=bond_price,
                reason=f"可转债溢价过高: 溢价率{premium*100:.2f}%"
            ))
        
        return signals


class IndexFuturesArbitrageStrategy(BaseStrategy):
    """
    股指期货套利策略
    
    基于股指期货与现货之间的套利机会
    
    策略原理：
    1. 计算股指期货的理论价格
    2. 比较实际价格与理论价格
    3. 存在套利空间时进行期现套利
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        dividend_yield: float = 0.02,
        min_basis: float = 0.01
    ):
        """
        初始化股指期货套利策略
        
        Args:
            risk_free_rate: 无风险利率
            dividend_yield: 股息率
            min_basis: 最小基差要求
        """
        config = StrategyConfig(
            name="IndexFuturesArbitrage",
            description="股指期货套利策略"
        )
        super().__init__(config)
        
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield
        self.min_basis = min_basis
    
    def calculate_theoretical_price(
        self,
        spot_price: float,
        days_to_maturity: int
    ) -> float:
        """
        计算股指期货理论价格
        
        F = S * e^((r - q) * T)
        
        Args:
            spot_price: 现货价格
            days_to_maturity: 到期天数
            
        Returns:
            理论价格
        """
        T = days_to_maturity / 365
        theoretical_price = spot_price * np.exp(
            (self.risk_free_rate - self.dividend_yield) * T
        )
        return theoretical_price
    
    def generate_signals(
        self,
        futures_data: pd.DataFrame,
        spot_data: pd.DataFrame,
        days_to_maturity: int
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            futures_data: 期货数据
            spot_data: 现货数据
            days_to_maturity: 到期天数
        """
        signals = []
        
        if futures_data.empty or spot_data.empty:
            return signals
        
        # 获取价格
        futures_price = futures_data['close'].iloc[-1]
        spot_price = spot_data['close'].iloc[-1]
        
        # 计算理论价格
        theoretical_price = self.calculate_theoretical_price(
            spot_price, days_to_maturity
        )
        
        # 计算基差
        basis = (futures_price - theoretical_price) / theoretical_price
        
        if basis > self.min_basis:
            # 期货高估，卖期货买现货
            signals.append(Signal(
                stock_code='FUTURES',
                signal_type='sell',
                price=futures_price,
                reason=f"期现套利: 期货高估{basis*100:.2f}%"
            ))
            signals.append(Signal(
                stock_code='SPOT',
                signal_type='buy',
                price=spot_price,
                reason=f"期现套利: 买入现货"
            ))
        
        elif basis < -self.min_basis:
            # 期货低估，买期货卖现货
            signals.append(Signal(
                stock_code='FUTURES',
                signal_type='buy',
                price=futures_price,
                reason=f"期现套利: 期货低估{basis*100:.2f}%"
            ))
            signals.append(Signal(
                stock_code='SPOT',
                signal_type='sell',
                price=spot_price,
                reason=f"期现套利: 卖出现货"
            ))
        
        return signals


if __name__ == "__main__":
    # 测试套利策略
    print("=" * 60)
    print("测试套利策略")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    np.random.seed(42)
    
    # 创建两只相关性较高的股票
    base = 10 + np.cumsum(np.random.normal(0, 0.1, 100))
    
    data = {
        '000001.SZ': pd.DataFrame({
            'date': dates,
            'close': base,
            'high': base * 1.02,
            'low': base * 0.98,
            'open': base,
            'volume': np.random.randint(100000, 1000000, 100)
        }),
        '000002.SZ': pd.DataFrame({
            'date': dates,
            'close': base * 1.1 + np.random.normal(0, 0.2, 100),
            'high': base * 1.1 * 1.02,
            'low': base * 1.1 * 0.98,
            'open': base * 1.1,
            'volume': np.random.randint(100000, 1000000, 100)
        })
    }
    
    # 测试统计套利策略
    print("\n【测试统计套利策略】")
    strategy = StatisticalArbitrageStrategy()
    
    # 先寻找配对
    pairs = strategy.find_pairs(data)
    print(f"找到 {len(pairs)} 个配对")
    for pair in pairs:
        print(f"  {pair[0]} - {pair[1]}: 相关性={pair[2]:.3f}")
    
    # 生成信号
    signals = strategy.generate_signals(data)
    print(f"\n生成信号数量: {len(signals)}")
    for signal in signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    print("\n" + "=" * 60)
    print("套利策略测试完成！")
    print("=" * 60)