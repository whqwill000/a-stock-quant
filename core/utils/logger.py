"""
日志工具模块

提供统一的日志记录功能，支持控制台输出和文件输出
支持彩色日志输出，便于调试和问题排查

使用方法:
    from core.utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# 尝试导入彩色日志库，如果不存在则使用标准库
try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称，通常使用 __name__
        level: 日志级别，默认 INFO
        log_file: 日志文件路径，如果为 None 则不输出到文件
        format_string: 自定义日志格式字符串
        
    Returns:
        配置好的日志记录器
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("系统启动成功")
    """
    # 获取或创建日志记录器
    logger = logging.getLogger(name)
    
    # 如果已经有处理器，直接返回（避免重复添加处理器）
    if logger.handlers:
        return logger
    
    # 设置日志级别
    logger.setLevel(level)
    
    # 默认日志格式
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 日期格式
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 创建控制台处理器
    if HAS_COLORLOG:
        # 使用彩色日志输出
        console_format = (
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s"
        )
        log_colors = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            colorlog.ColoredFormatter(
                console_format,
                datefmt=date_format,
                log_colors=log_colors
            )
        )
    else:
        # 使用标准日志输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(format_string, datefmt=date_format)
        )
    
    # 设置控制台处理器级别
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(format_string, datefmt=date_format)
        )
        logger.addHandler(file_handler)
    
    return logger


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> None:
    """
    全局日志配置
    
    配置根日志记录器，影响所有模块的日志输出
    
    Args:
        log_level: 日志级别字符串，可选 DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_file: 日志文件路径
        log_format: 日志格式字符串
        
    Example:
        >>> setup_logging(log_level="DEBUG", log_file="logs/app.log")
    """
    # 日志级别映射
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    # 获取日志级别
    level = level_map.get(log_level.upper(), logging.INFO)
    
    # 配置根日志记录器
    logging.basicConfig(
        level=level,
        format=log_format or "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ] if not log_file else [
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8'),
        ]
    )


class LoggerContext:
    """
    日志上下文管理器
    
    用于临时修改日志级别或添加额外的日志信息
    
    Example:
        >>> with LoggerContext(logger, level=logging.DEBUG):
        ...     logger.debug("这条调试信息会被输出")
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        level: Optional[int] = None,
        extra: Optional[dict] = None
    ):
        """
        初始化日志上下文
        
        Args:
            logger: 日志记录器
            level: 临时日志级别
            extra: 额外的上下文信息
        """
        self.logger = logger
        self.original_level = logger.level
        self.temp_level = level
        self.extra = extra or {}
    
    def __enter__(self):
        """进入上下文，设置临时日志级别"""
        if self.temp_level is not None:
            self.logger.setLevel(self.temp_level)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文，恢复原始日志级别"""
        self.logger.setLevel(self.original_level)
        return False


# 创建默认日志记录器
default_logger = get_logger("a_stock_quant")


if __name__ == "__main__":
    # 测试日志功能
    logger = get_logger("test")
    
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    logger.critical("这是一条严重错误信息")
    
    # 测试日志上下文
    print("\n测试日志上下文：")
    with LoggerContext(logger, level=logging.DEBUG):
        logger.debug("临时开启的调试信息")