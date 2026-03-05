"""
账户管理模块

管理交易账户的资金和持仓，是交易模拟器的核心组件
支持资金冻结/解冻、持仓管理、T+1 规则等 A 股特有规则

使用方法:
    from core.simulator.account import Account
    
    account = Account(initial_cash=1000000)
    account.freeze_cash(10000)  # 冻结资金
    account.buy_stock("000001.SZ", 1000, 10.5)  # 买入股票
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# 导入项目模块
from core.utils.logger import get_logger
from core.utils.helpers import (
    calculate_commission,
    calculate_stamp_tax,
    calculate_transfer_fee,
    round_price,
    round_volume
)

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class Position:
    """
    持仓数据类
    
    记录单只股票的持仓信息，包括数量、成本、市值等
    
    Attributes:
        stock_code: 股票代码
        total_volume: 总持仓数量
        available_volume: 可用持仓数量（T+1 后可用）
        frozen_volume: 冻结持仓数量（委托卖出时冻结）
        avg_cost: 平均持仓成本
        current_price: 当前价格
        market_value: 市值
        profit_loss: 浮动盈亏
        profit_loss_ratio: 盈亏比例
    """
    
    stock_code: str
    total_volume: int = 0
    available_volume: int = 0
    frozen_volume: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    
    @property
    def market_value(self) -> float:
        """计算市值"""
        return self.total_volume * self.current_price
    
    @property
    def profit_loss(self) -> float:
        """计算浮动盈亏"""
        return (self.current_price - self.avg_cost) * self.total_volume
    
    @property
    def profit_loss_ratio(self) -> float:
        """计算盈亏比例"""
        if self.avg_cost == 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'total_volume': self.total_volume,
            'available_volume': self.available_volume,
            'frozen_volume': self.frozen_volume,
            'avg_cost': self.avg_cost,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'profit_loss': self.profit_loss,
            'profit_loss_ratio': self.profit_loss_ratio
        }


@dataclass
class TPlus1Record:
    """
    T+1 记录数据类
    
    记录买入股票的日期，用于判断何时可以卖出
    
    Attributes:
        stock_code: 股票代码
        volume: 买入数量
        buy_date: 买入日期
        available_date: 可用日期（买入次日）
    """
    
    stock_code: str
    volume: int
    buy_date: date
    available_date: date


class Account:
    """
    交易账户类
    
    管理账户的资金和持仓，提供买入、卖出、冻结等操作
    
    A 股特殊规则：
    - T+1：当日买入的股票次日才能卖出
    - 涨跌停：涨停无法买入，跌停无法卖出
    - 最小单位：100 股 = 1 手
    
    Attributes:
        initial_cash: 初始资金
        available_cash: 可用资金
        frozen_cash: 冻结资金
        positions: 持仓字典
        t_plus1_records: T+1 记录列表
    """
    
    def __init__(self, initial_cash: float = 1000000.0):
        """
        初始化账户
        
        Args:
            initial_cash: 初始资金，默认 100 万
        """
        self.initial_cash = initial_cash
        self.available_cash = initial_cash
        self.frozen_cash = 0.0
        
        # 持仓管理
        self.positions: Dict[str, Position] = {}
        
        # T+1 记录
        self.t_plus1_records: List[TPlus1Record] = []
        
        # 交易记录
        self.trade_history: List[dict] = []
        
        # 当前日期（用于 T+1 判断）
        self.current_date: date = date.today()
        
        logger.info(f"账户初始化完成，初始资金: {initial_cash:,.2f} 元")
    
    # ============================================================
    # 资金管理
    # ============================================================
    
    @property
    def total_cash(self) -> float:
        """总资金 = 可用资金 + 冻结资金"""
        return self.available_cash + self.frozen_cash
    
    @property
    def total_market_value(self) -> float:
        """总市值"""
        return sum(pos.market_value for pos in self.positions.values())
    
    @property
    def total_asset(self) -> float:
        """总资产 = 总资金 + 总市值"""
        return self.total_cash + self.total_market_value
    
    @property
    def total_profit_loss(self) -> float:
        """总盈亏"""
        return self.total_asset - self.initial_cash
    
    @property
    def total_profit_loss_ratio(self) -> float:
        """总收益率"""
        if self.initial_cash == 0:
            return 0.0
        return (self.total_asset - self.initial_cash) / self.initial_cash
    
    def freeze_cash(self, amount: float) -> bool:
        """
        冻结资金（下单时调用）
        
        Args:
            amount: 要冻结的金额
            
        Returns:
            是否成功冻结
        """
        if amount <= 0:
            logger.warning(f"冻结金额必须大于 0: {amount}")
            return False
        
        if self.available_cash < amount:
            logger.warning(
                f"资金不足，无法冻结。"
                f"可用: {self.available_cash:,.2f}, 需要: {amount:,.2f}"
            )
            return False
        
        self.available_cash -= amount
        self.frozen_cash += amount
        
        logger.debug(f"冻结资金: {amount:,.2f} 元")
        return True
    
    def unfreeze_cash(self, amount: float) -> bool:
        """
        解冻资金（撤单时调用）
        
        Args:
            amount: 要解冻的金额
            
        Returns:
            是否成功解冻
        """
        if amount <= 0:
            return False
        
        if self.frozen_cash < amount:
            logger.warning(f"冻结资金不足，无法解冻: {amount}")
            amount = self.frozen_cash
        
        self.frozen_cash -= amount
        self.available_cash += amount
        
        logger.debug(f"解冻资金: {amount:,.2f} 元")
        return True
    
    def deduct_cash(self, amount: float) -> bool:
        """
        扣除资金（成交时调用）
        
        从冻结资金中扣除
        
        Args:
            amount: 要扣除的金额
            
        Returns:
            是否成功扣除
        """
        if amount <= 0:
            return False
        
        if self.frozen_cash < amount:
            logger.warning(f"冻结资金不足，无法扣除: {amount}")
            return False
        
        self.frozen_cash -= amount
        
        logger.debug(f"扣除资金: {amount:,.2f} 元")
        return True
    
    def add_cash(self, amount: float) -> None:
        """
        增加资金（卖出成交时调用）
        
        Args:
            amount: 要增加的金额
        """
        if amount > 0:
            self.available_cash += amount
            logger.debug(f"增加资金: {amount:,.2f} 元")
    
    # ============================================================
    # 持仓管理
    # ============================================================
    
    def get_position(self, stock_code: str) -> Position:
        """
        获取持仓信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            持仓对象，如果不存在则返回空持仓
        """
        if stock_code not in self.positions:
            self.positions[stock_code] = Position(stock_code=stock_code)
        return self.positions[stock_code]
    
    def update_position_price(self, stock_code: str, price: float) -> None:
        """
        更新持仓价格
        
        Args:
            stock_code: 股票代码
            price: 当前价格
        """
        if stock_code in self.positions:
            self.positions[stock_code].current_price = price
    
    def update_all_prices(self, prices: Dict[str, float]) -> None:
        """
        批量更新持仓价格
        
        Args:
            prices: 价格字典，{股票代码: 价格}
        """
        for stock_code, price in prices.items():
            self.update_position_price(stock_code, price)
    
    def freeze_position(self, stock_code: str, volume: int) -> bool:
        """
        冻结持仓（卖出委托时调用）
        
        Args:
            stock_code: 股票代码
            volume: 要冻结的数量
            
        Returns:
            是否成功冻结
        """
        if volume <= 0:
            return False
        
        position = self.get_position(stock_code)
        
        if position.available_volume < volume:
            logger.warning(
                f"可用持仓不足，无法冻结。"
                f"股票: {stock_code}, 可用: {position.available_volume}, 需要: {volume}"
            )
            return False
        
        position.available_volume -= volume
        position.frozen_volume += volume
        
        logger.debug(f"冻结持仓: {stock_code} {volume} 股")
        return True
    
    def unfreeze_position(self, stock_code: str, volume: int) -> bool:
        """
        解冻持仓（撤单时调用）
        
        Args:
            stock_code: 股票代码
            volume: 要解冻的数量
            
        Returns:
            是否成功解冻
        """
        if volume <= 0:
            return False
        
        position = self.get_position(stock_code)
        
        if position.frozen_volume < volume:
            volume = position.frozen_volume
        
        position.frozen_volume -= volume
        position.available_volume += volume
        
        logger.debug(f"解冻持仓: {stock_code} {volume} 股")
        return True
    
    # ============================================================
    # 交易操作
    # ============================================================
    
    def buy(
        self,
        stock_code: str,
        volume: int,
        price: float,
        commission: float = 0.0,
        transfer_fee: float = 0.0
    ) -> Tuple[bool, str]:
        """
        买入股票
        
        执行买入操作，更新资金和持仓
        注意：调用前应确保资金已冻结
        
        Args:
            stock_code: 股票代码
            volume: 买入数量
            price: 买入价格
            commission: 佣金
            transfer_fee: 过户费
            
        Returns:
            (是否成功, 消息)
        """
        # 参数校验
        if volume <= 0:
            return False, "买入数量必须大于 0"
        
        if price <= 0:
            return False, "买入价格必须大于 0"
        
        # 计算总金额
        amount = volume * price
        total_cost = amount + commission + transfer_fee
        
        # 获取或创建持仓
        position = self.get_position(stock_code)
        
        # 更新持仓成本（加权平均）
        if position.total_volume > 0:
            total_cost_basis = position.avg_cost * position.total_volume + amount
            new_total_volume = position.total_volume + volume
            position.avg_cost = total_cost_basis / new_total_volume
        else:
            position.avg_cost = price
        
        # 更新持仓数量
        position.total_volume += volume
        # T+1: 当日买入的股份不可用
        # available_volume 不变，需要等到次日
        
        # 扣除资金
        self.deduct_cash(total_cost)
        
        # 记录 T+1
        self.t_plus1_records.append(TPlus1Record(
            stock_code=stock_code,
            volume=volume,
            buy_date=self.current_date,
            available_date=self._get_next_trading_day(self.current_date)
        ))
        
        # 记录交易
        self.trade_history.append({
            'type': 'buy',
            'stock_code': stock_code,
            'volume': volume,
            'price': price,
            'amount': amount,
            'commission': commission,
            'transfer_fee': transfer_fee,
            'total_cost': total_cost,
            'datetime': datetime.now()
        })
        
        logger.info(
            f"买入成功: {stock_code} {volume}股 @ {price:.2f}, "
            f"金额: {amount:,.2f}, 费用: {commission + transfer_fee:.2f}"
        )
        
        return True, "买入成功"
    
    def sell(
        self,
        stock_code: str,
        volume: int,
        price: float,
        commission: float = 0.0,
        stamp_tax: float = 0.0,
        transfer_fee: float = 0.0
    ) -> Tuple[bool, str]:
        """
        卖出股票
        
        执行卖出操作，更新资金和持仓
        注意：调用前应确保持仓已冻结
        
        Args:
            stock_code: 股票代码
            volume: 卖出数量
            price: 卖出价格
            commission: 佣金
            stamp_tax: 印花税
            transfer_fee: 过户费
            
        Returns:
            (是否成功, 消息)
        """
        # 参数校验
        if volume <= 0:
            return False, "卖出数量必须大于 0"
        
        if price <= 0:
            return False, "卖出价格必须大于 0"
        
        # 获取持仓
        position = self.get_position(stock_code)
        
        if position.frozen_volume < volume:
            return False, f"冻结持仓不足: {position.frozen_volume} < {volume}"
        
        # 计算总金额
        amount = volume * price
        total_fee = commission + stamp_tax + transfer_fee
        net_amount = amount - total_fee
        
        # 计算已实现盈亏
        realized_pnl = (price - position.avg_cost) * volume - total_fee
        
        # 更新持仓
        position.frozen_volume -= volume
        position.total_volume -= volume
        
        # 如果持仓清空，删除记录
        if position.total_volume == 0:
            del self.positions[stock_code]
        
        # 增加资金
        self.add_cash(net_amount)
        
        # 记录交易
        self.trade_history.append({
            'type': 'sell',
            'stock_code': stock_code,
            'volume': volume,
            'price': price,
            'amount': amount,
            'commission': commission,
            'stamp_tax': stamp_tax,
            'transfer_fee': transfer_fee,
            'net_amount': net_amount,
            'realized_pnl': realized_pnl,
            'datetime': datetime.now()
        })
        
        logger.info(
            f"卖出成功: {stock_code} {volume}股 @ {price:.2f}, "
            f"金额: {amount:,.2f}, 费用: {total_fee:.2f}, 盈亏: {realized_pnl:,.2f}"
        )
        
        return True, "卖出成功"
    
    # ============================================================
    # T+1 规则
    # ============================================================
    
    def _get_next_trading_day(self, current: date) -> date:
        """
        获取下一个交易日（简化版）
        
        实际应使用交易日历，这里简单返回下一个工作日
        
        Args:
            current: 当前日期
            
        Returns:
            下一个交易日
        """
        next_day = current
        while True:
            next_day += pd.Timedelta(days=1)
            # 跳过周末
            if next_day.weekday() < 5:
                return next_day
    
    def update_t_plus1(self, new_date: date) -> None:
        """
        更新日期，处理 T+1 到期
        
        将到期的买入记录转为可用持仓
        
        Args:
            new_date: 新的日期
        """
        self.current_date = new_date
        
        # 处理到期的 T+1 记录
        for record in self.t_plus1_records[:]:
            if record.available_date <= new_date:
                # 增加可用持仓
                position = self.get_position(record.stock_code)
                position.available_volume += record.volume
                
                # 移除记录
                self.t_plus1_records.remove(record)
                
                logger.debug(
                    f"T+1 到期: {record.stock_code} {record.volume}股 可用"
                )
    
    def get_available_volume(self, stock_code: str) -> int:
        """
        获取可用持仓数量
        
        Args:
            stock_code: 股票代码
            
        Returns:
            可用持仓数量
        """
        position = self.get_position(stock_code)
        return position.available_volume
    
    # ============================================================
    # 账户信息
    # ============================================================
    
    def get_account_info(self) -> dict:
        """
        获取账户信息
        
        Returns:
            账户信息字典
        """
        return {
            'initial_cash': self.initial_cash,
            'available_cash': self.available_cash,
            'frozen_cash': self.frozen_cash,
            'total_cash': self.total_cash,
            'total_market_value': self.total_market_value,
            'total_asset': self.total_asset,
            'total_profit_loss': self.total_profit_loss,
            'total_profit_loss_ratio': self.total_profit_loss_ratio,
            'position_count': len(self.positions),
            'current_date': self.current_date.isoformat()
        }
    
    def get_positions_df(self) -> pd.DataFrame:
        """
        获取持仓信息 DataFrame
        
        Returns:
            持仓信息 DataFrame
        """
        if not self.positions:
            return pd.DataFrame()
        
        data = [pos.to_dict() for pos in self.positions.values()]
        return pd.DataFrame(data)
    
    def get_trade_history_df(self) -> pd.DataFrame:
        """
        获取交易记录 DataFrame
        
        Returns:
            交易记录 DataFrame
        """
        if not self.trade_history:
            return pd.DataFrame()
        
        return pd.DataFrame(self.trade_history)
    
    def reset(self) -> None:
        """
        重置账户
        
        清空所有持仓和交易记录，恢复初始资金
        """
        self.available_cash = self.initial_cash
        self.frozen_cash = 0.0
        self.positions.clear()
        self.t_plus1_records.clear()
        self.trade_history.clear()
        
        logger.info("账户已重置")


if __name__ == "__main__":
    # 测试账户模块
    print("=" * 60)
    print("测试账户管理模块")
    print("=" * 60)
    
    # 创建账户
    account = Account(initial_cash=1000000)
    
    # 测试资金管理
    print("\n【测试资金管理】")
    print(f"初始资金: {account.total_cash:,.2f}")
    
    # 冻结资金
    account.freeze_cash(50000)
    print(f"冻结后 - 可用: {account.available_cash:,.2f}, 冻结: {account.frozen_cash:,.2f}")
    
    # 解冻资金
    account.unfreeze_cash(20000)
    print(f"解冻后 - 可用: {account.available_cash:,.2f}, 冻结: {account.frozen_cash:,.2f}")
    
    # 测试买入
    print("\n【测试买入】")
    account.freeze_cash(10500)  # 冻结买入资金
    success, msg = account.buy(
        stock_code="000001.SZ",
        volume=1000,
        price=10.5,
        commission=5.0,
        transfer_fee=0.1
    )
    print(f"买入结果: {msg}")
    
    # 查看持仓
    print("\n【持仓信息】")
    position = account.get_position("000001.SZ")
    print(f"股票: {position.stock_code}")
    print(f"总持仓: {position.total_volume}")
    print(f"可用持仓: {position.available_volume}")  # T+1，当日不可用
    print(f"成本: {position.avg_cost:.2f}")
    
    # 更新日期（模拟次日）
    print("\n【模拟次日】")
    from datetime import timedelta
    next_day = account.current_date + timedelta(days=1)
    account.update_t_plus1(next_day)
    print(f"可用持仓: {account.get_available_volume('000001.SZ')}")  # 次日可用
    
    # 测试卖出
    print("\n【测试卖出】")
    account.freeze_position("000001.SZ", 500)
    success, msg = account.sell(
        stock_code="000001.SZ",
        volume=500,
        price=11.0,
        commission=5.0,
        stamp_tax=5.5,
        transfer_fee=0.05
    )
    print(f"卖出结果: {msg}")
    
    # 查看账户信息
    print("\n【账户信息】")
    info = account.get_account_info()
    for key, value in info.items():
        print(f"{key}: {value}")
    
    print("\n" + "=" * 60)
    print("账户管理模块测试完成！")
    print("=" * 60)