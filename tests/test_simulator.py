"""
测试交易模拟器模块

测试账户、订单、撮合、风控等交易模拟器功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.simulator.account import Account, Position
from core.simulator.order import Order, OrderManager, OrderStatus, OrderType, Trade
from core.simulator.matching import MatchingEngine, MarketData, PriceLimitRule
from core.simulator.risk_control import RiskControl, RiskConfig


class TestAccount:
    """测试账户模块"""
    
    def test_account_initialization(self):
        """测试账户初始化"""
        account = Account(initial_cash=1000000)
        
        assert account.initial_cash == 1000000
        assert account.available_cash == 1000000
        assert account.frozen_cash == 0
        assert len(account.positions) == 0
    
    def test_freeze_cash(self):
        """测试资金冻结"""
        account = Account(initial_cash=1000000)
        
        # 正常冻结
        assert account.freeze_cash(100000) == True
        assert account.available_cash == 900000
        assert account.frozen_cash == 100000
        
        # 冻结超过可用资金
        assert account.freeze_cash(1000000) == False
    
    def test_unfreeze_cash(self):
        """测试资金解冻"""
        account = Account(initial_cash=1000000)
        account.freeze_cash(100000)
        
        account.unfreeze_cash(50000)
        
        assert account.available_cash == 950000
        assert account.frozen_cash == 50000
    
    def test_buy_stock(self):
        """测试买入股票"""
        account = Account(initial_cash=1000000)
        account.freeze_cash(10500)
        
        success, msg = account.buy(
            stock_code="000001.SZ",
            volume=1000,
            price=10.5,
            commission=5.0,
            transfer_fee=0.1
        )
        
        assert success == True
        assert account.get_position("000001.SZ").total_volume == 1000
        # T+1，当日不可用
        assert account.get_position("000001.SZ").available_volume == 0
    
    def test_sell_stock(self):
        """测试卖出股票"""
        account = Account(initial_cash=1000000)
        
        # 先买入
        account.freeze_cash(10500)
        account.buy("000001.SZ", 1000, 10.5, 5.0, 0.1)
        
        # 模拟次日
        next_day = account.current_date + timedelta(days=1)
        account.update_t_plus1(next_day)
        
        # 冻结持仓并卖出
        account.freeze_position("000001.SZ", 500)
        success, msg = account.sell(
            stock_code="000001.SZ",
            volume=500,
            price=11.0,
            commission=5.0,
            stamp_tax=5.5,
            transfer_fee=0.05
        )
        
        assert success == True
        assert account.get_position("000001.SZ").total_volume == 500
    
    def test_t_plus1(self):
        """测试 T+1 规则"""
        account = Account(initial_cash=1000000)
        account.freeze_cash(10500)
        account.buy("000001.SZ", 1000, 10.5, 5.0, 0.1)
        
        # 当日不可用
        assert account.get_available_volume("000001.SZ") == 0
        
        # 次日可用
        next_day = account.current_date + timedelta(days=1)
        account.update_t_plus1(next_day)
        
        assert account.get_available_volume("000001.SZ") == 1000
    
    def test_account_info(self):
        """测试账户信息"""
        account = Account(initial_cash=1000000)
        
        info = account.get_account_info()
        
        assert info['initial_cash'] == 1000000
        assert info['available_cash'] == 1000000
        assert info['total_asset'] == 1000000


class TestOrder:
    """测试订单模块"""
    
    def test_order_creation(self):
        """测试订单创建"""
        order = Order(
            stock_code="000001.SZ",
            direction="buy",
            order_type="limit",
            price=10.5,
            volume=1000
        )
        
        assert order.stock_code == "000001.SZ"
        assert order.direction == "buy"
        assert order.price == 10.5
        assert order.volume == 1000
        assert order.status == OrderStatus.PENDING.value
    
    def test_order_validation(self):
        """测试订单验证"""
        # 无效方向
        with pytest.raises(ValueError):
            Order(
                stock_code="000001.SZ",
                direction="invalid",
                order_type="limit",
                price=10.5,
                volume=1000
            )
        
        # 无效价格
        with pytest.raises(ValueError):
            Order(
                stock_code="000001.SZ",
                direction="buy",
                order_type="limit",
                price=0,
                volume=1000
            )
    
    def test_order_update_fill(self):
        """测试订单成交更新"""
        order = Order(
            stock_code="000001.SZ",
            direction="buy",
            order_type="limit",
            price=10.5,
            volume=1000
        )
        
        order.update_fill(500, 10.48)
        
        assert order.filled_volume == 500
        assert order.avg_price == 10.48
        assert order.status == OrderStatus.PARTIAL.value
    
    def test_order_cancel(self):
        """测试订单撤销"""
        order = Order(
            stock_code="000001.SZ",
            direction="buy",
            order_type="limit",
            price=10.5,
            volume=1000
        )
        
        order.cancel()
        
        assert order.status == OrderStatus.CANCELLED.value


class TestOrderManager:
    """测试订单管理器"""
    
    def test_create_order(self):
        """测试创建订单"""
        manager = OrderManager()
        
        order = manager.create_order(
            stock_code="000001.SZ",
            direction="buy",
            order_type="limit",
            price=10.5,
            volume=1000
        )
        
        assert order.order_id in manager.orders
    
    def test_submit_order(self):
        """测试提交订单"""
        manager = OrderManager()
        order = manager.create_order(
            stock_code="000001.SZ",
            direction="buy",
            order_type="limit",
            price=10.5,
            volume=1000
        )
        
        manager.submit_order(order.order_id)
        
        assert manager.get_order(order.order_id).status == OrderStatus.SUBMITTED.value
    
    def test_cancel_order(self):
        """测试撤销订单"""
        manager = OrderManager()
        order = manager.create_order(
            stock_code="000001.SZ",
            direction="buy",
            order_type="limit",
            price=10.5,
            volume=1000
        )
        manager.submit_order(order.order_id)
        
        manager.cancel_order(order.order_id)
        
        assert manager.get_order(order.order_id).status == OrderStatus.CANCELLED.value


class TestMatchingEngine:
    """测试撮合引擎"""
    
    def test_match_limit_buy_order(self):
        """测试限价买入订单撮合"""
        engine = MatchingEngine()
        
        order = Order(
            stock_code="000001.SZ",
            direction="buy",
            order_type="limit",
            price=10.5,
            volume=1000
        )
        order.status = OrderStatus.SUBMITTED.value
        
        market_data = MarketData(
            stock_code="000001.SZ",
            date=datetime.now(),
            open=10.3,
            high=10.8,
            low=10.2,
            close=10.6,
            limit_up=11.0,
            limit_down=9.0
        )
        
        trades = engine.match(order, market_data)
        
        assert len(trades) == 1
        assert trades[0].volume == 1000
    
    def test_match_limit_sell_order(self):
        """测试限价卖出订单撮合"""
        engine = MatchingEngine()
        
        order = Order(
            stock_code="000001.SZ",
            direction="sell",
            order_type="limit",
            price=10.5,
            volume=1000
        )
        order.status = OrderStatus.SUBMITTED.value
        
        market_data = MarketData(
            stock_code="000001.SZ",
            date=datetime.now(),
            open=10.6,
            high=10.8,
            low=10.2,
            close=10.7,
            limit_up=11.0,
            limit_down=9.0
        )
        
        trades = engine.match(order, market_data)
        
        assert len(trades) == 1
    
    def test_price_limit_rule(self):
        """测试涨跌停规则"""
        rule = PriceLimitRule()
        
        # 主板
        limit_up, limit_down = rule.calculate_limit_prices("600000.SH", 10.0)
        assert limit_up == 11.0
        assert limit_down == 9.0
        
        # 科创板
        limit_up, limit_down = rule.calculate_limit_prices("688001.SH", 50.0)
        assert limit_up == 60.0
        assert limit_down == 40.0


class TestRiskControl:
    """测试风控模块"""
    
    def test_check_buy_order(self):
        """测试买入订单风控检查"""
        risk = RiskControl()
        account = Account(initial_cash=1000000)
        
        order = Order(
            stock_code="000001.SZ",
            direction="buy",
            order_type="limit",
            price=10.0,
            volume=1000
        )
        order.status = OrderStatus.SUBMITTED.value
        
        passed, reason = risk.check_buy_order(order, account, 10.0)
        
        assert passed == True
    
    def test_check_sell_order(self):
        """测试卖出订单风控检查"""
        risk = RiskControl()
        account = Account(initial_cash=1000000)
        
        # 先买入
        account.freeze_cash(10500)
        account.buy("000001.SZ", 1000, 10.0, 5.0, 0.1)
        next_day = account.current_date + timedelta(days=1)
        account.update_t_plus1(next_day)
        
        order = Order(
            stock_code="000001.SZ",
            direction="sell",
            order_type="limit",
            price=10.5,
            volume=500
        )
        order.status = OrderStatus.SUBMITTED.value
        
        passed, reason = risk.check_sell_order(order, account)
        
        assert passed == True
    
    def test_stop_loss(self):
        """测试止损检查"""
        risk = RiskControl()
        
        position = Position(
            stock_code="000001.SZ",
            total_volume=1000,
            available_volume=1000,
            avg_cost=10.0,
            current_price=9.0  # 亏损 10%
        )
        
        is_stop, ratio, reason = risk.check_stop_loss("000001.SZ", 9.0, position)
        
        assert is_stop == True
    
    def test_take_profit(self):
        """测试止盈检查"""
        risk = RiskControl()
        
        position = Position(
            stock_code="000001.SZ",
            total_volume=1000,
            available_volume=1000,
            avg_cost=10.0,
            current_price=12.0  # 盈利 20%
        )
        
        is_profit, ratio, reason = risk.check_take_profit("000001.SZ", 12.0, position)
        
        assert is_profit == True


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])