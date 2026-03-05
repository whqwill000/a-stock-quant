"""
辅助函数模块

提供常用的辅助函数，包括日期处理、金额格式化、数据验证等
这些函数在量化交易中经常使用，统一放在这里便于复用

使用方法:
    from core.utils.helpers import format_date, format_money, validate_stock_code
"""

from datetime import datetime, date, timedelta
from typing import Union, Optional, List, Tuple
import re
import pandas as pd
import numpy as np


# ============================================================
# 日期处理函数
# ============================================================

def format_date(
    dt: Union[datetime, date, str, None],
    fmt: str = "%Y-%m-%d"
) -> str:
    """
    格式化日期
    
    将各种格式的日期转换为指定格式的字符串
    
    Args:
        dt: 日期对象，可以是 datetime、date、字符串或 None
        fmt: 输出格式，默认 "%Y-%m-%d"
        
    Returns:
        格式化后的日期字符串
        
    Example:
        >>> format_date(datetime.now())
        '2024-01-01'
        >>> format_date("20240101", fmt="%Y年%m月%d日")
        '2024年01月01日'
    """
    if dt is None:
        return ""
    
    # 如果是字符串，尝试解析
    if isinstance(dt, str):
        # 尝试多种常见格式
        formats = [
            "%Y-%m-%d",
            "%Y%m%d",
            "%Y/%m/%d",
            "%Y年%m月%d日",
        ]
        
        for f in formats:
            try:
                dt = datetime.strptime(dt, f)
                break
            except ValueError:
                continue
        else:
            # 如果都解析失败，返回原字符串
            return dt
    
    # 格式化输出
    if isinstance(dt, (datetime, date)):
        return dt.strftime(fmt)
    
    return str(dt)


