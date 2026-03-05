"""
资金流策略

基于资金流向的交易策略
包括北向资金、主力资金、散户资金等

策略原理：
1. 跟踪大资金（北向资金、主力资金）的流向
2. 大资金流入时买入
3. 大资金流出时卖出
4. 利用资金流向的领先性获利

使用方法:
    from strategies.capital_flow import CapitalFlowStrategy
    
    strategy = CapitalFlowStrategy()
    signals = strategy.generate_signals(data, flow_data)
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
class CapitalFlowConfig(StrategyConfig):
    """
    资金流策略配置
    
    Attributes:
        flow_threshold: 资金流阈值
        lookback_days: 回溯天数
        holding_days: 持有天数
        min_flow_ratio: 最小资金流比例
    """
    
    name: str = "CapitalFlow"
    description: str = "资金流策略"
    flow_threshold: float = 10000000  # 1000万
    lookback_days: int = 5
    holding_days: int = 10
    min_flow_ratio: float = 0.01


class CapitalFlowStrategy(BaseStrategy):
    """
    资金流策略
    
    基于资金流向的交易策略
    
    资金类型：
    1. 北向资金：外资通过港股通买入A股
    2. 主力资金：大单交易
    3. 散户资金：小单交易
    4. 融资融券：杠杆资金
    
    Attributes:
        config: 策略配置
        entry_dates: 入场日期记录
    """
    
    def __init__(self, config: Optional[CapitalFlowConfig] = None):
        """
        初始化资金流策略
        
        Args:
            config: 策略配置
        """
        super().__init__(config or CapitalFlowConfig())
        
        self.entry_dates: Dict[str, datetime] = {}
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        flow_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            flow_data: 资金流数据
            
        Returns:
            信号列表
        """
        signals = []
        
        if flow_data is None:
            logger.warning("未提供资金流数据")
            return signals
        
        for stock_code, df in data.items():
            if stock_code not in flow_data:
                continue
            
            flow_df = flow_data[stock_code]
            
            if len(flow_df) < self.config.lookback_days:
                continue
            
            # 计算资金流指标
            flow_signal = self._analyze_flow(flow_df)
            
            if flow_signal is None:
                continue
            
            current_price = df['close'].iloc[-1]
            
            # 检查是否已持有
            has_position = self.has_position(stock_code)
            
            if not has_position and flow_signal['direction'] == 'buy':
                # 资金流入，买入
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=current_price,
                    strength=flow_signal['strength'],
                    reason=f"资金流入: {flow_signal['reason']}"
                ))
                
                self.entry_dates[stock_code] = df['date'].iloc[-1]
            
            elif has_position:
                # 检查卖出条件
                sell_signal = self._check_sell(stock_code, df, flow_df)
                
                if sell_signal:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=current_price,
                        reason=sell_signal
                    ))
                    
                    if stock_code in self.entry_dates:
                        del self.entry_dates[stock_code]
        
        return signals
    
    def _analyze_flow(self, flow_df: pd.DataFrame) -> Optional[dict]:
        """
        分析资金流
        
        Args:
            flow_df: 资金流数据
            
        Returns:
            资金流信号
        """
        # 获取最近N天的资金流
        recent_flow = flow_df.tail(self.config.lookback_days)
        
        # 计算净流入
        if 'net_inflow' in recent_flow.columns:
            total_inflow = recent_flow['net_inflow'].sum()
        elif 'main_inflow' in recent_flow.columns:
            total_inflow = recent_flow['main_inflow'].sum()
        else:
            return None
        
        # 计算流入比例
        if 'amount' in recent_flow.columns:
            total_amount = recent_flow['amount'].sum()
            flow_ratio = total_inflow / total_amount if total_amount > 0 else 0
        else:
            flow_ratio = 0
        
        # 判断信号
        if total_inflow > self.config.flow_threshold:
            return {
                'direction': 'buy',
                'strength': min(1.0, total_inflow / (self.config.flow_threshold * 5)),
                'reason': f"近{self.config.lookback_days}日净流入{total_inflow/100000000:.2f}亿"
            }
        
        return None
    
    def _check_sell(
        self,
        stock_code: str,
        df: pd.DataFrame,
        flow_df: pd.DataFrame
    ) -> Optional[str]:
        """
        检查卖出条件
        
        Args:
            stock_code: 股票代码
            df: K 线数据
            flow_df: 资金流数据
            
        Returns:
            卖出原因
        """
        # 检查持有天数
        if stock_code in self.entry_dates:
            entry_date = self.entry_dates[stock_code]
            current_date = df['date'].iloc[-1]
            holding_days = (pd.to_datetime(current_date) - pd.to_datetime(entry_date)).days
            
            if holding_days >= self.config.holding_days:
                return f"持有期满: {holding_days}天"
        
        # 检查资金流出
        if 'net_inflow' in flow_df.columns:
            recent_outflow = flow_df['net_inflow'].tail(3).sum()
            
            if recent_outflow < -self.config.flow_threshold:
                return f"资金流出: 近3日净流出{abs(recent_outflow)/100000000:.2f}亿"
        
        return None


