"""
风控模块

提供交易风险控制功能，包括仓位控制、止损止盈、交易限制等
保护账户资金安全，防止重大亏损

使用方法:
    from core.simulator.risk_control import RiskControl
    
    risk = RiskControl()
    passed, reason = risk.check_buy_order(order, account)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import pandas as pd
import numpy as np

# 导入项目模块
from core.simulator.order import Order, OrderDirection
from core.simulator.account import Account, Position
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class RiskConfig:
    """
    风控配置数据类
    
    存储风控参数配置
    
    Attributes:
        max_position_ratio: 单只股票最大仓位比例
        max_total_position: 最大总仓位比例
        max_order_value: 单笔最大委托金额
        max_daily_turnover: 单日最大成交额
        max_loss_ratio: 最大亏损比例（触发止损）
        max_drawdown: 最大回撤限制
        stop_loss_ratio: 止损比例
        take_profit_ratio: 止盈比例
    """
    
    # 仓位限制
    max_position_ratio: float = 0.30      # 单只股票最大仓位 30%
    max_total_position: float = 0.95      # 最大总仓位 95%
    
    # 交易限制
    max_order_value: float = 1000000      # 单笔最大委托金额 100 万
    max_daily_turnover: float = 5000000   # 单日最大成交额 500 万
    
    # 风险限制
    max_loss_ratio: float = 0.10          # 最大亏损比例 10%
    max_drawdown: float = 0.20            # 最大回撤 20%
    
    # 止损止盈
    stop_loss_ratio: float = 0.05         # 止损比例 5%
    take_profit_ratio: float = 0.15       # 止盈比例 15%
    
    # 其他限制
    min_trade_volume: int = 100           # 最小交易数量
    max_trade_volume: int = 1000000       # 最大交易数量


class RiskControl:
    """
    风险控制类
    
    提供交易前的风险检查和交易后的风险监控
    
    主要功能：
    1. 订单检查：检查订单是否符合风控规则
    2. 仓位控制：限制单只股票和总仓位比例
    3. 止损止盈：监控持仓盈亏，触发止损止盈
    4. 交易限制：限制单笔和单日交易金额
    
    Attributes:
        config: 风控配置
        daily_turnover: 当日成交额
        trade_date: 交易日期
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        初始化风控模块
        
        Args:
            config: 风控配置，如果为 None 则使用默认配置
        """
        self.config = config or RiskConfig()
        
        # 当日交易统计
        self.daily_turnover: float = 0.0
        self.trade_date: date = date.today()
        
        # 风控记录
        self.risk_events: List[dict] = []
        
        logger.info(
            f"风控模块初始化完成 - "
            f"单股最大仓位: {self.config.max_position_ratio*100:.0f}%, "
            f"止损: {self.config.stop_loss_ratio*100:.0f}%"
        )
    
    # ============================================================
    # 订单检查
    # ============================================================
    
    def check_buy_order(
        self,
        order: Order,
        account: Account,
        market_price: float
    ) -> Tuple[bool, str]:
        """
        检查买入订单
        
        Args:
            order: 订单对象
            account: 账户对象
            market_price: 市场价格
            
        Returns:
            (是否通过, 原因说明)
        """
        # 1. 检查订单状态
        if not order.is_active:
            return False, f"订单状态无效: {order.status}"
        
        # 2. 检查交易数量
        if order.volume < self.config.min_trade_volume:
            return False, f"委托数量小于最小限制: {order.volume} < {self.config.min_trade_volume}"
        
        if order.volume > self.config.max_trade_volume:
            return False, f"委托数量超过最大限制: {order.volume} > {self.config.max_trade_volume}"
        
        # 3. 检查交易数量是否为 100 的整数倍
        if order.volume % 100 != 0:
            return False, f"委托数量必须是 100 的整数倍: {order.volume}"
        
        # 4. 计算委托金额
        order_value = order.price * order.volume
        
        # 5. 检查单笔委托金额
        if order_value > self.config.max_order_value:
            return False, f"委托金额超过单笔限制: {order_value:,.2f} > {self.config.max_order_value:,.2f}"
        
        # 6. 检查资金是否充足
        required_cash = order_value * 1.001  # 预留费用空间
        if account.available_cash < required_cash:
            return False, f"资金不足: 可用 {account.available_cash:,.2f}, 需要 {required_cash:,.2f}"
        
        # 7. 检查单只股票仓位
        position = account.get_position(order.stock_code)
        new_position_value = (position.total_volume + order.volume) * market_price
        position_ratio = new_position_value / account.total_asset
        
        if position_ratio > self.config.max_position_ratio:
            return False, f"超过单只股票最大仓位: {position_ratio*100:.1f}% > {self.config.max_position_ratio*100:.0f}%"
        
        # 8. 检查总仓位
        new_market_value = account.total_market_value + order_value
        total_position_ratio = (new_market_value + account.frozen_cash) / account.total_asset
        
        if total_position_ratio > self.config.max_total_position:
            return False, f"超过最大总仓位: {total_position_ratio*100:.1f}% > {self.config.max_total_position*100:.0f}%"
        
        # 9. 检查当日成交额
        if self.trade_date == date.today():
            if self.daily_turnover + order_value > self.config.max_daily_turnover:
                return False, f"超过当日最大成交额: {self.daily_turnover + order_value:,.2f} > {self.config.max_daily_turnover:,.2f}"
        
        # 记录风控检查通过
        self._log_risk_event('check_buy', order.stock_code, 'passed', f"金额: {order_value:,.2f}")
        
        return True, "风控检查通过"
    
    def check_sell_order(
        self,
        order: Order,
        account: Account
    ) -> Tuple[bool, str]:
        """
        检查卖出订单
        
        Args:
            order: 订单对象
            account: 账户对象
            
        Returns:
            (是否通过, 原因说明)
        """
        # 1. 检查订单状态
        if not order.is_active:
            return False, f"订单状态无效: {order.status}"
        
        # 2. 检查交易数量
        if order.volume < self.config.min_trade_volume:
            return False, f"委托数量小于最小限制: {order.volume}"
        
        # 3. 检查持仓是否充足
        position = account.get_position(order.stock_code)
        
        if position.available_volume < order.volume:
            return False, f"可用持仓不足: 可用 {position.available_volume}, 需要 {order.volume}"
        
        # 4. 检查当日成交额
        order_value = order.price * order.volume
        if self.trade_date == date.today():
            if self.daily_turnover + order_value > self.config.max_daily_turnover:
                return False, f"超过当日最大成交额"
        
        # 记录风控检查通过
        self._log_risk_event('check_sell', order.stock_code, 'passed', f"数量: {order.volume}")
        
        return True, "风控检查通过"
    
    # ============================================================
    # 止损止盈
    # ============================================================
    
    def check_stop_loss(
        self,
        stock_code: str,
        current_price: float,
        position: Position
    ) -> Tuple[bool, float, str]:
        """
        检查止损
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            position: 持仓对象
            
        Returns:
            (是否触发止损, 亏损比例, 原因说明)
        """
        if position.total_volume == 0 or position.avg_cost == 0:
            return False, 0.0, "无持仓"
        
        # 计算亏损比例
        loss_ratio = (current_price - position.avg_cost) / position.avg_cost
        
        # 检查是否触发止损
        if loss_ratio <= -self.config.stop_loss_ratio:
            reason = f"触发止损: 亏损 {loss_ratio*100:.2f}% <= -{self.config.stop_loss_ratio*100:.0f}%"
            
            self._log_risk_event('stop_loss', stock_code, 'triggered', reason)
            
            return True, loss_ratio, reason
        
        return False, loss_ratio, "未触发止损"
    
    def check_take_profit(
        self,
        stock_code: str,
        current_price: float,
        position: Position
    ) -> Tuple[bool, float, str]:
        """
        检查止盈
        
        Args:
            stock_code: 股票代码
            current_price: 当前价格
            position: 持仓对象
            
        Returns:
            (是否触发止盈, 盈利比例, 原因说明)
        """
        if position.total_volume == 0 or position.avg_cost == 0:
            return False, 0.0, "无持仓"
        
        # 计算盈利比例
        profit_ratio = (current_price - position.avg_cost) / position.avg_cost
        
        # 检查是否触发止盈
        if profit_ratio >= self.config.take_profit_ratio:
            reason = f"触发止盈: 盈利 {profit_ratio*100:.2f}% >= {self.config.take_profit_ratio*100:.0f}%"
            
            self._log_risk_event('take_profit', stock_code, 'triggered', reason)
            
            return True, profit_ratio, reason
        
        return False, profit_ratio, "未触发止盈"
    
    def check_all_positions(
        self,
        account: Account,
        prices: Dict[str, float]
    ) -> List[dict]:
        """
        检查所有持仓的止损止盈
        
        Args:
            account: 账户对象
            prices: 价格字典 {股票代码: 价格}
            
        Returns:
            触发止损止盈的持仓列表
        """
        triggered = []
        
        for stock_code, position in account.positions.items():
            current_price = prices.get(stock_code, position.current_price)
            
            # 检查止损
            is_stop_loss, ratio, reason = self.check_stop_loss(
                stock_code, current_price, position
            )
            
            if is_stop_loss:
                triggered.append({
                    'stock_code': stock_code,
                    'type': 'stop_loss',
                    'ratio': ratio,
                    'reason': reason,
                    'volume': position.available_volume,
                    'price': current_price
                })
                continue
            
            # 检查止盈
            is_take_profit, ratio, reason = self.check_take_profit(
                stock_code, current_price, position
            )
            
            if is_take_profit:
                triggered.append({
                    'stock_code': stock_code,
                    'type': 'take_profit',
                    'ratio': ratio,
                    'reason': reason,
                    'volume': position.available_volume,
                    'price': current_price
                })
        
        return triggered
    
    # ============================================================
    # 账户风险监控
    # ============================================================
    
    def check_account_risk(self, account: Account) -> Dict:
        """
        检查账户风险
        
        Args:
            account: 账户对象
            
        Returns:
            风险报告字典
        """
        report = {
            'total_asset': account.total_asset,
            'total_profit_loss': account.total_profit_loss,
            'total_profit_loss_ratio': account.total_profit_loss_ratio,
            'position_count': len(account.positions),
            'position_ratio': account.total_market_value / account.total_asset if account.total_asset > 0 else 0,
            'cash_ratio': account.total_cash / account.total_asset if account.total_asset > 0 else 0,
            'warnings': [],
            'alerts': []
        }
        
        # 检查总亏损
        if account.total_profit_loss_ratio <= -self.config.max_loss_ratio:
            report['alerts'].append(
                f"账户亏损超过限制: {account.total_profit_loss_ratio*100:.2f}%"
            )
        
        # 检查仓位集中度
        if account.positions:
            max_position_ratio = 0.0
            max_position_stock = ""
            
            for stock_code, position in account.positions.items():
                ratio = position.market_value / account.total_asset
                if ratio > max_position_ratio:
                    max_position_ratio = ratio
                    max_position_stock = stock_code
            
            if max_position_ratio > self.config.max_position_ratio:
                report['warnings'].append(
                    f"持仓集中度过高: {max_position_stock} 占比 {max_position_ratio*100:.1f}%"
                )
        
        # 检查现金比例
        cash_ratio = report['cash_ratio']
        if cash_ratio < 0.05:
            report['warnings'].append(
                f"现金比例过低: {cash_ratio*100:.1f}%"
            )
        
        return report
    
    def check_max_drawdown(
        self,
        account: Account,
        peak_asset: float
    ) -> Tuple[bool, float]:
        """
        检查最大回撤
        
        Args:
            account: 账户对象
            peak_asset: 历史最高资产
            
        Returns:
            (是否超过限制, 当前回撤)
        """
        if peak_asset <= 0:
            return False, 0.0
        
        drawdown = (peak_asset - account.total_asset) / peak_asset
        
        if drawdown > self.config.max_drawdown:
            self._log_risk_event(
                'max_drawdown',
                'account',
                'exceeded',
                f"回撤: {drawdown*100:.2f}% > {self.config.max_drawdown*100:.0f}%"
            )
            return True, drawdown
        
        return False, drawdown
    
    # ============================================================
    # 交易统计
    # ============================================================
    
    def update_daily_turnover(self, amount: float) -> None:
        """
        更新当日成交额
        
        Args:
            amount: 成交金额
        """
        # 检查是否新的一天
        today = date.today()
        if self.trade_date != today:
            self.trade_date = today
            self.daily_turnover = 0.0
        
        self.daily_turnover += amount
    
    def reset_daily(self) -> None:
        """重置当日统计"""
        self.trade_date = date.today()
        self.daily_turnover = 0.0
    
    # ============================================================
    # 风控记录
    # ============================================================
    
    def _log_risk_event(
        self,
        event_type: str,
        stock_code: str,
        status: str,
        message: str
    ) -> None:
        """
        记录风控事件
        
        Args:
            event_type: 事件类型
            stock_code: 股票代码
            status: 状态
            message: 消息
        """
        event = {
            'time': datetime.now(),
            'event_type': event_type,
            'stock_code': stock_code,
            'status': status,
            'message': message
        }
        
        self.risk_events.append(event)
        
        logger.info(f"风控事件: {event_type} - {stock_code} - {status} - {message}")
    
    def get_risk_events(
        self,
        event_type: Optional[str] = None
    ) -> List[dict]:
        """
        获取风控事件记录
        
        Args:
            event_type: 事件类型，如果为 None 则返回所有
            
        Returns:
            风控事件列表
        """
        if event_type:
            return [e for e in self.risk_events if e['event_type'] == event_type]
        return self.risk_events
    
    def clear_risk_events(self) -> None:
        """清空风控事件记录"""
        self.risk_events.clear()


if __name__ == "__main__":
    # 测试风控模块
    print("=" * 60)
    print("测试风控模块")
    print("=" * 60)
    
    from core.simulator.order import OrderManager
    
    # 创建风控模块
    risk = RiskControl()
    
    # 创建账户和订单管理器
    account = Account(initial_cash=1000000)
    order_manager = OrderManager()
    
    # 测试买入订单检查
    print("\n【测试买入订单检查】")
    
    # 正常订单
    order1 = order_manager.create_order(
        stock_code="000001.SZ",
        direction="buy",
        order_type="limit",
        price=10.0,
        volume=1000
    )
    passed, reason = risk.check_buy_order(order1, account, 10.0)
    print(f"正常订单: {passed}, {reason}")
    
    # 超过资金限制
    order2 = order_manager.create_order(
        stock_code="000002.SZ",
        direction="buy",
        order_type="limit",
        price=1000.0,
        volume=2000
    )
    passed, reason = risk.check_buy_order(order2, account, 1000.0)
    print(f"超额订单: {passed}, {reason}")
    
    # 测试止损止盈
    print("\n【测试止损止盈】")
    
    # 模拟持仓
    account.buy("000001.SZ", 1000, 10.0, 5.0, 0.1)
    position = account.get_position("000001.SZ")
    position.current_price = 9.0  # 亏损 10%
    
    # 检查止损
    is_stop, ratio, reason = risk.check_stop_loss("000001.SZ", 9.0, position)
    print(f"止损检查: 触发={is_stop}, 比例={ratio*100:.2f}%, 原因={reason}")
    
    # 检查止盈
    position.current_price = 12.0  # 盈利 20%
    is_profit, ratio, reason = risk.check_take_profit("000001.SZ", 12.0, position)
    print(f"止盈检查: 触发={is_profit}, 比例={ratio*100:.2f}%, 原因={reason}")
    
    # 测试账户风险检查
    print("\n【测试账户风险检查】")
    report = risk.check_account_risk(account)
    print(f"总资产: {report['total_asset']:,.2f}")
    print(f"总盈亏: {report['total_profit_loss']:,.2f}")
    print(f"收益率: {report['total_profit_loss_ratio']*100:.2f}%")
    print(f"仓位比例: {report['position_ratio']*100:.1f}%")
    print(f"警告: {report['warnings']}")
    
    # 查看风控事件
    print("\n【风控事件记录】")
    events = risk.get_risk_events()
    for event in events[-5:]:
        print(f"  {event['event_type']}: {event['message']}")
    
    print("\n" + "=" * 60)
    print("风控模块测试完成！")
    print("=" * 60)