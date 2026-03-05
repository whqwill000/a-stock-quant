"""
A 股量化金融平台 - 核心模块

提供数据获取、回测引擎、交易模拟器等核心功能
"""

__version__ = "0.1.0"
__author__ = "A Stock Quant Team"

from .data_fetch import DataFetcher
from .backtest import BacktestEngine
from .simulator import TradingSimulator

__all__ = [
    "DataFetcher",
    "BacktestEngine",
    "TradingSimulator",
]
