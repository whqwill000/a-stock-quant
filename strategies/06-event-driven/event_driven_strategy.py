"""
事件驱动策略

基于特定事件的交易策略
包括财报事件、分析师评级、股权事件等

策略原理：
1. 监控市场事件
2. 分析事件对价格的影响
3. 在事件发生前后进行交易
4. 利用事件驱动的价格波动获利

使用方法:
    from strategies.event_driven import EventDrivenStrategy
    
    strategy = EventDrivenStrategy()
    signals = strategy.generate_signals(data, events)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 导入项目模块
from strategies.base import BaseStrategy, StrategyConfig, Signal
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class Event:
    """
    事件数据类
    
    Attributes:
        event_id: 事件ID
        event_type: 事件类型
        stock_code: 股票代码
        event_date: 事件日期
        data: 事件数据
        impact: 预期影响
    """
    
    event_id: str
    event_type: str
    stock_code: str
    event_date: datetime
    data: Dict = None
    impact: float = 0.0
    
    def __post_init__(self):
        """初始化后处理"""
        if self.data is None:
            self.data = {}


@dataclass
class EventDrivenConfig(StrategyConfig):
    """
    事件驱动策略配置
    
    Attributes:
        event_types: 关注的事件类型
        pre_event_days: 事件前建仓天数
        post_event_days: 事件后持仓天数
        min_impact: 最小影响阈值
    """
    
    name: str = "EventDriven"
    description: str = "事件驱动策略"
    event_types: List[str] = None
    pre_event_days: int = 5
    post_event_days: int = 10
    min_impact: float = 0.02
    
    def __post_init__(self):
        """初始化后处理"""
        if self.event_types is None:
            self.event_types = [
                'earnings',      # 财报发布
                'dividend',      # 分红
                'analyst',       # 分析师评级
                'insider',       # 内部人交易
                'block_trade',   # 大宗交易
                'repurchase'     # 股票回购
            ]


class EventDrivenStrategy(BaseStrategy):
    """
    事件驱动策略
    
    基于市场事件的交易策略
    
    主要事件类型：
    1. 财报事件：业绩超预期/不及预期
    2. 分红事件：分红公告
    3. 分析师事件：评级调整
    4. 内部人事件：高管增减持
    5. 大宗交易：大宗交易信息
    
    Attributes:
        config: 策略配置
        pending_events: 待处理事件
        active_positions: 活跃持仓
    """
    
    def __init__(self, config: Optional[EventDrivenConfig] = None):
        """
        初始化事件驱动策略
        
        Args:
            config: 策略配置
        """
        super().__init__(config or EventDrivenConfig())
        
        # 待处理事件
        self.pending_events: List[Event] = []
        
        # 活跃持仓
        self.active_positions: Dict[str, dict] = {}
    
    def add_event(self, event: Event) -> None:
        """
        添加事件
        
        Args:
            event: 事件对象
        """
        if event.event_type in self.config.event_types:
            self.pending_events.append(event)
            logger.info(f"添加事件: {event.event_type} - {event.stock_code}")
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        events: Optional[List[Event]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            events: 事件列表
            
        Returns:
            信号列表
        """
        signals = []
        
        # 添加新事件
        if events:
            for event in events:
                self.add_event(event)
        
        # 处理待处理事件
        signals.extend(self._process_events(data))
        
        # 检查持仓退出
        signals.extend(self._check_exit(data))
        
        return signals
    
    def _process_events(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        处理事件
        
        Args:
            data: K 线数据
            
        Returns:
            信号列表
        """
        signals = []
        
        for event in self.pending_events[:]:
            # 检查股票数据是否存在
            if event.stock_code not in data:
                continue
            
            df = data[event.stock_code]
            current_date = df['date'].iloc[-1]
            
            # 计算距离事件的天数
            days_to_event = (event.event_date - pd.to_datetime(current_date)).days
            
            # 事件前建仓
            if 0 < days_to_event <= self.config.pre_event_days:
                if abs(event.impact) >= self.config.min_impact:
                    signal_type = 'buy' if event.impact > 0 else 'sell'
                    
                    signals.append(Signal(
                        stock_code=event.stock_code,
                        signal_type=signal_type,
                        price=df['close'].iloc[-1],
                        strength=min(1.0, abs(event.impact) / 0.1),
                        reason=f"事件驱动: {event.event_type}, 预期影响: {event.impact*100:.1f}%"
                    ))
                    
                    # 记录持仓
                    self.active_positions[event.stock_code] = {
                        'event': event,
                        'entry_date': current_date,
                        'direction': signal_type
                    }
                    
                    # 移除已处理事件
                    self.pending_events.remove(event)
        
        return signals
    
    def _check_exit(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """
        检查持仓退出
        
        Args:
            data: K 线数据
            
        Returns:
            信号列表
        """
        signals = []
        
        for stock_code, position in list(self.active_positions.items()):
            if stock_code not in data:
                continue
            
            df = data[stock_code]
            current_date = df['date'].iloc[-1]
            event = position['event']
            
            # 计算持有天数
            entry_date = position['entry_date']
            holding_days = (pd.to_datetime(current_date) - pd.to_datetime(entry_date)).days
            
            # 事件后退出
            if holding_days >= self.config.post_event_days:
                exit_signal_type = 'sell' if position['direction'] == 'buy' else 'buy'
                
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type=exit_signal_type,
                    price=df['close'].iloc[-1],
                    reason=f"事件驱动: 事件后退出，持有{holding_days}天"
                ))
                
                del self.active_positions[stock_code]
        
        return signals


class EarningsAnnouncementStrategy(BaseStrategy):
    """
    财报公告策略
    
    基于财报公告的事件驱动策略
    
    策略原理：
    1. 在财报公告前买入预期好的股票
    2. 公告后根据实际与预期的差异调整
    3. 利用盈余公告后的价格漂移
    """
    
    def __init__(
        self,
        pre_announcement_days: int = 5,
        post_announcement_days: int = 3,
        surprise_threshold: float = 0.05
    ):
        """
        初始化财报公告策略
        
        Args:
            pre_announcement_days: 公告前建仓天数
            post_announcement_days: 公告后持仓天数
            surprise_threshold: 盈余惊喜阈值
        """
        config = StrategyConfig(
            name="EarningsAnnouncement",
            description="财报公告策略"
        )
        super().__init__(config)
        
        self.pre_announcement_days = pre_announcement_days
        self.post_announcement_days = post_announcement_days
        self.surprise_threshold = surprise_threshold
        
        # 公告日程
        self.announcement_schedule: Dict[str, datetime] = {}
        
        # 已处理公告
        self.processed_announcements: set = set()
    
    def set_announcement_schedule(
        self,
        schedule: Dict[str, datetime]
    ) -> None:
        """
        设置公告日程
        
        Args:
            schedule: 公告日程 {股票代码: 公告日期}
        """
        self.announcement_schedule = schedule
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        earnings_data: Optional[Dict[str, dict]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            earnings_data: 盈余数据
        """
        signals = []
        
        for stock_code, announcement_date in self.announcement_schedule.items():
            if stock_code not in data:
                continue
            
            df = data[stock_code]
            current_date = df['date'].iloc[-1]
            
            # 计算距离公告的天数
            days_to_announcement = (announcement_date - pd.to_datetime(current_date)).days
            
            # 公告前建仓
            if 0 < days_to_announcement <= self.pre_announcement_days:
                # 检查是否已处理
                event_key = f"{stock_code}_{announcement_date.strftime('%Y%m%d')}"
                if event_key in self.processed_announcements:
                    continue
                
                # 分析预期（简化：使用历史趋势）
                if len(df) >= 20:
                    recent_trend = df['close'].pct_change(20).iloc[-1]
                    
                    if recent_trend > 0:  # 近期上涨，预期正面
                        signals.append(Signal(
                            stock_code=stock_code,
                            signal_type='buy',
                            price=df['close'].iloc[-1],
                            reason=f"财报公告前建仓，公告日: {announcement_date.strftime('%Y-%m-%d')}"
                        ))
                        
                        self.processed_announcements.add(event_key)
            
            # 公告后根据盈余惊喜调整
            elif days_to_announcement < 0 and earnings_data:
                event_key = f"{stock_code}_{announcement_date.strftime('%Y%m%d')}_post"
                
                if event_key not in self.processed_announcements:
                    if stock_code in earnings_data:
                        earnings = earnings_data[stock_code]
                        
                        # 计算盈余惊喜
                        if 'actual' in earnings and 'expected' in earnings:
                            surprise = (earnings['actual'] - earnings['expected']) / abs(earnings['expected'])
                            
                            if surprise > self.surprise_threshold:
                                # 正面惊喜，买入
                                signals.append(Signal(
                                    stock_code=stock_code,
                                    signal_type='buy',
                                    price=df['close'].iloc[-1],
                                    reason=f"盈余惊喜: {surprise*100:.1f}%超预期"
                                ))
                            elif surprise < -self.surprise_threshold:
                                # 负面惊喜，卖出
                                signals.append(Signal(
                                    stock_code=stock_code,
                                    signal_type='sell',
                                    price=df['close'].iloc[-1],
                                    reason=f"盈余失望: {surprise*100:.1f}%低于预期"
                                ))
                            
                            self.processed_announcements.add(event_key)
        
        return signals


class AnalystRatingStrategy(BaseStrategy):
    """
    分析师评级策略
    
    基于分析师评级变化的事件驱动策略
    
    策略原理：
    1. 监控分析师评级变化
    2. 评级上调时买入
    3. 评级下调时卖出
    """
    
    def __init__(
        self,
        rating_change_threshold: int = 1,
        min_analysts: int = 3
    ):
        """
        初始化分析师评级策略
        
        Args:
            rating_change_threshold: 评级变化阈值
            min_analysts: 最少分析师数量
        """
        config = StrategyConfig(
            name="AnalystRating",
            description="分析师评级策略"
        )
        super().__init__(config)
        
        self.rating_change_threshold = rating_change_threshold
        self.min_analysts = min_analysts
        
        # 评级历史
        self.rating_history: Dict[str, List[dict]] = {}
    
    def update_ratings(
        self,
        stock_code: str,
        ratings: List[dict]
    ) -> None:
        """
        更新评级数据
        
        Args:
            stock_code: 股票代码
            ratings: 评级列表
        """
        self.rating_history[stock_code] = ratings
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        rating_changes: Optional[Dict[str, dict]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            rating_changes: 评级变化
        """
        signals = []
        
        if not rating_changes:
            return signals
        
        for stock_code, change in rating_changes.items():
            if stock_code not in data:
                continue
            
            df = data[stock_code]
            
            # 检查评级变化幅度
            old_rating = change.get('old_rating', 0)
            new_rating = change.get('new_rating', 0)
            rating_diff = new_rating - old_rating
            
            # 评级上调
            if rating_diff >= self.rating_change_threshold:
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=df['close'].iloc[-1],
                    strength=min(1.0, rating_diff / 3),
                    reason=f"分析师评级上调: {old_rating} -> {new_rating}"
                ))
            
            # 评级下调
            elif rating_diff <= -self.rating_change_threshold:
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='sell',
                    price=df['close'].iloc[-1],
                    strength=min(1.0, abs(rating_diff) / 3),
                    reason=f"分析师评级下调: {old_rating} -> {new_rating}"
                ))
        
        return signals


class InsiderTradingStrategy(BaseStrategy):
    """
    内部人交易策略
    
    基于高管和大股东交易的事件驱动策略
    
    策略原理：
    1. 监控内部人交易公告
    2. 高管增持时跟随买入
    3. 高管减持时跟随卖出
    """
    
    def __init__(
        self,
        min_trade_value: float = 1000000,
        follow_days: int = 5
    ):
        """
        初始化内部人交易策略
        
        Args:
            min_trade_value: 最小交易金额
            follow_days: 跟随交易天数
        """
        config = StrategyConfig(
            name="InsiderTrading",
            description="内部人交易策略"
        )
        super().__init__(config)
        
        self.min_trade_value = min_trade_value
        self.follow_days = follow_days
        
        # 内部人交易记录
        self.insider_trades: Dict[str, List[dict]] = {}
    
    def add_insider_trade(
        self,
        stock_code: str,
        trade: dict
    ) -> None:
        """
        添加内部人交易记录
        
        Args:
            stock_code: 股票代码
            trade: 交易记录
        """
        if stock_code not in self.insider_trades:
            self.insider_trades[stock_code] = []
        
        self.insider_trades[stock_code].append(trade)
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        insider_trades: Optional[Dict[str, List[dict]]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据
            insider_trades: 内部人交易数据
        """
        signals = []
        
        # 更新交易记录
        if insider_trades:
            for stock_code, trades in insider_trades.items():
                for trade in trades:
                    self.add_insider_trade(stock_code, trade)
        
        for stock_code, trades in self.insider_trades.items():
            if stock_code not in data:
                continue
            
            df = data[stock_code]
            
            # 分析最近的内部人交易
            for trade in trades:
                trade_date = trade.get('date')
                trade_type = trade.get('type')  # 'buy' or 'sell'
                trade_value = trade.get('value', 0)
                
                # 检查交易金额
                if trade_value < self.min_trade_value:
                    continue
                
                # 检查是否在跟随期内
                current_date = df['date'].iloc[-1]
                days_since_trade = (pd.to_datetime(current_date) - pd.to_datetime(trade_date)).days
                
                if 0 <= days_since_trade <= self.follow_days:
                    if trade_type == 'buy':
                        signals.append(Signal(
                            stock_code=stock_code,
                            signal_type='buy',
                            price=df['close'].iloc[-1],
                            reason=f"跟随内部人增持，金额: {trade_value:,.0f}"
                        ))
                    elif trade_type == 'sell':
                        signals.append(Signal(
                            stock_code=stock_code,
                            signal_type='sell',
                            price=df['close'].iloc[-1],
                            reason=f"跟随内部人减持，金额: {trade_value:,.0f}"
                        ))
        
        return signals


class DividendStrategy(BaseStrategy):
    """
    分红策略
    
    基于分红公告的事件驱动策略
    
    策略原理：
    1. 在除息日前买入高股息股票
    2. 获取分红收益
    3. 除息后根据情况决定是否继续持有
    """
    
    def __init__(
        self,
        min_dividend_yield: float = 0.03,
        pre_ex_dividend_days: int = 10,
        post_ex_dividend_days: int = 5
    ):
        """
        初始化分红策略
        
        Args:
            min_dividend_yield: 最小股息率
            pre_ex_dividend_days: 除息前建仓天数
            post_ex_dividend_days: 除息后持仓天数
        """
        config = StrategyConfig(
            name="Dividend",
            description="分红策略"
        )
        super().__init__(config)
        
        self.min_dividend_yield = min_dividend_yield
        self.pre_ex_dividend_days = pre_ex_dividend_days
        self.post_ex_dividend_days = post_ex_dividend_days
        
        # 分红日程
        self.dividend_schedule: Dict[str, dict] = {}
        
        # 已处理分红
        self.processed_dividends: set = set()
    
    def set_dividend_schedule(
        self,
        schedule: Dict[str, dict]
    ) -> None:
        """
        设置分红日程
        
        Args:
            schedule: 分红日程 {股票代码: {ex_date, dividend_amount, record_date}}
        """
        self.dividend_schedule = schedule
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        for stock_code, dividend_info in self.dividend_schedule.items():
            if stock_code not in data:
                continue
            
            df = data[stock_code]
            current_date = df['date'].iloc[-1]
            current_price = df['close'].iloc[-1]
            
            ex_date = dividend_info.get('ex_date')
            dividend_amount = dividend_info.get('dividend_amount', 0)
            
            if not ex_date:
                continue
            
            # 计算股息率
            dividend_yield = dividend_amount / current_price
            
            # 检查股息率是否达标
            if dividend_yield < self.min_dividend_yield:
                continue
            
            # 计算距离除息日的天数
            days_to_ex = (pd.to_datetime(ex_date) - pd.to_datetime(current_date)).days
            
            event_key = f"{stock_code}_{ex_date.strftime('%Y%m%d')}"
            
            # 除息前建仓
            if 0 < days_to_ex <= self.pre_ex_dividend_days:
                if event_key not in self.processed_dividends:
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=current_price,
                        reason=f"分红策略: 股息率{dividend_yield*100:.2f}%, 除息日{ex_date.strftime('%Y-%m-%d')}"
                    ))
                    self.processed_dividends.add(event_key)
            
            # 除息后退出
            elif days_to_ex < -self.post_ex_dividend_days:
                exit_key = f"{event_key}_exit"
                if exit_key not in self.processed_dividends:
                    if self.has_position(stock_code):
                        signals.append(Signal(
                            stock_code=stock_code,
                            signal_type='sell',
                            price=current_price,
                            reason="分红策略: 除息后退出"
                        ))
                        self.processed_dividends.add(exit_key)
        
        return signals


if __name__ == "__main__":
    # 测试事件驱动策略
    print("=" * 60)
    print("测试事件驱动策略")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    np.random.seed(42)
    
    data = {}
    for code in ['000001.SZ', '000002.SZ']:
        prices = 10 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'open': prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })
        data[code] = df
    
    # 创建测试事件
    events = [
        Event(
            event_id='E001',
            event_type='earnings',
            stock_code='000001.SZ',
            event_date=dates[50],
            impact=0.05
        )
    ]
    
    # 测试事件驱动策略
    print("\n【测试事件驱动策略】")
    strategy = EventDrivenStrategy()
    signals = strategy.generate_signals(data, events)
    
    print(f"生成信号数量: {len(signals)}")
    for signal in signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    print("\n" + "=" * 60)
    print("事件驱动策略测试完成！")
    print("=" * 60)