def parse_date(date_str: str) -> Optional[date]:
    """
    解析日期字符串
    
    将各种格式的日期字符串解析为 date 对象
    
    Args:
        date_str: 日期字符串
        
    Returns:
        date 对象，解析失败返回 None
        
    Example:
        >>> parse_date("2024-01-01")
        datetime.date(2024, 1, 1)
    """
    if not date_str:
        return None
    
    # 支持的日期格式
    formats = [
        "%Y-%m-%d",
        "%Y%m%d",
        "%Y/%m/%d",
        "%Y年%m月%d日",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def get_trading_days(
    start_date: Union[str, date],
    end_date: Union[str, date],
    exclude_weekends: bool = True
) -> List[date]:
    """
    获取日期范围内的交易日列表
    
    注意：这是一个简化版本，仅排除周末
    实际使用时应该排除节假日，建议使用 akshare 获取真实交易日历
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        exclude_weekends: 是否排除周末
        
    Returns:
        交易日列表
        
    Example:
        >>> days = get_trading_days("2024-01-01", "2024-01-10")
    """
    # 解析日期
    start = parse_date(start_date) if isinstance(start_date, str) else start_date
    end = parse_date(end_date) if isinstance(end_date, str) else end_date
    
    if start is None or end is None:
        return []
    
    # 生成日期列表
    days = []
    current = start
    
    while current <= end:
        # 排除周末（周六=5，周日=6）
        if exclude_weekends and current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        
        days.append(current)
        current += timedelta(days=1)
    
    return days


def is_trading_time(dt: Optional[datetime] = None) -> bool:
    """
    判断当前是否在交易时间内
    
    A 股交易时间：
    - 上午：9:30 - 11:30
    - 下午：13:00 - 15:00
    
    Args:
        dt: 要判断的时间，默认为当前时间
        
    Returns:
        是否在交易时间内
        
    Example:
        >>> is_trading_time()
        False
    """
    if dt is None:
        dt = datetime.now()
    
    # 检查是否为工作日
    if dt.weekday() >= 5:  # 周六、周日
        return False
    
    # 检查时间
    current_time = dt.time()
    
    # 上午交易时间
    from datetime import time
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    
    # 下午交易时间
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    
    return (
        (morning_start <= current_time <= morning_end) or
        (afternoon_start <= current_time <= afternoon_end)
    )


# ============================================================
# 金额格式化函数
# ============================================================

def format_money(
    amount: float,
    decimal: int = 2,
    unit: str = ""
) -> str:
    """
    格式化金额
    
    将金额格式化为易读的字符串，支持千分位分隔符
    
    Args:
        amount: 金额数值
        decimal: 小数位数，默认 2 位
        unit: 单位，如 "元"、"万"、"亿"
        
    Returns:
        格式化后的金额字符串
        
    Example:
        >>> format_money(1234567.89)
        '1,234,567.89'
        >>> format_money(123456789, unit="亿")
        '1.23亿'
    """
    # 处理单位转换
    if unit == "万":
        amount = amount / 10000
    elif unit == "亿":
        amount = amount / 100000000
    
    # 格式化数字
    formatted = f"{amount:,.{decimal}f}"
    
    # 添加单位
    if unit:
        formatted = f"{formatted}{unit}"
    
    return formatted


def format_percentage(
    value: float,
    decimal: int = 2,
    show_sign: bool = True
) -> str:
    """
    格式化百分比
    
    Args:
        value: 数值（小数形式，如 0.05 表示 5%）
        decimal: 小数位数
        show_sign: 是否显示正负号
        
    Returns:
        格式化后的百分比字符串
        
    Example:
        >>> format_percentage(0.0568)
        '+5.68%'
        >>> format_percentage(-0.0321)
        '-3.21%'
    """
    # 转换为百分比
    percentage = value * 100
    
    # 格式化
    if show_sign and percentage > 0:
        return f"+{percentage:.{decimal}f}%"
    else:
        return f"{percentage:.{decimal}f}%"


# ============================================================
# 股票代码验证函数
# ============================================================

def validate_stock_code(stock_code: str) -> bool:
    """
    验证股票代码格式
    
    A 股股票代码格式：
    - 上海主板：600xxx, 601xxx, 603xxx
    - 上海科创板：688xxx
    - 深圳主板：000xxx, 001xxx, 002xxx, 003xxx
    - 深圳创业板：300xxx, 301xxx
    - 北交所：8xxxxx, 4xxxxx
    
    Args:
        stock_code: 股票代码
        
    Returns:
        是否为有效的股票代码格式
        
    Example:
        >>> validate_stock_code("000001")
        True
        >>> validate_stock_code("600000")
        True
        >>> validate_stock_code("12345")
        False
    """
    if not stock_code:
        return False
    
    # 移除可能的后缀（如 .SH, .SZ）
    code = stock_code.split('.')[0]
    
    # 检查长度
    if len(code) != 6:
        return False
    
    # 检查是否全为数字
    if not code.isdigit():
        return False
    
    # 检查前缀
    valid_prefixes = [
        '600', '601', '603', '605',  # 上海主板
        '688',  # 科创板
        '000', '001', '002', '003',  # 深圳主板
        '300', '301',  # 创业板
        '8', '4',  # 北交所
    ]
    
    for prefix in valid_prefixes:
        if code.startswith(prefix):
            return True
    
    return False


def get_stock_exchange(stock_code: str) -> Optional[str]:
    """
    获取股票所属交易所
    
    Args:
        stock_code: 股票代码
        
    Returns:
        交易所代码：'SH'（上海）、'SZ'（深圳）、'BJ'（北交所），无法识别返回 None
        
    Example:
        >>> get_stock_exchange("600000")
        'SH'
        >>> get_stock_exchange("000001")
        'SZ'
    """
    if not stock_code:
        return None
    
    # 移除可能的后缀
    code = stock_code.split('.')[0]
    
    if len(code) != 6:
        return None
    
    # 上海交易所
    if code.startswith(('600', '601', '603', '605', '688')):
        return 'SH'
    
    # 深圳交易所
    if code.startswith(('000', '001', '002', '003', '300', '301')):
        return 'SZ'
    
    # 北交所
    if code.startswith(('8', '4')):
        return 'BJ'
    
    return None


def normalize_stock_code(stock_code: str) -> str:
    """
    标准化股票代码
    
    将各种格式的股票代码转换为标准格式（带后缀）
    
    Args:
        stock_code: 股票代码
        
    Returns:
        标准化后的股票代码，如 "000001.SZ"
        
    Example:
        >>> normalize_stock_code("000001")
        '000001.SZ'
        >>> normalize_stock_code("600000.SH")
        '600000.SH'
    """
    if not stock_code:
        return stock_code
    
    # 如果已经有后缀，直接返回
    if '.' in stock_code:
        return stock_code.upper()
    
    # 获取交易所
    exchange = get_stock_exchange(stock_code)
    
    if exchange:
        return f"{stock_code}.{exchange}"
    
    return stock_code


# ============================================================
# 数据处理函数
# ============================================================

def safe_divide(
    numerator: Union[float, np.ndarray, pd.Series],
    denominator: Union[float, np.ndarray, pd.Series],
    fill_value: float = 0.0
) -> Union[float, np.ndarray, pd.Series]:
    """
    安全除法，避免除零错误
    
    Args:
        numerator: 被除数
        denominator: 除数
        fill_value: 除数为零时的填充值
        
    Returns:
        除法结果
        
    Example:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0)
        0.0
    """
    # 处理标量
    if isinstance(numerator, (int, float)) and isinstance(denominator, (int, float)):
        if denominator == 0:
            return fill_value
        return numerator / denominator
    
    # 处理数组或 Series
    if isinstance(denominator, (np.ndarray, pd.Series)):
        result = np.where(denominator != 0, numerator / denominator, fill_value)
        if isinstance(denominator, pd.Series):
            return pd.Series(result, index=denominator.index)
        return result
    
    return fill_value


def winsorize(
    data: Union[np.ndarray, pd.Series],
    limits: Tuple[float, float] = (0.01, 0.01)
) -> Union[np.ndarray, pd.Series]:
    """
    缩尾处理（Winsorization）
    
    将极端值替换为指定分位数的值，用于处理异常值
    
    Args:
        data: 输入数据
        limits: 上下限分位数，如 (0.01, 0.01) 表示将最低 1% 和最高 1% 的值缩尾
        
    Returns:
        处理后的数据
        
    Example:
        >>> data = pd.Series([1, 2, 3, 4, 5, 100])
        >>> winsorize(data, limits=(0.1, 0.1))
        # 极端值 100 会被替换
    """
    lower_limit, upper_limit = limits
    
    # 计算分位数
    lower_quantile = np.quantile(data, lower_limit)
    upper_quantile = np.quantile(data, 1 - upper_limit)
    
    # 缩尾处理
    if isinstance(data, pd.Series):
        return data.clip(lower=lower_quantile, upper=upper_quantile)
    else:
        return np.clip(data, lower_quantile, upper_quantile)


def standardize(
    data: Union[np.ndarray, pd.Series],
    method: str = "zscore"
) -> Union[np.ndarray, pd.Series]:
    """
    数据标准化
    
    Args:
        data: 输入数据
        method: 标准化方法
            - "zscore": Z-Score 标准化 (x - mean) / std
            - "minmax": Min-Max 标准化 (x - min) / (max - min)
            
    Returns:
        标准化后的数据
        
    Example:
        >>> data = pd.Series([1, 2, 3, 4, 5])
        >>> standardize(data, method="zscore")
    """
    if method == "zscore":
        mean = np.mean(data)
        std = np.std(data)
        return safe_divide(data - mean, std, fill_value=0.0)
    
    elif method == "minmax":
        min_val = np.min(data)
        max_val = np.max(data)
        return safe_divide(data - min_val, max_val - min_val, fill_value=0.5)
    
    else:
        raise ValueError(f"未知的标准化方法: {method}")


# ============================================================
# 其他辅助函数
# ============================================================

def calculate_commission(
    amount: float,
    rate: float = 0.00025,
    min_commission: float = 5.0
) -> float:
    """
    计算交易佣金
    
    Args:
        amount: 交易金额
        rate: 佣金费率，默认万分之 2.5
        min_commission: 最低佣金，默认 5 元
        
    Returns:
        佣金金额
        
    Example:
        >>> calculate_commission(10000)  # 1 万元交易
        5.0  # 低于最低佣金，收取 5 元
        >>> calculate_commission(100000)  # 10 万元交易
        25.0  # 万分之 2.5
    """
    commission = amount * rate
    return max(commission, min_commission)


def calculate_stamp_tax(amount: float, rate: float = 0.0005) -> float:
    """
    计算印花税（仅卖出时收取）
    
    Args:
        amount: 卖出金额
        rate: 印花税率，默认 0.05%
        
    Returns:
        印花税金额
        
    Example:
        >>> calculate_stamp_tax(10000)
        5.0
    """
    return amount * rate


def calculate_transfer_fee(volume: int, rate: float = 0.00001) -> float:
    """
    计算过户费（按股数收取）
    
    Args:
        volume: 成交股数
        rate: 过户费率，默认每股 0.00001 元
        
    Returns:
        过户费金额
        
    Example:
        >>> calculate_transfer_fee(1000)
        0.01
    """
    return volume * rate


def round_price(price: float, tick_size: float = 0.01) -> float:
    """
    将价格四舍五入到最小变动单位
    
    A 股最小变动单位为 0.01 元
    
    Args:
        price: 原始价格
        tick_size: 最小变动单位
        
    Returns:
        调整后的价格
        
    Example:
        >>> round_price(10.567)
        10.57
    """
    return round(price / tick_size) * tick_size


def round_volume(volume: int, lot_size: int = 100) -> int:
    """
    将数量调整为整手数
    
    A 股最小交易单位为 100 股（1 手）
    
    Args:
        volume: 原始数量
        lot_size: 每手股数
        
    Returns:
        调整后的数量（向下取整到整手）
        
    Example:
        >>> round_volume(150)
        100
        >>> round_volume(250)
        200
    """
    return (volume // lot_size) * lot_size


if __name__ == "__main__":
    # 测试辅助函数
    print("=" * 60)
    print("测试辅助函数模块")
    print("=" * 60)
    
    # 测试日期格式化
    print("\n【日期格式化】")
    print(f"当前日期: {format_date(datetime.now())}")
    print(f"解析日期: {parse_date('2024-01-01')}")
    
    # 测试金额格式化
    print("\n【金额格式化】")
    print(f"金额: {format_money(1234567.89)}")
    print(f"金额（万）: {format_money(123456789, unit='万')}")
    print(f"百分比: {format_percentage(0.0568)}")
    
    # 测试股票代码验证
    print("\n【股票代码验证】")
    print(f"000001 有效: {validate_stock_code('000001')}")
    print(f"600000 有效: {validate_stock_code('600000')}")
    print(f"000001 交易所: {get_stock_exchange('000001')}")
    print(f"标准化: {normalize_stock_code('000001')}")
    
    # 测试交易成本计算
    print("\n【交易成本计算】")
    print(f"佣金（1 万）: {calculate_commission(10000)} 元")
    print(f"佣金（10 万）: {calculate_commission(100000)} 元")
    print(f"印花税（10 万）: {calculate_stamp_tax(100000)} 元")
    
    print("\n" + "=" * 60)
    print("辅助函数模块测试完成！")
    print("=" * 60)