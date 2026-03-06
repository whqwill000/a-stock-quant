"""
A 股量化金融平台 - 核心模块

提供数据获取、回测引擎、交易模拟器等核心功能
"""

__version__ = "0.1.0"
__author__ = "A Stock Quant Team"

# 导入核心类
from .data_fetch import AKShareFetcher, TushareFetcher, DataCache
from .backtest import BacktestEngine
from .simulator import Account, Order, OrderManager, MatchingEngine, RiskControl
from .analysis import PerformanceAnalyzer, RiskAnalyzer
from .utils import get_logger, ConfigManager

__all__ = [
    # 数据获取
    "AKShareFetcher",
    "TushareFetcher",
    "DataCache",
    # 回测引擎
    "BacktestEngine",
    # 交易模拟器
    "Account",
    "Order",
    "OrderManager",
    "MatchingEngine",
    "RiskControl",
    # 分析模块
    "PerformanceAnalyzer",
    "RiskAnalyzer",
    # 工具模块
    "get_logger",
    "ConfigManager",
]
