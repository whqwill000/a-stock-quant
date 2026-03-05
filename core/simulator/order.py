"""
订单管理模块

管理交易订单的创建、提交、撤销和状态管理
支持限价委托和市价委托两种订单类型

使用方法:
    from core.simulator.order import Order, OrderManager
    
    # 创建订单
    order = OrderManager.create_order(
        stock_code="000001.SZ",
        direction="buy",
        order_type="limit",
        price=10.5,
        volume=1000
    )
    
    # 提交订单
    OrderManager.submit_order(order)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
import pandas as pd

# 导入项目模块
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class OrderDirection(Enum):
    """订单方向枚举"""
    BUY = "buy"      # 买入
    SELL = "sell"    # 卖出


class OrderType(Enum):
    """订单类型枚举"""
    LIMIT = "limit"    # 限价委托
    MARKET = "market"  # 市价委托


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"          # 待提交
    SUBMITTED = "submitted"      # 已提交
    PARTIAL = "partial"          # 部分成交
    FILLED = "filled"            # 完全成交
    CANCELLED = "cancelled"      # 已撤销
    REJECTED = "rejected"        # 已拒绝
    EXPIRED = "expired"          # 已过期


@dataclass
class Order:
    """
    订单数据类
    
    记录单个订单的完整信息
    
    Attributes:
        order_id: 订单编号（唯一标识）
        stock_code: 股票代码
        direction: 买卖方向
        order_type: 订单类型
        price: 委托价格
        volume: 委托数量
        filled_volume: 已成交数量
        avg_price: 成交均价
        status: 订单状态
        create_time: 创建时间
        submit_time: 提交时间
        update_time: 更新时间
        message: 备注信息
    """
    
    # 必填字段
    stock_code: str
    direction: str
    order_type: str
    price: float
    volume: int
    
    # 自动生成字段
    order_id: str = ""
    filled_volume: int = 0
    avg_price: float = 0.0
    status: str = OrderStatus.PENDING.value
    create_time: datetime = field(default_factory=datetime.now)
    submit_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    message: str = ""
    
    def __post_init__(self):
        """初始化后处理"""
        # 生成订单 ID
        if not self.order_id:
            timestamp = self.create_time.strftime("%Y%m%d%H%M%S%f")
            self.order_id = f"ORD{timestamp}"
        
        # 验证参数
        self._validate()
    
    def _validate(self) -> None:
        """验证订单参数"""
        # 验证方向
        if self.direction not in [OrderDirection.BUY.value, OrderDirection.SELL.value]:
            raise ValueError(f"无效的订单方向: {self.direction}")
        
        # 验证类型
        if self.order_type not in [OrderType.LIMIT.value, OrderType.MARKET.value]:
            raise ValueError(f"无效的订单类型: {self.order_type}")
        
        # 验证价格
        if self.order_type == OrderType.LIMIT.value and self.price <= 0:
            raise ValueError(f"限价单价格必须大于 0: {self.price}")
        
        # 验证数量
        if self.volume <= 0:
            raise ValueError(f"委托数量必须大于 0: {self.volume}")
        
        # 验证数量是否为 100 的整数倍
        if self.volume % 100 != 0:
            logger.warning(f"委托数量不是 100 的整数倍: {self.volume}")
    
    @property
    def remaining_volume(self) -> int:
        """剩余未成交数量"""
        return self.volume - self.filled_volume
    
    @property
    def is_fully_filled(self) -> bool:
        """是否完全成交"""
        return self.filled_volume >= self.volume
    
    @property
    def is_active(self) -> bool:
        """是否仍然有效（可以继续成交）"""
        return self.status in [
            OrderStatus.SUBMITTED.value,
            OrderStatus.PARTIAL.value
        ]
    
    @property
    def is_buy(self) -> bool:
        """是否为买入订单"""
        return self.direction == OrderDirection.BUY.value
    
    @property
    def is_sell(self) -> bool:
        """是否为卖出订单"""
        return self.direction == OrderDirection.SELL.value
    
    @property
    def is_limit(self) -> bool:
        """是否为限价单"""
        return self.order_type == OrderType.LIMIT.value
    
    @property
    def is_market(self) -> bool:
        """是否为市价单"""
        return self.order_type == OrderType.MARKET.value
    
    def update_fill(self, filled_volume: int, price: float) -> None:
        """
        更新成交信息
        
        Args:
            filled_volume: 本次成交数量
            price: 本次成交价格
        """
        # 计算新的成交均价
        total_amount = self.avg_price * self.filled_volume + price * filled_volume
        new_filled_volume = self.filled_volume + filled_volume
        
        if new_filled_volume > 0:
            self.avg_price = total_amount / new_filled_volume
        
        self.filled_volume = new_filled_volume
        self.update_time = datetime.now()
        
        # 更新状态
        if self.is_fully_filled:
            self.status = OrderStatus.FILLED.value
        elif self.filled_volume > 0:
            self.status = OrderStatus.PARTIAL.value
        
        logger.debug(
            f"订单更新: {self.order_id}, "
            f"成交: {filled_volume}股 @ {price:.2f}, "
            f"累计: {self.filled_volume}/{self.volume}"
        )
    
    def cancel(self) -> bool:
        """
        撤销订单
        
        Returns:
            是否成功撤销
        """
        if self.status in [
            OrderStatus.FILLED.value,
            OrderStatus.CANCELLED.value,
            OrderStatus.REJECTED.value
        ]:
            logger.warning(f"订单无法撤销，当前状态: {self.status}")
            return False
        
        self.status = OrderStatus.CANCELLED.value
        self.update_time = datetime.now()
        
        logger.info(f"订单已撤销: {self.order_id}")
        return True
    
    def reject(self, reason: str = "") -> bool:
        """
        拒绝订单
        
        Args:
            reason: 拒绝原因
            
        Returns:
            是否成功拒绝
        """
        if self.status != OrderStatus.PENDING.value:
            return False
        
        self.status = OrderStatus.REJECTED.value
        self.message = reason
        self.update_time = datetime.now()
        
        logger.info(f"订单已拒绝: {self.order_id}, 原因: {reason}")
        return True
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'order_id': self.order_id,
            'stock_code': self.stock_code,
            'direction': self.direction,
            'order_type': self.order_type,
            'price': self.price,
            'volume': self.volume,
            'filled_volume': self.filled_volume,
            'remaining_volume': self.remaining_volume,
            'avg_price': self.avg_price,
            'status': self.status,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'submit_time': self.submit_time.isoformat() if self.submit_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'message': self.message
        }


@dataclass
class Trade:
    """
    成交记录数据类
    
    记录单笔成交的详细信息
    
    Attributes:
        trade_id: 成交编号
        order_id: 关联订单编号
        stock_code: 股票代码
        direction: 买卖方向
        price: 成交价格
        volume: 成交数量
        amount: 成交金额
        commission: 佣金
        stamp_tax: 印花税（仅卖出）
        transfer_fee: 过户费
        total_fee: 总费用
        trade_time: 成交时间
    """
    
    order_id: str
    stock_code: str
    direction: str
    price: float
    volume: int
    
    trade_id: str = ""
    amount: float = 0.0
    commission: float = 0.0
    stamp_tax: float = 0.0
    transfer_fee: float = 0.0
    trade_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化后处理"""
        # 生成成交 ID
        if not self.trade_id:
            timestamp = self.trade_time.strftime("%Y%m%d%H%M%S%f")
            self.trade_id = f"TRD{timestamp}"
        
        # 计算成交金额
        if self.amount == 0:
            self.amount = self.price * self.volume
    
    @property
    def total_fee(self) -> float:
        """总费用"""
        return self.commission + self.stamp_tax + self.transfer_fee
    
    @property
    def net_amount(self) -> float:
        """净金额（扣除费用后）"""
        if self.direction == OrderDirection.BUY.value:
            return self.amount + self.total_fee
        else:
            return self.amount - self.total_fee
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'trade_id': self.trade_id,
            'order_id': self.order_id,
            'stock_code': self.stock_code,
            'direction': self.direction,
            'price': self.price,
            'volume': self.volume,
            'amount': self.amount,
            'commission': self.commission,
            'stamp_tax': self.stamp_tax,
            'transfer_fee': self.transfer_fee,
            'total_fee': self.total_fee,
            'net_amount': self.net_amount,
            'trade_time': self.trade_time.isoformat()
        }


