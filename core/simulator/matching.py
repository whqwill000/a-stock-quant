"""
撮合引擎模块

模拟 A 股交易撮合过程，处理订单匹配和成交
支持限价单和市价单的撮合逻辑

使用方法:
    from core.simulator.matching import MatchingEngine
    
    engine = MatchingEngine()
    trades = engine.match(order, market_data)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# 导入项目模块
from core.simulator.order import Order, Trade, OrderStatus, OrderType, OrderDirection
from core.simulator.account import Account
from core.utils.logger import get_logger
from core.utils.helpers import (
    calculate_commission,
    calculate_stamp_tax,
    calculate_transfer_fee,
    round_price
)

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class MarketData:
    """
    市场数据类
    
    存储单只股票的市场行情数据
    
    Attributes:
        stock_code: 股票代码
        date: 交易日期
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        amount: 成交额
        limit_up: 涨停价
        limit_down: 跌停价
    """
    
    stock_code: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    amount: float = 0.0
    limit_up: float = 0.0
    limit_down: float = 0.0
    
    @property
    def mid_price(self) -> float:
        """中间价"""
        return (self.high + self.low) / 2
    
    @property
    def is_limit_up(self) -> bool:
        """是否涨停"""
        return self.close >= self.limit_up if self.limit_up > 0 else False
    
    @property
    def is_limit_down(self) -> bool:
        """是否跌停"""
        return self.close <= self.limit_down if self.limit_down > 0 else False


class PriceLimitRule:
    """
    涨跌停规则类
    
    计算 A 股涨跌停价格
    
    A 股涨跌停规则：
    - 主板：±10%
    - 科创板/创业板：±20%
    - ST 股：±5%
    - 北交所：±30%
    """
    
    # 涨跌停幅度
    LIMIT_MAIN = 0.10       # 主板 10%
    LIMIT_STAR = 0.20       # 科创板/创业板 20%
    LIMIT_ST = 0.05         # ST 股 5%
    LIMIT_BSE = 0.30        # 北交所 30%
    
    def get_limit_ratio(self, stock_code: str) -> float:
        """
        获取涨跌停幅度
        
        Args:
            stock_code: 股票代码
            
        Returns:
            涨跌停幅度
        """
        code = stock_code.split('.')[0]
        
        # ST 股票
        if 'ST' in stock_code.upper():
            return self.LIMIT_ST
        
        # 科创板（688 开头）
        if code.startswith('688'):
            return self.LIMIT_STAR
        
        # 创业板（300/301 开头）
        if code.startswith(('300', '301')):
            return self.LIMIT_STAR
        
        # 北交所（8/4 开头）
        if code.startswith(('8', '4')):
            return self.LIMIT_BSE
        
        # 主板
        return self.LIMIT_MAIN
    
    def calculate_limit_prices(
        self,
        stock_code: str,
        prev_close: float
    ) -> Tuple[float, float]:
        """
        计算涨跌停价格
        
        Args:
            stock_code: 股票代码
            prev_close: 昨日收盘价
            
        Returns:
            (涨停价, 跌停价)
        """
        if prev_close <= 0:
            return 0.0, 0.0
        
        ratio = self.get_limit_ratio(stock_code)
        
        # 计算涨跌停价格（四舍五入到分）
        limit_up = round_price(prev_close * (1 + ratio))
        limit_down = round_price(prev_close * (1 - ratio))
        
        return limit_up, limit_down
    
    def is_limit_up(
        self,
        stock_code: str,
        price: float,
        prev_close: float
    ) -> bool:
        """
        判断是否涨停
        
        Args:
            stock_code: 股票代码
            price: 当前价格
            prev_close: 昨日收盘价
            
        Returns:
            是否涨停
        """
        limit_up, _ = self.calculate_limit_prices(stock_code, prev_close)
        return price >= limit_up
    
    def is_limit_down(
        self,
        stock_code: str,
        price: float,
        prev_close: float
    ) -> bool:
        """
        判断是否跌停
        
        Args:
            stock_code: 股票代码
            price: 当前价格
            prev_close: 昨日收盘价
            
        Returns:
            是否跌停
        """
        _, limit_down = self.calculate_limit_prices(stock_code, prev_close)
        return price <= limit_down


class MatchingEngine:
    """
    撮合引擎类
    
    模拟 A 股交易撮合过程
    
    撮合原则：
    1. 价格优先：高价买入优先，低价卖出优先
    2. 时间优先：同价位先申报优先
    3. 市价优先：市价单优先于限价单
    
    Attributes:
        price_limit_rule: 涨跌停规则
        commission_rate: 佣金费率
        min_commission: 最低佣金
        stamp_tax_rate: 印花税率
        transfer_fee_rate: 过户费率
    """
    
    def __init__(
        self,
        commission_rate: float = 0.00025,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 0.0005,
        transfer_fee_rate: float = 0.00001
    ):
        """
        初始化撮合引擎
        
        Args:
            commission_rate: 佣金费率，默认万分之 2.5
            min_commission: 最低佣金，默认 5 元
            stamp_tax_rate: 印花税率，默认 0.05%
            transfer_fee_rate: 过户费率，默认十万分之一
        """
        self.price_limit_rule = PriceLimitRule()
        
        # 交易成本参数
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate
        self.transfer_fee_rate = transfer_fee_rate
        
        logger.info(
            f"撮合引擎初始化完成 - "
            f"佣金: {commission_rate*10000:.1f}万, "
            f"印花税: {stamp_tax_rate*100:.2f}%"
        )
    
    def match(
        self,
        order: Order,
        market_data: MarketData,
        account: Optional[Account] = None
    ) -> List[Trade]:
        """
        撮合订单
        
        根据市场数据判断订单是否可以成交，生成成交记录
        
        Args:
            order: 订单对象
            market_data: 市场数据
            account: 账户对象（用于资金和持仓检查）
            
        Returns:
            成交记录列表
            
        Example:
            >>> engine = MatchingEngine()
            >>> trades = engine.match(order, market_data)
        """
        trades = []
        
        # 检查订单状态
        if not order.is_active:
            logger.warning(f"订单非活动状态，无法撮合: {order.order_id}")
            return trades
        
        # 检查涨跌停限制
        if not self._check_price_limit(order, market_data):
            logger.debug(
                f"订单受涨跌停限制: {order.order_id}, "
                f"涨停: {market_data.is_limit_up}, 跌停: {market_data.is_limit_down}"
            )
            return trades
        
        # 根据订单类型撮合
        if order.is_limit:
            trade = self._match_limit_order(order, market_data)
        else:
            trade = self._match_market_order(order, market_data)
        
        if trade:
            trades.append(trade)
        
        return trades
    
    def _check_price_limit(self, order: Order, market_data: MarketData) -> bool:
        """
        检查涨跌停限制
        
        Args:
            order: 订单对象
            market_data: 市场数据
            
        Returns:
            是否可以交易
        """
        # 涨停时无法买入
        if market_data.is_limit_up and order.is_buy:
            return False
        
        # 跌停时无法卖出
        if market_data.is_limit_down and order.is_sell:
            return False
        
        return True
    
    def _match_limit_order(
        self,
        order: Order,
        market_data: MarketData
    ) -> Optional[Trade]:
        """
        撮合限价单
        
        限价单撮合逻辑：
        - 买入：委托价 >= 当前最低价时可以成交
        - 卖出：委托价 <= 当前最高价时可以成交
        
        Args:
            order: 订单对象
            market_data: 市场数据
            
        Returns:
            成交记录，如果无法成交则返回 None
        """
        # 买入限价单
        if order.is_buy:
            # 委托价必须 >= 最低价才能成交
            if order.price >= market_data.low:
                # 成交价格取委托价和开盘价的较小值
                # 实际应该取委托价和市场最优价的较小值
                trade_price = min(order.price, market_data.open)
                return self._create_trade(order, trade_price, market_data)
        
        # 卖出限价单
        else:
            # 委托价必须 <= 最高价才能成交
            if order.price <= market_data.high:
                # 成交价格取委托价和开盘价的较大值
                trade_price = max(order.price, market_data.open)
                return self._create_trade(order, trade_price, market_data)
        
        return None
    
    def _match_market_order(
        self,
        order: Order,
        market_data: MarketData
    ) -> Optional[Trade]:
        """
        撮合市价单
        
        市价单以当前市场价格成交
        
        Args:
            order: 订单对象
            market_data: 市场数据
            
        Returns:
            成交记录
        """
        # 市价单以开盘价成交（简化处理）
        # 实际应该以当前最优价成交
        trade_price = market_data.open
        
        return self._create_trade(order, trade_price, market_data)
    
    def _create_trade(
        self,
        order: Order,
        price: float,
        market_data: MarketData
    ) -> Trade:
        """
        创建成交记录
        
        Args:
            order: 订单对象
            price: 成交价格
            market_data: 市场数据
            
        Returns:
            成交记录对象
        """
        # 计算成交数量（取剩余未成交数量）
        volume = order.remaining_volume
        
        # 计算成交金额
        amount = price * volume
        
        # 计算交易成本
        commission = calculate_commission(
            amount,
            self.commission_rate,
            self.min_commission
        )
        
        # 印花税（仅卖出收取）
        stamp_tax = 0.0
        if order.is_sell:
            stamp_tax = calculate_stamp_tax(amount, self.stamp_tax_rate)
        
        # 过户费
        transfer_fee = calculate_transfer_fee(volume, self.transfer_fee_rate)
        
        # 创建成交记录
        trade = Trade(
            order_id=order.order_id,
            stock_code=order.stock_code,
            direction=order.direction,
            price=price,
            volume=volume,
            amount=amount,
            commission=commission,
            stamp_tax=stamp_tax,
            transfer_fee=transfer_fee,
            trade_time=market_data.date
        )
        
        logger.info(
            f"成交: {trade.trade_id}, "
            f"{order.direction} {order.stock_code} "
            f"{volume}股 @ {price:.2f}, "
            f"金额: {amount:,.2f}, 费用: {trade.total_fee:.2f}"
        )
        
        return trade
    
    def match_batch(
        self,
        orders: List[Order],
        market_data_dict: Dict[str, MarketData],
        account: Optional[Account] = None
    ) -> List[Trade]:
        """
        批量撮合订单
        
        Args:
            orders: 订单列表
            market_data_dict: 市场数据字典 {股票代码: MarketData}
            account: 账户对象
            
        Returns:
            成交记录列表
        """
        all_trades = []
        
        for order in orders:
            market_data = market_data_dict.get(order.stock_code)
            
            if market_data:
                trades = self.match(order, market_data, account)
                all_trades.extend(trades)
        
        return all_trades
    
    def simulate_daily_trading(
        self,
        orders: List[Order],
        daily_data: pd.DataFrame,
        account: Account
    ) -> List[Trade]:
        """
        模拟日内交易
        
        根据日内行情数据模拟订单撮合
        
        Args:
            orders: 订单列表
            daily_data: 日行情数据 DataFrame
            account: 账户对象
            
        Returns:
            成交记录列表
        """
        trades = []
        
        # 按股票代码分组订单
        orders_by_stock: Dict[str, List[Order]] = {}
        for order in orders:
            if order.stock_code not in orders_by_stock:
                orders_by_stock[order.stock_code] = []
            orders_by_stock[order.stock_code].append(order)
        
        # 遍历每只股票的数据
        for stock_code, stock_orders in orders_by_stock.items():
            # 获取该股票的行情数据
            stock_data = daily_data[daily_data['stock_code'] == stock_code]
            
            if stock_data.empty:
                logger.warning(f"未找到股票数据: {stock_code}")
                continue
            
            # 取最新一天的数据
            row = stock_data.iloc[-1]
            
            # 计算涨跌停价格
            prev_close = row.get('pre_close', row['close'])
            limit_up, limit_down = self.price_limit_rule.calculate_limit_prices(
                stock_code, prev_close
            )
            
            # 创建市场数据对象
            market_data = MarketData(
                stock_code=stock_code,
                date=pd.to_datetime(row['date']),
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row.get('volume', 0),
                amount=row.get('amount', 0),
                limit_up=limit_up,
                limit_down=limit_down
            )
            
            # 撮合订单
            for order in stock_orders:
                order_trades = self.match(order, market_data, account)
                trades.extend(order_trades)
        
        return trades


if __name__ == "__main__":
    # 测试撮合引擎
    print("=" * 60)
    print("测试撮合引擎模块")
    print("=" * 60)
    
    from core.simulator.order import OrderManager
    
    # 创建撮合引擎
    engine = MatchingEngine()
    
    # 创建订单管理器
    order_manager = OrderManager()
    
    # 创建测试订单
    print("\n【创建测试订单】")
    buy_order = order_manager.create_order(
        stock_code="000001.SZ",
        direction="buy",
        order_type="limit",
        price=10.5,
        volume=1000
    )
    order_manager.submit_order(buy_order.order_id)
    
    sell_order = order_manager.create_order(
        stock_code="000002.SZ",
        direction="sell",
        order_type="limit",
        price=15.0,
        volume=500
    )
    order_manager.submit_order(sell_order.order_id)
    
    # 创建测试市场数据
    print("\n【创建测试市场数据】")
    market_data_1 = MarketData(
        stock_code="000001.SZ",
        date=datetime.now(),
        open=10.3,
        high=10.8,
        low=10.2,
        close=10.6,
        volume=1000000,
        limit_up=11.0,
        limit_down=9.0
    )
    
    market_data_2 = MarketData(
        stock_code="000002.SZ",
        date=datetime.now(),
        open=15.2,
        high=15.5,
        low=14.8,
        close=15.3,
        volume=500000,
        limit_up=16.5,
        limit_down=13.5
    )
    
    # 测试撮合
    print("\n【测试订单撮合】")
    
    # 撮合买入订单
    trades_1 = engine.match(buy_order, market_data_1)
    print(f"买入订单成交: {len(trades_1)} 笔")
    if trades_1:
        trade = trades_1[0]
        print(f"  成交价: {trade.price:.2f}")
        print(f"  成交量: {trade.volume}")
        print(f"  成交额: {trade.amount:.2f}")
        print(f"  佣金: {trade.commission:.2f}")
    
    # 撮合卖出订单
    trades_2 = engine.match(sell_order, market_data_2)
    print(f"卖出订单成交: {len(trades_2)} 笔")
    if trades_2:
        trade = trades_2[0]
        print(f"  成交价: {trade.price:.2f}")
        print(f"  成交量: {trade.volume}")
        print(f"  成交额: {trade.amount:.2f}")
        print(f"  印花税: {trade.stamp_tax:.2f}")
    
    # 测试涨跌停规则
    print("\n【测试涨跌停规则】")
    price_rule = PriceLimitRule()
    
    # 主板
    limit_up, limit_down = price_rule.calculate_limit_prices("600000.SH", 10.0)
    print(f"主板 600000: 涨停价={limit_up:.2f}, 跌停价={limit_down:.2f}")
    
    # 科创板
    limit_up, limit_down = price_rule.calculate_limit_prices("688001.SH", 50.0)
    print(f"科创板 688001: 涨停价={limit_up:.2f}, 跌停价={limit_down:.2f}")
    
    # 创业板
    limit_up, limit_down = price_rule.calculate_limit_prices("300001.SZ", 20.0)
    print(f"创业板 300001: 涨停价={limit_up:.2f}, 跌停价={limit_down:.2f}")
    
    print("\n" + "=" * 60)
    print("撮合引擎模块测试完成！")
    print("=" * 60)