class NorthboundCapitalStrategy(BaseStrategy):
    """
    北向资金策略
    
    跟踪外资通过港股通买入A股的资金流向
    
    策略原理：
    1. 北向资金通常被视为"聪明钱"
    2. 北向资金持续流入预示后市看好
    3. 北向资金流入的股票通常表现较好
    """
    
    def __init__(
        self,
        min_holding_days: int = 5,
        flow_threshold: float = 50000000,
        top_n: int = 10
    ):
        """
        初始化北向资金策略
        
        Args:
            min_holding_days: 最小持有天数
            flow_threshold: 资金流阈值
            top_n: 选股数量
        """
        config = StrategyConfig(
            name="NorthboundCapital",
            description="北向资金策略"
        )
        super().__init__(config)
        
        self.min_holding_days = min_holding_days
        self.flow_threshold = flow_threshold
        self.top_n = top_n
        
        self.entry_dates: Dict[str, datetime] = {}
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        northbound_data: Optional[pd.DataFrame] = None,
        stock_holding_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            northbound_data: 北向资金总体数据
            stock_holding_data: 个股北向资金持股数据
        """
        signals = []
        
        # 检查北向资金总体流向
        if northbound_data is not None and not northbound_data.empty:
            total_flow = northbound_data['net_inflow'].tail(5).sum()
            
            # 北向资金整体流出时谨慎
            if total_flow < -self.flow_threshold * 10:
                logger.info(f"北向资金整体流出，谨慎操作")
                return signals
        
        # 分析个股北向资金持股变化
        if stock_holding_data is None:
            return signals
        
        flow_scores = {}
        
        for stock_code, holding_df in stock_holding_data.items():
            if stock_code not in data:
                continue
            
            if len(holding_df) < 5:
                continue
            
            # 计算持股变化
            holding_change = holding_df['shares'].diff()
            recent_change = holding_change.tail(5).sum()
            
            # 计算持股比例变化
            if 'holding_ratio' in holding_df.columns:
                ratio_change = holding_df['holding_ratio'].diff().tail(5).sum()
            else:
                ratio_change = 0
            
            # 综合得分
            if recent_change > 0:
                flow_scores[stock_code] = recent_change + ratio_change * 1000000
        
        if not flow_scores:
            return signals
        
        # 选择北向资金增持最多的股票
        sorted_stocks = pd.Series(flow_scores).sort_values(ascending=False)
        selected = sorted_stocks.head(self.top_n).index.tolist()
        
        # 生成买入信号
        for stock_code in selected:
            if stock_code in data:
                price = data[stock_code]['close'].iloc[-1]
                
                if not self.has_position(stock_code):
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=price,
                        reason=f"北向资金增持: {flow_scores[stock_code]/10000:.0f}万股"
                    ))
                    
                    self.entry_dates[stock_code] = data[stock_code]['date'].iloc[-1]
        
        # 检查卖出
        for stock_code in list(self.positions.keys()):
            if stock_code not in data:
                continue
            
            # 检查北向资金是否减持
            if stock_code in stock_holding_data:
                holding_df = stock_holding_data[stock_code]
                recent_change = holding_df['shares'].diff().tail(3).sum()
                
                if recent_change < 0:
                    price = data[stock_code]['close'].iloc[-1]
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=price,
                        reason=f"北向资金减持: {abs(recent_change)/10000:.0f}万股"
                    ))
                    
                    if stock_code in self.entry_dates:
                        del self.entry_dates[stock_code]
        
        return signals


class MainForceStrategy(BaseStrategy):
    """
    主力资金策略
    
    跟踪主力资金（大单）的流向
    
    策略原理：
    1. 主力资金代表机构和大户的交易
    2. 主力资金流入通常预示股价上涨
    3. 主力资金流出通常预示股价下跌
    """
    
    def __init__(
        self,
        large_order_threshold: float = 500000,
        lookback_days: int = 5,
        top_n: int = 10
    ):
        """
        初始化主力资金策略
        
        Args:
            large_order_threshold: 大单金额阈值
            lookback_days: 回溯天数
            top_n: 选股数量
        """
        config = StrategyConfig(
            name="MainForce",
            description="主力资金策略"
        )
        super().__init__(config)
        
        self.large_order_threshold = large_order_threshold
        self.lookback_days = lookback_days
        self.top_n = top_n
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        order_flow_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            order_flow_data: 订单流数据
        """
        signals = []
        
        if order_flow_data is None:
            return signals
        
        flow_scores = {}
        
        for stock_code, flow_df in order_flow_data.items():
            if stock_code not in data:
                continue
            
            if len(flow_df) < self.lookback_days:
                continue
            
            # 计算主力资金净流入
            if 'main_inflow' in flow_df.columns:
                main_inflow = flow_df['main_inflow'].tail(self.lookback_days).sum()
            elif 'large_buy' in flow_df.columns and 'large_sell' in flow_df.columns:
                main_inflow = (flow_df['large_buy'] - flow_df['large_sell']).tail(self.lookback_days).sum()
            else:
                continue
            
            # 计算主力资金流入比例
            if 'amount' in flow_df.columns:
                total_amount = flow_df['amount'].tail(self.lookback_days).sum()
                flow_ratio = main_inflow / total_amount if total_amount > 0 else 0
            else:
                flow_ratio = 0
            
            if main_inflow > self.large_order_threshold:
                flow_scores[stock_code] = main_inflow
        
        if not flow_scores:
            return signals
        
        # 选择主力资金流入最多的股票
        sorted_stocks = pd.Series(flow_scores).sort_values(ascending=False)
        selected = sorted_stocks.head(self.top_n).index.tolist()
        
        # 生成买入信号
        for stock_code in selected:
            if stock_code in data and not self.has_position(stock_code):
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    reason=f"主力资金流入: {flow_scores[stock_code]/100000000:.2f}亿"
                ))
        
        return signals