class OrderManager:
    """
    订单管理器
    
    管理所有订单的创建、查询、撤销等操作
    
    Attributes:
        orders: 订单字典
        trades: 成交记录列表
        order_counter: 订单计数器
    """
    
    def __init__(self):
        """初始化订单管理器"""
        self.orders: Dict[str, Order] = {}
        self.trades: List[Trade] = []
        self.order_counter = 0
        
        logger.info("订单管理器初始化完成")
    
    def create_order(
        self,
        stock_code: str,
        direction: str,
        order_type: str,
        price: float,
        volume: int
    ) -> Order:
        """
        创建订单
        
        Args:
            stock_code: 股票代码
            direction: 买卖方向，"buy" 或 "sell"
            order_type: 订单类型，"limit" 或 "market"
            price: 委托价格（市价单可以为 0）
            volume: 委托数量
            
        Returns:
            创建的订单对象
            
        Example:
            >>> manager = OrderManager()
            >>> order = manager.create_order(
            ...     stock_code="000001.SZ",
            ...     direction="buy",
            ...     order_type="limit",
            ...     price=10.5,
            ...     volume=1000
            ... )
        """
        # 更新计数器
        self.order_counter += 1
        
        # 创建订单
        order = Order(
            stock_code=stock_code,
            direction=direction,
            order_type=order_type,
            price=price,
            volume=volume
        )
        
        # 存储订单
        self.orders[order.order_id] = order
        
        logger.info(
            f"创建订单: {order.order_id}, "
            f"{direction} {stock_code} {volume}股 @ {price:.2f}"
        )
        
        return order
    
    def submit_order(self, order_id: str) -> bool:
        """
        提交订单
        
        Args:
            order_id: 订单编号
            
        Returns:
            是否成功提交
        """
        order = self.orders.get(order_id)
        
        if not order:
            logger.warning(f"订单不存在: {order_id}")
            return False
        
        if order.status != OrderStatus.PENDING.value:
            logger.warning(f"订单状态不允许提交: {order.status}")
            return False
        
        order.status = OrderStatus.SUBMITTED.value
        order.submit_time = datetime.now()
        order.update_time = datetime.now()
        
        logger.info(f"订单已提交: {order_id}")
        return True
    
    def cancel_order(self, order_id: str) -> bool:
        """
        撤销订单
        
        Args:
            order_id: 订单编号
            
        Returns:
            是否成功撤销
        """
        order = self.orders.get(order_id)
        
        if not order:
            logger.warning(f"订单不存在: {order_id}")
            return False
        
        return order.cancel()
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        获取订单
        
        Args:
            order_id: 订单编号
            
        Returns:
            订单对象，不存在则返回 None
        """
        return self.orders.get(order_id)
    
    def get_active_orders(self, stock_code: Optional[str] = None) -> List[Order]:
        """
        获取活动订单列表
        
        Args:
            stock_code: 股票代码，如果指定则只返回该股票的订单
            
        Returns:
            活动订单列表
        """
        orders = [
            order for order in self.orders.values()
            if order.is_active
        ]
        
        if stock_code:
            orders = [o for o in orders if o.stock_code == stock_code]
        
        return orders
    
    def get_orders_by_status(self, status: str) -> List[Order]:
        """
        按状态获取订单
        
        Args:
            status: 订单状态
            
        Returns:
            订单列表
        """
        return [
            order for order in self.orders.values()
            if order.status == status
        ]
    
    def add_trade(self, trade: Trade) -> None:
        """
        添加成交记录
        
        Args:
            trade: 成交记录对象
        """
        self.trades.append(trade)
        
        # 更新订单成交信息
        order = self.orders.get(trade.order_id)
        if order:
            order.update_fill(trade.volume, trade.price)
        
        logger.info(
            f"成交记录: {trade.trade_id}, "
            f"{trade.direction} {trade.stock_code} "
            f"{trade.volume}股 @ {trade.price:.2f}"
        )
    
    def get_trades(
        self,
        stock_code: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> List[Trade]:
        """
        获取成交记录
        
        Args:
            stock_code: 股票代码
            order_id: 订单编号
            
        Returns:
            成交记录列表
        """
        trades = self.trades
        
        if stock_code:
            trades = [t for t in trades if t.stock_code == stock_code]
        
        if order_id:
            trades = [t for t in trades if t.order_id == order_id]
        
        return trades
    
    def get_orders_df(self) -> pd.DataFrame:
        """
        获取订单 DataFrame
        
        Returns:
            订单 DataFrame
        """
        if not self.orders:
            return pd.DataFrame()
        
        data = [order.to_dict() for order in self.orders.values()]
        return pd.DataFrame(data)
    
    def get_trades_df(self) -> pd.DataFrame:
        """
        获取成交记录 DataFrame
        
        Returns:
            成交记录 DataFrame
        """
        if not self.trades:
            return pd.DataFrame()
        
        data = [trade.to_dict() for trade in self.trades]
        return pd.DataFrame(data)
    
    def clear_history(self) -> None:
        """清理历史订单和成交记录"""
        # 只保留活动订单
        self.orders = {
            k: v for k, v in self.orders.items()
            if v.is_active
        }
        
        logger.info("已清理历史订单")
    
    def reset(self) -> None:
        """重置订单管理器"""
        self.orders.clear()
        self.trades.clear()
        self.order_counter = 0
        
        logger.info("订单管理器已重置")


if __name__ == "__main__":
    # 测试订单模块
    print("=" * 60)
    print("测试订单管理模块")
    print("=" * 60)
    
    # 创建订单管理器
    manager = OrderManager()
    
    # 测试创建订单
    print("\n【测试创建订单】")
    order1 = manager.create_order(
        stock_code="000001.SZ",
        direction="buy",
        order_type="limit",
        price=10.5,
        volume=1000
    )
    print(f"订单 ID: {order1.order_id}")
    print(f"股票代码: {order1.stock_code}")
    print(f"方向: {order1.direction}")
    print(f"类型: {order1.order_type}")
    print(f"价格: {order1.price}")
    print(f"数量: {order1.volume}")
    print(f"状态: {order1.status}")
    
    # 测试提交订单
    print("\n【测试提交订单】")
    manager.submit_order(order1.order_id)
    print(f"提交后状态: {order1.status}")
    
    # 测试更新成交
    print("\n【测试更新成交】")
    order1.update_fill(500, 10.48)
    print(f"成交后状态: {order1.status}")
    print(f"已成交: {order1.filled_volume}")
    print(f"成交均价: {order1.avg_price}")
    
    # 测试完全成交
    print("\n【测试完全成交】")
    order1.update_fill(500, 10.52)
    print(f"完全成交后状态: {order1.status}")
    print(f"成交均价: {order1.avg_price}")
    
    # 测试撤销订单
    print("\n【测试撤销订单】")
    order2 = manager.create_order(
        stock_code="000002.SZ",
        direction="sell",
        order_type="limit",
        price=15.0,
        volume=2000
    )
    manager.submit_order(order2.order_id)
    manager.cancel_order(order2.order_id)
    print(f"撤销后状态: {order2.status}")
    
    # 查看订单列表
    print("\n【订单列表】")
    df = manager.get_orders_df()
    print(df[['order_id', 'stock_code', 'direction', 'status', 'filled_volume']])
    
    print("\n" + "=" * 60)
    print("订单管理模块测试完成！")
    print("=" * 60)