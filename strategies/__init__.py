"""
A 股量化金融平台 - 策略模块

提供多种量化交易策略的实现
"""

__version__ = "0.1.0"
__author__ = "A Stock Quant Team"

# 导入策略基类
from .base import BaseStrategy, StrategyConfig, Signal

# 动态导入策略模块（避免数字开头的模块名问题）
import importlib
import sys

# 策略模块映射
_strategy_modules = {
    'trend_following': '_01_trend_following',
    'mean_reversion': '_02_mean_reversion',
    'multi_factor': '_03_multi_factor',
    'momentum': '_04_momentum',
    'arbitrage': '_05_arbitrage',
    'event_driven': '_06_event_driven',
    'capital_flow': '_07_capital_flow',
}

# 动态导入策略类
for strategy_name, module_name in _strategy_modules.items():
    try:
        module_name_underscore = module_name.replace('-', '_')
        # 使用正确的模块名
        if strategy_name == 'trend_following':
            module = importlib.import_module(f'.{module_name_underscore}.trend_strategy', __package__)
        else:
            module = importlib.import_module(f'.{module_name_underscore}.{strategy_name}_strategy', __package__)
        
        # 获取模块中的所有类
        for attr_name in dir(module):
            if attr_name.endswith('Strategy') and attr_name != 'BaseStrategy':
                # 动态导入所有策略类
                strategy_class = getattr(module, attr_name)
                if hasattr(strategy_class, '__bases__'):
                    globals()[attr_name] = strategy_class
    except ImportError as e:
        pass

__all__ = [
    # 基类
    "BaseStrategy",
    "StrategyConfig",
    "Signal",
    # 具体策略
    "TrendFollowingStrategy",
    "MeanReversionStrategy",
    "MultiFactorStrategy",
    "MomentumStrategy",
    "ConvertibleBondArbitrageStrategy",
    "ETFArbitrageStrategy",
    "IndexFuturesArbitrageStrategy",
    "StatisticalArbitrageStrategy",
    "EventDrivenStrategy",
    "CapitalFlowStrategy",
]
