"""
策略实现模块

[策略名称] - [简短描述]
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class Signal:
    """交易信号数据类"""
    stock_code: str       # 股票代码
    action: str           # 买卖方向：buy/sell
    price: float          # 信号价格
    volume: int           # 建议数量
    strength: float       # 信号强度 (0-1)
    reason: str           # 信号原因


class Strategy:
    """
    策略基类
    
    所有策略类都应继承此类，并实现 generate_signals 方法
    """
    
    def __init__(self, name: str, params: dict = None):
        """
        初始化策略
        
        Args:
            name: 策略名称
            params: 策略参数字典
        """
        self.name = name
        self.params = params or {}
        self.positions: Dict[str, int] = {}  # 当前持仓
        
    def generate_signals(
        self, 
        data: pd.DataFrame,
        current_date: str
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 市场数据 DataFrame，包含以下列：
                  - stock_code: 股票代码
                  - date: 日期
                  - open: 开盘价
                  - high: 最高价
                  - low: 最低价
                  - close: 收盘价
                  - volume: 成交量
                  - 其他指标数据...
            current_date: 当前日期
            
        Returns:
            信号列表
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            df: 原始数据
            
        Returns:
            添加指标后的数据
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def update_position(self, stock_code: str, volume: int):
        """
        更新持仓信息
        
        Args:
            stock_code: 股票代码
            volume: 持仓变化（正数买入，负数卖出）
        """
        if stock_code not in self.positions:
            self.positions[stock_code] = 0
        self.positions[stock_code] += volume
        if self.positions[stock_code] == 0:
            del self.positions[stock_code]


# ============================================================
# 示例策略：双均线趋势跟踪策略
# ============================================================

class DoubleMAStrategy(Strategy):
    """
    双均线趋势跟踪策略
    
    原理：
    - 短期均线上穿长期均线时买入（金叉）
    - 短期均线下穿长期均线时卖出（死叉）
    """
    
    def __init__(self, params: dict = None):
        super().__init__("双均线策略", params)
        
        # 策略参数
        self.ma_short = self.params.get("ma_short", 5)    # 短期均线
        self.ma_long = self.params.get("ma_long", 20)     # 长期均线
        self.position_size = self.params.get("position_size", 0.1)  # 仓位
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算均线指标"""
        df = df.copy()
        
        # 计算均线
        df["ma_short"] = df["close"].rolling(window=self.ma_short).mean()
        df["ma_long"] = df["close"].rolling(window=self.ma_long).mean()
        
        # 计算均线差值
        df["ma_diff"] = df["ma_short"] - df["ma_long"]
        
        # 计算差值变化（用于判断交叉）
        df["ma_diff_prev"] = df["ma_diff"].shift(1)
        
        return df
    
    def generate_signals(
        self, 
        data: pd.DataFrame,
        current_date: str
    ) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        for stock_code in data["stock_code"].unique():
            stock_data = data[data["stock_code"] == stock_code].copy()
            
            # 计算指标
            stock_data = self.calculate_indicators(stock_data)
            
            # 获取最新数据
            latest = stock_data.iloc[-1]
            prev = stock_data.iloc[-2] if len(stock_data) > 1 else latest
            
            # 判断金叉：短期均线从下方上穿长期均线
            golden_cross = (prev["ma_diff"] < 0) and (latest["ma_diff"] > 0)
            
            # 判断死叉：短期均线从上方下穿长期均线
            death_cross = (prev["ma_diff"] > 0) and (latest["ma_diff"] < 0)
            
            # 生成信号
            if golden_cross:
                signals.append(Signal(
                    stock_code=stock_code,
                    action="buy",
                    price=latest["close"],
                    volume=1000,  # 示例数量，实际应根据仓位计算
                    strength=0.8,
                    reason=f"金叉：MA{self.ma_short}上穿 MA{self.ma_long}"
                ))
            elif death_cross:
                signals.append(Signal(
                    stock_code=stock_code,
                    action="sell",
                    price=latest["close"],
                    volume=self.positions.get(stock_code, 0),
                    strength=0.8,
                    reason=f"死叉：MA{self.ma_short}下穿 MA{self.ma_long}"
                ))
        
        return signals


# ============================================================
# 策略注册（供回测引擎使用）
# ============================================================

def get_strategy_class(strategy_type: str):
    """
    获取策略类
    
    Args:
        strategy_type: 策略类型
        
    Returns:
        策略类
    """
    strategies = {
        "double_ma": DoubleMAStrategy,
        # 添加更多策略...
    }
    
    if strategy_type not in strategies:
        raise ValueError(f"未知策略类型：{strategy_type}")
    
    return strategies[strategy_type]
