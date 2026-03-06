"""
动量策略

基于价格动量和盈余动量的交易策略
适用于趋势延续的市场环境

策略原理：
1. 过去表现好的股票未来表现也会好
2. 使用价格动量、盈余动量等指标
3. 买入强势股，卖出弱势股
4. 定期调仓

使用方法:
    from strategies.momentum import MomentumStrategy
    
    strategy = MomentumStrategy()
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
class MomentumConfig(StrategyConfig):
    """
    动量策略配置
    
    Attributes:
        lookback_period: 回溯期
        holding_period: 持有期
        top_n: 选股数量
        skip_period: 跳过期（避免短期反转）
        use_volume_filter: 是否使用成交量过滤
        min_volume_ratio: 最小成交量比率
    """
    
    name: str = "Momentum"
    description: str = "动量策略"
    lookback_period: int = 60
    holding_period: int = 20
    top_n: int = 10
    skip_period: int = 5
    use_volume_filter: bool = True
    min_volume_ratio: float = 1.5


class MomentumStrategy(BaseStrategy):
    """
    动量策略
    
    基于价格动量的选股策略
    
    买入条件：
    1. 过去 N 天收益率排名靠前
    2. 成交量放大（可选）
    3. 价格处于上升趋势
    
    卖出条件：
    1. 持有期满
    2. 动量衰减
    3. 价格趋势反转
    
    Attributes:
        config: 策略配置
        entry_dates: 入场日期记录
    """
    
    def __init__(self, config: Optional[MomentumConfig] = None):
        """
        初始化动量策略
        
        Args:
            config: 策略配置
        """
        super().__init__(config or MomentumConfig())
        
        self.entry_dates: Dict[str, datetime] = {}
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 数据字典 {股票代码: DataFrame}
            
        Returns:
            信号列表
        """
        signals = []
        
        # 计算所有股票的动量得分
        momentum_scores = self._calculate_momentum_scores(data)
        
        if momentum_scores.empty:
            return signals
        
        # 排序选择动量最强的股票
        sorted_stocks = momentum_scores.sort_values(ascending=False)
        top_stocks = sorted_stocks.head(self.config.top_n).index.tolist()
        
        # 生成信号
        for stock_code in top_stocks:
            if stock_code not in data:
                continue
            
            df = data[stock_code]
            current_price = df['close'].iloc[-1]
            
            # 检查是否已持有
            if self.has_position(stock_code):
                continue
            
            # 检查成交量过滤
            if self.config.use_volume_filter:
                if not self._check_volume_filter(df):
                    continue
            
            # 买入信号
            signals.append(Signal(
                stock_code=stock_code,
                signal_type='buy',
                price=current_price,
                strength=momentum_scores[stock_code] / momentum_scores.max(),
                reason=f"动量得分: {momentum_scores[stock_code]:.4f}"
            ))
            
            # 记录入场日期
            self.entry_dates[stock_code] = df['date'].iloc[-1]
        
        # 检查卖出信号
        for stock_code in list(self.positions.keys()):
            if stock_code not in data:
                continue
            
            df = data[stock_code]
            current_price = df['close'].iloc[-1]
            
            # 检查持有期
            if self._should_exit(stock_code, df):
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='sell',
                    price=current_price,
                    reason="持有期满或动量衰减"
                ))
                
                # 清除入场记录
                if stock_code in self.entry_dates:
                    del self.entry_dates[stock_code]
        
        return signals
    
    def _calculate_momentum_scores(
        self,
        data: Dict[str, pd.DataFrame]
    ) -> pd.Series:
        """
        计算动量得分
        
        Args:
            data: 数据字典
            
        Returns:
            动量得分 Series
        """
        scores = {}
        
        for stock_code, df in data.items():
            if len(df) < self.config.lookback_period + self.config.skip_period:
                continue
            
            close = df['close']
            
            # 计算动量（跳过最近几天，避免短期反转）
            # 使用 t-skip 到 t-lookback 的收益率
            end_idx = -self.config.skip_period if self.config.skip_period > 0 else None
            start_idx = -self.config.lookback_period - self.config.skip_period
            
            if start_idx == 0:
                momentum = close.iloc[end_idx] / close.iloc[0] - 1
            else:
                momentum = close.iloc[end_idx] / close.iloc[start_idx] - 1
            
            scores[stock_code] = momentum
        
        return pd.Series(scores)
    
    def _check_volume_filter(self, df: pd.DataFrame) -> bool:
        """
        检查成交量过滤条件
        
        Args:
            df: K 线数据
            
        Returns:
            是否通过过滤
        """
        if 'volume' not in df.columns:
            return True
        
        # 计算平均成交量
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        # 当前成交量应大于平均成交量的一定比例
        return current_volume >= avg_volume * self.config.min_volume_ratio
    
    def _should_exit(self, stock_code: str, df: pd.DataFrame) -> bool:
        """
        判断是否应该退出
        
        Args:
            stock_code: 股票代码
            df: K 线数据
            
        Returns:
            是否应该退出
        """
        if stock_code not in self.entry_dates:
            return True
        
        entry_date = self.entry_dates[stock_code]
        current_date = df['date'].iloc[-1]
        
        # 计算持有天数
        holding_days = (pd.to_datetime(current_date) - 
                       pd.to_datetime(entry_date)).days
        
        # 持有期满
        if holding_days >= self.config.holding_period:
            return True
        
        # 检查动量是否衰减
        if len(df) >= 10:
            recent_return = df['close'].pct_change(5).iloc[-1]
            if recent_return < -0.05:  # 近5天下跌超过5%
                return True
        
        return False