class MarginTradingStrategy(BaseStrategy):
    """
    融资融券策略
    
    跟踪融资融券余额变化
    
    策略原理：
    1. 融资余额增加表示看多
    2. 融券余额增加表示看空
    3. 融资融券差额变化反映市场情绪
    """
    
    def __init__(
        self,
        margin_change_threshold: float = 0.05,
        lookback_days: int = 5
    ):
        """
        初始化融资融券策略
        
        Args:
            margin_change_threshold: 余额变化阈值
            lookback_days: 回溯天数
        """
        config = StrategyConfig(
            name="MarginTrading",
            description="融资融券策略"
        )
        super().__init__(config)
        
        self.margin_change_threshold = margin_change_threshold
        self.lookback_days = lookback_days
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        margin_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            margin_data: 融资融券数据
        """
        signals = []
        
        if margin_data is None:
            return signals
        
        for stock_code, margin_df in margin_data.items():
            if stock_code not in data:
                continue
            
            if len(margin_df) < self.lookback_days:
                continue
            
            # 计算融资余额变化
            if 'financing_balance' in margin_df.columns:
                financing_change = margin_df['financing_balance'].pct_change(self.lookback_days).iloc[-1]
            else:
                financing_change = 0
            
            # 计算融券余额变化
            if 'short_balance' in margin_df.columns:
                short_change = margin_df['short_balance'].pct_change(self.lookback_days).iloc[-1]
            else:
                short_change = 0
            
            current_price = data[stock_code]['close'].iloc[-1]
            
            # 融资余额大幅增加，看多
            if financing_change > self.margin_change_threshold:
                if not self.has_position(stock_code):
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=current_price,
                        reason=f"融资余额增加: {financing_change*100:.1f}%"
                    ))
            
            # 融券余额大幅增加，看空
            elif short_change > self.margin_change_threshold:
                if self.has_position(stock_code):
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=current_price,
                        reason=f"融券余额增加: {short_change*100:.1f}%"
                    ))
        
        return signals


class SmartMoneyStrategy(BaseStrategy):
    """
    聪明钱策略
    
    综合多种资金流指标识别聪明钱的动向
    
    策略原理：
    1. 结合北向资金、主力资金、融资融券等
    2. 多个指标共振时信号更强
    3. 跟随聪明钱的交易方向
    """
    
    def __init__(
        self,
        weight_northbound: float = 0.4,
        weight_mainforce: float = 0.4,
        weight_margin: float = 0.2,
        min_score: float = 0.5,
        top_n: int = 10
    ):
        """
        初始化聪明钱策略
        
        Args:
            weight_northbound: 北向资金权重
            weight_mainforce: 主力资金权重
            weight_margin: 融资融券权重
            min_score: 最小得分要求
            top_n: 选股数量
        """
        config = StrategyConfig(
            name="SmartMoney",
            description="聪明钱策略"
        )
        super().__init__(config)
        
        self.weight_northbound = weight_northbound
        self.weight_mainforce = weight_mainforce
        self.weight_margin = weight_margin
        self.min_score = min_score
        self.top_n = top_n
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        northbound_data: Optional[Dict[str, pd.DataFrame]] = None,
        mainforce_data: Optional[Dict[str, pd.DataFrame]] = None,
        margin_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            northbound_data: 北向资金数据
            mainforce_data: 主力资金数据
            margin_data: 融资融券数据
        """
        signals = []
        
        # 计算各资金流得分
        scores = {}
        
        for stock_code in data.keys():
            score = 0
            
            # 北向资金得分
            if northbound_data and stock_code in northbound_data:
                nb_df = northbound_data[stock_code]
                if len(nb_df) >= 5 and 'shares' in nb_df.columns:
                    nb_change = nb_df['shares'].diff().tail(5).sum()
                    if nb_change > 0:
                        score += self.weight_northbound
            
            # 主力资金得分
            if mainforce_data and stock_code in mainforce_data:
                mf_df = mainforce_data[stock_code]
                if len(mf_df) >= 5 and 'main_inflow' in mf_df.columns:
                    mf_inflow = mf_df['main_inflow'].tail(5).sum()
                    if mf_inflow > 0:
                        score += self.weight_mainforce
            
            # 融资融券得分
            if margin_data and stock_code in margin_data:
                mg_df = margin_data[stock_code]
                if len(mg_df) >= 5 and 'financing_balance' in mg_df.columns:
                    mg_change = mg_df['financing_balance'].pct_change(5).iloc[-1]
                    if mg_change > 0:
                        score += self.weight_margin
            
            if score >= self.min_score:
                scores[stock_code] = score
        
        if not scores:
            return signals
        
        # 选择得分最高的股票
        sorted_scores = pd.Series(scores).sort_values(ascending=False)
        selected = sorted_scores.head(self.top_n).index.tolist()
        
        # 生成买入信号
        for stock_code in selected:
            if stock_code in data and not self.has_position(stock_code):
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    strength=scores[stock_code],
                    reason=f"聪明钱综合得分: {scores[stock_code]:.2f}"
                ))
        
        return signals


if __name__ == "__main__":
    # 测试资金流策略
    print("=" * 60)
    print("测试资金流策略")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    np.random.seed(42)
    
    data = {}
    flow_data = {}
    
    for code in ['000001.SZ', '000002.SZ', '600000.SH']:
        prices = 10 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
        
        data[code] = pd.DataFrame({
            'date': dates,
            'close': prices,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'open': prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })
        
        # 模拟资金流数据
        flow_data[code] = pd.DataFrame({
            'date': dates,
            'net_inflow': np.random.uniform(-50000000, 100000000, 100),
            'main_inflow': np.random.uniform(-30000000, 60000000, 100),
            'amount': np.random.uniform(100000000, 500000000, 100)
        })
    
    # 测试资金流策略
    print("\n【测试资金流策略】")
    strategy = CapitalFlowStrategy()
    signals = strategy.generate_signals(data, flow_data)
    
    print(f"生成信号数量: {len(signals)}")
    for signal in signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    print("\n" + "=" * 60)
    print("资金流策略测试完成！")
    print("=" * 60)