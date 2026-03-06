"""
测试工具模块

测试日志、配置、辅助函数等工具模块的功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils.logger import get_logger, setup_logging, LoggerContext
from core.utils.config import Config, ConfigManager
from core.utils.helpers import (
    format_date, parse_date, get_trading_days, is_trading_time,
    format_money, format_percentage,
    validate_stock_code, get_stock_exchange, normalize_stock_code,
    safe_divide, winsorize, standardize,
    calculate_commission, calculate_stamp_tax, calculate_transfer_fee,
    round_price, round_volume
)


class TestLogger:
    """测试日志模块"""
    
    def test_get_logger(self):
        """测试获取日志记录器"""
        logger = get_logger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"
    
    def test_logger_levels(self):
        """测试日志级别"""
        logger = get_logger("test_levels")
        
        # 测试各级别日志
        logger.debug("调试信息")
        logger.info("普通信息")
        logger.warning("警告信息")
        logger.error("错误信息")
    
    def test_logger_context(self):
        """测试日志上下文"""
        logger = get_logger("test_context")
        
        with LoggerContext(logger, level=10):  # DEBUG level
            logger.debug("这条调试信息应该输出")


class TestConfig:
    """测试配置模块"""
    
    def test_config_get_set(self):
        """测试配置的获取和设置"""
        config = Config({
            "app": {
                "name": "测试应用",
                "version": "1.0.0"
            }
        })
        
        # 测试获取
        assert config.get("app.name") == "测试应用"
        assert config.get("app.version") == "1.0.0"
        assert config.get("not.exist", default="默认值") == "默认值"
        
        # 测试设置
        config.set("app.name", "新名称")
        assert config.get("app.name") == "新名称"
    
    def test_config_dict_access(self):
        """测试字典式访问"""
        config = Config({"key": "value"})
        
        assert config["key"] == "value"
        assert "key" in config
    
    def test_config_update(self):
        """测试配置更新"""
        config = Config({"a": 1})
        config.update({"b": 2})
        
        assert config.get("a") == 1
        assert config.get("b") == 2


class TestHelpers:
    """测试辅助函数模块"""
    
    def test_format_date(self):
        """测试日期格式化"""
        # 测试 datetime 对象
        dt = datetime(2024, 1, 15)
        assert format_date(dt) == "2024-01-15"
        
        # 测试字符串
        assert format_date("20240115") == "2024-01-15"
        
        # 测试自定义格式
        assert format_date(dt, fmt="%Y年%m月%d日") == "2024年01月15日"
    
    def test_parse_date(self):
        """测试日期解析"""
        assert parse_date("2024-01-15") == date(2024, 1, 15)
        assert parse_date("20240115") == date(2024, 1, 15)
        assert parse_date("invalid") is None
    
    def test_format_money(self):
        """测试金额格式化"""
        assert format_money(1234567.89) == "1,234,567.89"
        assert format_money(123456789, unit="亿") == "1.23亿"
    
    def test_format_percentage(self):
        """测试百分比格式化"""
        assert format_percentage(0.0568) == "+5.68%"
        assert format_percentage(-0.0321) == "-3.21%"
    
    def test_validate_stock_code(self):
        """测试股票代码验证"""
        assert validate_stock_code("000001") == True
        assert validate_stock_code("600000") == True
        assert validate_stock_code("688001") == True
        assert validate_stock_code("300001") == True
        assert validate_stock_code("12345") == False
    
    def test_get_stock_exchange(self):
        """测试获取交易所"""
        assert get_stock_exchange("600000") == "SH"
        assert get_stock_exchange("000001") == "SZ"
        assert get_stock_exchange("688001") == "SH"
        assert get_stock_exchange("300001") == "SZ"
    
    def test_normalize_stock_code(self):
        """测试标准化股票代码"""
        assert normalize_stock_code("000001") == "000001.SZ"
        assert normalize_stock_code("600000") == "600000.SH"
        assert normalize_stock_code("600000.SH") == "600000.SH"
    
    def test_safe_divide(self):
        """测试安全除法"""
        assert safe_divide(10, 2) == 5.0
        assert safe_divide(10, 0) == 0.0
        assert safe_divide(10, 0, fill_value=-1) == -1
    
    def test_winsorize(self):
        """测试缩尾处理"""
        data = pd.Series([1, 2, 3, 4, 5, 100])
        result = winsorize(data, limits=(0.1, 0.1))
        
        # 极端值应该被处理
        assert result.max() < 100
    
    def test_standardize(self):
        """测试标准化"""
        data = pd.Series([1, 2, 3, 4, 5])
        result = standardize(data, method="zscore")

        # 标准化后均值应接近0
        if isinstance(result, pd.Series):
            assert abs(result.mean()) < 1e-10
        else:
            assert abs(np.mean(result)) < 1e-10
    
    def test_calculate_commission(self):
        """测试佣金计算"""
        # 低于最低佣金
        assert calculate_commission(10000) == 5.0
        
        # 高于最低佣金
        assert calculate_commission(100000) == 25.0
    
    def test_calculate_stamp_tax(self):
        """测试印花税计算"""
        assert calculate_stamp_tax(10000) == 5.0
        assert calculate_stamp_tax(100000) == 50.0
    
    def test_round_price(self):
        """测试价格取整"""
        assert round_price(10.567) == 10.57
        assert round_price(10.562) == 10.56
    
    def test_round_volume(self):
        """测试数量取整"""
        assert round_volume(150) == 100
        assert round_volume(250) == 200


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])