class PriceMomentumStrategy(BaseStrategy):
    """
    价格动量策略
    
    基于多种价格动量指标的组合策略
    """
    
    def __init__(
        self,
        lookback_periods: List[int] = None,
        weights: List[float] = None,
        top_n: int = 10
    ):
        """
        初始化价格动量策略
        
        Args:
            lookback_periods: 回溯期列表
            weights: 各期权重
            top_n: 选股数量
        """
        config = StrategyConfig(
            name="PriceMomentum",
            description="价格动量策略"
        )
        super().__init__(config)
        
        self.lookback_periods = lookback_periods or [20, 60, 120]
        self.weights = weights or [0.2, 0.4, 0.4]
        self.top_n = top_n
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        # 计算综合动量得分
        scores = {}
        
        for stock_code, df in data.items():
            if len(df) < max(self.lookback_periods):
                continue
            
            close = df['close']
            total_score = 0
            
            for period, weight in zip(self.lookback_periods, self.weights):
                # 计算收益率
                ret = close.pct_change(period).iloc[-1]
                
                # 计算风险调整收益（夏普）
                returns = close.pct_change().iloc[-period:]
                sharpe = returns.mean() / (returns.std() + 1e-10) * np.sqrt(252)
                
                # 综合得分
                total_score += weight * (ret + sharpe * 0.1)
            
            scores[stock_code] = total_score
        
        if not scores:
            return signals
        
        # 排序选股
        sorted_scores = pd.Series(scores).sort_values(ascending=False)
        selected = sorted_scores.head(self.top_n).index.tolist()
        
        # 生成买入信号
        for stock_code in selected:
            if stock_code in data:
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    reason=f"价格动量选股，得分: {scores[stock_code]:.4f}"
                ))
        
        return signals


class EarningsMomentumStrategy(BaseStrategy):
    """
    盈余动量策略
    
    基于盈利预期修正的动量策略
    """
    
    def __init__(
        self,
        lookback_quarters: int = 4,
        top_n: int = 10
    ):
        """
        初始化盈余动量策略
        
        Args:
            lookback_quarters: 回溯季度数
            top_n: 选股数量
        """
        config = StrategyConfig(
            name="EarningsMomentum",
            description="盈余动量策略"
        )
        super().__init__(config)
        
        self.lookback_quarters = lookback_quarters
        self.top_n = top_n
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        earnings_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            earnings_data: 盈利数据（可选）
        """
        signals = []
        
        # 如果没有盈利数据，使用简化的价格动量
        if earnings_data is None:
            logger.warning("未提供盈利数据，使用价格动量替代")
            return self._use_price_momentum(data)
        
        # 计算盈余动量
        scores = {}
        
        for stock_code, df in earnings_data.items():
            if 'eps' not in df.columns or len(df) < self.lookback_quarters:
                continue
            
            # 计算盈利增长
            eps = df['eps']
            growth = eps.pct_change().iloc[-self.lookback_quarters:]
            
            # 盈利惊喜（实际 vs 预期）
            if 'eps_estimate' in df.columns:
                surprise = (eps - df['eps_estimate']) / df['eps_estimate']
                surprise_score = surprise.iloc[-1]
            else:
                surprise_score = 0
            
            # 综合得分
            scores[stock_code] = growth.mean() + surprise_score * 0.5
        
        if not scores:
            return signals
        
        # 排序选股
        sorted_scores = pd.Series(scores).sort_values(ascending=False)
        selected = sorted_scores.head(self.top_n).index.tolist()
        
        # 生成买入信号
        for stock_code in selected:
            if stock_code in data:
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    reason=f"盈余动量选股"
                ))
        
        return signals
    
    def _use_price_momentum(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """使用价格动量作为替代"""
        signals = []
        
        scores = {}
        for stock_code, df in data.items():
            if len(df) < 60:
                continue
            
            # 使用价格动量
            ret = df['close'].pct_change(60).iloc[-1]
            scores[stock_code] = ret
        
        if not scores:
            return signals
        
        sorted_scores = pd.Series(scores).sort_values(ascending=False)
        selected = sorted_scores.head(self.top_n).index.tolist()
        
        for stock_code in selected:
            if stock_code in data:
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    reason="价格动量替代"
                ))
        
        return signals


class RelativeStrengthStrategy(BaseStrategy):
    """
    相对强度策略
    
    基于股票相对于基准的强度进行选股
    """
    
    def __init__(
        self,
        lookback: int = 60,
        top_n: int = 10,
        min_strength: float = 1.0
    ):
        """
        初始化相对强度策略
        
        Args:
            lookback: 回溯期
            top_n: 选股数量
            min_strength: 最小相对强度
        """
        config = StrategyConfig(
            name="RelativeStrength",
            description="相对强度策略"
        )
        super().__init__(config)
        
        self.lookback = lookback
        self.top_n = top_n
        self.min_strength = min_strength
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            benchmark_data: 基准数据
        """
        signals = []
        
        # 计算相对强度
        scores = {}
        
        for stock_code, df in data.items():
            if len(df) < self.lookback:
                continue
            
            # 计算股票收益率
            stock_return = df['close'].pct_change(self.lookback).iloc[-1]
            
            # 计算基准收益率
            if benchmark_data is not None and len(benchmark_data) >= self.lookback:
                benchmark_return = benchmark_data['close'].pct_change(self.lookback).iloc[-1]
            else:
                # 使用所有股票的平均作为基准
                all_returns = []
                for other_df in data.values():
                    if len(other_df) >= self.lookback:
                        all_returns.append(other_df['close'].pct_change(self.lookback).iloc[-1])
                benchmark_return = np.mean(all_returns) if all_returns else 0
            
            # 计算相对强度
            relative_strength = (1 + stock_return) / (1 + benchmark_return)
            
            if relative_strength >= self.min_strength:
                scores[stock_code] = relative_strength
        
        if not scores:
            return signals
        
        # 排序选股
        sorted_scores = pd.Series(scores).sort_values(ascending=False)
        selected = sorted_scores.head(self.top_n).index.tolist()
        
        # 生成买入信号
        for stock_code in selected:
            if stock_code in data:
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    strength=sorted_scores[stock_code] / sorted_scores.max(),
                    reason=f"相对强度: {sorted_scores[stock_code]:.2f}"
                ))
        
        return signals


class IndustryMomentumStrategy(BaseStrategy):
    """
    行业动量策略
    
    基于行业轮动的动量策略
    """
    
    def __init__(
        self,
        lookback: int = 20,
        top_industries: int = 3,
        stocks_per_industry: int = 3
    ):
        """
        初始化行业动量策略
        
        Args:
            lookback: 回溯期
            top_industries: 选择前N个行业
            stocks_per_industry: 每个行业选择股票数
        """
        config = StrategyConfig(
            name="IndustryMomentum",
            description="行业动量策略"
        )
        super().__init__(config)
        
        self.lookback = lookback
        self.top_industries = top_industries
        self.stocks_per_industry = stocks_per_industry
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        industry_mapping: Optional[Dict[str, str]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            industry_mapping: 股票-行业映射
        """
        signals = []
        
        if industry_mapping is None:
            # 如果没有行业映射，使用简化的动量策略
            logger.warning("未提供行业映射，使用简化动量策略")
            return self._simple_momentum(data)
        
        # 计算行业动量
        industry_returns = {}
        
        for stock_code, df in data.items():
            if len(df) < self.lookback:
                continue
            
            industry = industry_mapping.get(stock_code)
            if industry is None:
                continue
            
            ret = df['close'].pct_change(self.lookback).iloc[-1]
            
            if industry not in industry_returns:
                industry_returns[industry] = []
            industry_returns[industry].append(ret)
        
        # 计算行业平均收益
        industry_avg = {
            industry: np.mean(returns)
            for industry, returns in industry_returns.items()
        }
        
        # 选择动量最强的行业
        sorted_industries = pd.Series(industry_avg).sort_values(ascending=False)
        top_industries = sorted_industries.head(self.top_industries).index.tolist()
        
        # 在每个行业中选择股票
        for industry in top_industries:
            industry_stocks = [
                stock for stock, ind in industry_mapping.items()
                if ind == industry and stock in data
            ]
            
            # 计算行业内股票动量
            stock_scores = {}
            for stock_code in industry_stocks:
                df = data[stock_code]
                if len(df) >= self.lookback:
                    stock_scores[stock_code] = df['close'].pct_change(self.lookback).iloc[-1]
            
            # 选择行业内动量最强的股票
            sorted_stocks = pd.Series(stock_scores).sort_values(ascending=False)
            selected = sorted_stocks.head(self.stocks_per_industry).index.tolist()
            
            for stock_code in selected:
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    reason=f"行业动量: {industry}"
                ))
        
        return signals
    
    def _simple_momentum(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """简化动量策略"""
        signals = []
        
        scores = {}
        for stock_code, df in data.items():
            if len(df) >= self.lookback:
                scores[stock_code] = df['close'].pct_change(self.lookback).iloc[-1]
        
        if not scores:
            return signals
        
        sorted_scores = pd.Series(scores).sort_values(ascending=False)
        selected = sorted_scores.head(self.top_industries * self.stocks_per_industry).index.tolist()
        
        for stock_code in selected:
            price = data[stock_code]['close'].iloc[-1]
            signals.append(Signal(
                stock_code=stock_code,
                signal_type='buy',
                price=price,
                reason="简化动量选股"
            ))
        
        return signals


if __name__ == "__main__":
    # 测试动量策略
    print("=" * 60)
    print("测试动量策略")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=150, freq='B')
    np.random.seed(42)
    
    data = {}
    for i, code in enumerate(['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '000651.SZ']):
        # 模拟不同强度的趋势
        trend = np.linspace(10, 10 * (1 + 0.3 * (i - 2)), 150)
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
    
    # 测试动量策略
    print("\n【测试动量策略】")
    strategy = MomentumStrategy()
    signals = strategy.generate_signals(data)
    
    print(f"生成信号数量: {len(signals)}")
    for signal in signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    print("\n" + "=" * 60)
    print("动量策略测试完成！")
    print("=" * 60)