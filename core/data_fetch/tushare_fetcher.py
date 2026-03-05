"""
Tushare 数据获取器

使用 Tushare Pro API 获取 A 股市场数据
Tushare 是专业的金融数据平台，数据质量高，需要注册获取 token

主要功能：
- 获取股票历史行情数据
- 获取股票列表和基本信息
- 获取指数数据
- 获取财务数据
- 获取资金流向数据

使用方法:
    from core.data_fetch.tushare_fetcher import TushareFetcher
    
    fetcher = TushareFetcher(token="your_token")
    df = fetcher.get_stock_daily("000001.SZ", start_date="20230101")
"""

import time
from datetime import datetime, date
from typing import Optional, List, Dict, Union
import pandas as pd
import numpy as np

# 导入 Tushare
try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False

# 导入项目模块
from core.utils.logger import get_logger
from core.utils.helpers import normalize_stock_code, validate_stock_code
from core.data_fetch.data_cache import DataFrameCache

# 获取日志记录器
logger = get_logger(__name__)


class TushareFetcher:
    """
    Tushare 数据获取器
    
    封装 Tushare Pro API 的常用接口，提供统一的 A 股数据获取功能
    支持数据缓存，减少重复请求
    
    注意：Tushare 需要注册获取 token，部分接口需要积分权限
    
    Attributes:
        pro: Tushare Pro API 实例
        cache: 数据缓存实例
        retry_times: 请求失败重试次数
        retry_delay: 重试间隔（秒）
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        cache_enabled: bool = True,
        cache_dir: str = "data/cache",
        cache_expire_hours: int = 24,
        retry_times: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化 Tushare 数据获取器
        
        Args:
            token: Tushare API token，如果为 None 则尝试从环境变量读取
            cache_enabled: 是否启用缓存
            cache_dir: 缓存目录
            cache_expire_hours: 缓存过期时间（小时）
            retry_times: 请求失败重试次数
            retry_delay: 重试间隔（秒）
        """
        # 检查 Tushare 是否可用
        if not TUSHARE_AVAILABLE:
            raise ImportError(
                "Tushare 未安装，请运行: pip install tushare"
            )
        
        # 获取 token
        import os
        self.token = token or os.environ.get('TUSHARE_TOKEN')
        
        if not self.token:
            logger.warning(
                "未设置 Tushare token，部分功能可能受限。"
                "请访问 https://tushare.pro 注册获取 token"
            )
        else:
            # 设置 token
            ts.set_token(self.token)
            logger.info("Tushare token 已设置")
        
        # 初始化 Pro API
        self.pro = ts.pro_api()
        
        # 初始化缓存
        self.cache = DataFrameCache(
            cache_dir=cache_dir,
            expire_hours=cache_expire_hours,
            enabled=cache_enabled
        )
        
        # 重试配置
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        
        logger.info("Tushare 数据获取器初始化完成")
    
    def _retry_request(self, func, *args, **kwargs):
        """
        带重试的请求包装器
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        last_error = None
        
        for attempt in range(self.retry_times):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    f"请求失败 (尝试 {attempt + 1}/{self.retry_times}): {e}"
                )
                if attempt < self.retry_times - 1:
                    time.sleep(self.retry_delay)
        
        logger.error(f"请求最终失败: {last_error}")
        raise last_error
    
    # ============================================================
    # 股票基础数据
    # ============================================================
    
    def get_stock_list(
        self,
        exchange: str = "",
        list_status: str = "L"
    ) -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            exchange: 交易所代码，"" 表示全部，"SSE" 上交所，"SZSE" 深交所
            list_status: 上市状态，"L" 上市，"D" 退市，"P" 暂停上市
            
        Returns:
            股票列表 DataFrame
            
        Example:
            >>> fetcher = TushareFetcher(token="your_token")
            >>> df = fetcher.get_stock_list()
        """
        cache_key = f"stock_list_{exchange}_{list_status}"
        
        # 尝试从缓存获取
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info(f"获取股票列表 (交易所={exchange}, 状态={list_status})...")
            
            # 使用 Tushare 接口
            df = self._retry_request(
                self.pro.stock_basic,
                exchange=exchange,
                list_status=list_status,
                fields='ts_code,symbol,name,area,industry,list_date'
            )
            
            # 缓存数据
            self.cache.set(cache_key, df, expire_hours=24)
            
            logger.info(f"获取到 {len(df)} 只股票")
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise
    
    def get_stock_info(self, stock_code: str) -> Dict:
        """
        获取股票基本信息
        
        Args:
            stock_code: 股票代码，如 "000001.SZ"
            
        Returns:
            股票基本信息字典
        """
        # 标准化股票代码
        ts_code = normalize_stock_code(stock_code)
        
        try:
            df = self._retry_request(
                self.pro.stock_basic,
                ts_code=ts_code,
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )
            
            if df.empty:
                return {}
            
            return df.iloc[0].to_dict()
            
        except Exception as e:
            logger.error(f"获取股票信息失败 {stock_code}: {e}")
            return {}
    
    # ============================================================
    # 行情数据
    # ============================================================
    
    def get_stock_daily(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取股票日线行情数据
        
        Args:
            stock_code: 股票代码，如 "000001.SZ"
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
            adjust: 复权类型
                - "qfq": 前复权
                - "hfq": 后复权
                - None: 不复权
                
        Returns:
            日线行情 DataFrame
            
        Example:
            >>> fetcher = TushareFetcher(token="your_token")
            >>> df = fetcher.get_stock_daily("000001.SZ", start_date="20230101")
        """
        # 标准化股票代码
        ts_code = normalize_stock_code(stock_code)
        
        # 处理日期格式
        if start_date:
            start_date = start_date.replace('-', '')
        if end_date:
            end_date = end_date.replace('-', '')
        
        # 构建缓存键
        cache_key = f"daily_{ts_code}_{start_date or 'start'}_{end_date or 'end'}_{adjust}"
        
        # 尝试从缓存获取
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"从缓存获取日线数据: {stock_code}")
            return cached
        
        try:
            logger.info(f"获取 {stock_code} 日线数据...")
            
            # 根据复权类型选择接口
            if adjust == "qfq":
                # 前复权
                df = self._retry_request(
                    self.pro.daily,
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # 获取复权因子
                adj_factor = self._retry_request(
                    self.pro.adj_factor,
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if not adj_factor.empty:
                    df = df.merge(adj_factor[['trade_date', 'adj_factor']], on='trade_date')
                    # 应用复权因子
                    for col in ['open', 'high', 'low', 'close', 'pre_close']:
                        if col in df.columns:
                            df[col] = df[col] * df['adj_factor']
                    df = df.drop(columns=['adj_factor'])
                    
            elif adjust == "hfq":
                # 后复权（简化处理，实际需要更复杂的逻辑）
                df = self._retry_request(
                    self.pro.daily,
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # 不复权
                df = self._retry_request(
                    self.pro.daily,
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date
                )
            
            # 标准化列名
            column_mapping = {
                'trade_date': 'date',
                'vol': 'volume',
                'amount': 'amount',
                'pct_chg': 'pct_change'
            }
            df = df.rename(columns=column_mapping)
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            
            # 添加股票代码列
            df['stock_code'] = ts_code
            
            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            
            # 缓存数据
            self.cache.set(cache_key, df)
            
            logger.info(f"获取到 {len(df)} 条日线数据")
            return df
            
        except Exception as e:
            logger.error(f"获取日线数据失败 {stock_code}: {e}")
            raise
    
    def get_stock_minute(
        self,
        stock_code: str,
        freq: str = "1min",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取股票分钟行情数据
        
        Args:
            stock_code: 股票代码
            freq: 分钟频率，可选 "1min", "5min", "15min", "30min", "60min"
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            分钟行情 DataFrame
        """
        ts_code = normalize_stock_code(stock_code)
        
        try:
            logger.info(f"获取 {stock_code} {freq}分钟数据...")
            
            df = self._retry_request(
                self.pro.stk_mins,
                ts_code=ts_code,
                freq=freq,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
            
        except Exception as e:
            logger.error(f"获取分钟数据失败 {stock_code}: {e}")
            raise
    
    def get_realtime_quote(self, stock_code: str) -> Dict:
        """
        获取实时行情
        
        注意：Tushare 的实时行情接口需要较高积分权限
        
        Args:
            stock_code: 股票代码
            
        Returns:
            实时行情字典
        """
        ts_code = normalize_stock_code(stock_code)
        
        try:
            df = self._retry_request(
                self.pro.realtime_quote,
                ts_code=ts_code
            )
            
            if df.empty:
                return {}
            
            return df.iloc[0].to_dict()
            
        except Exception as e:
            logger.error(f"获取实时行情失败 {stock_code}: {e}")
            return {}
    
    # ============================================================
    # 指数数据
    # ============================================================
    
    def get_index_list(self, market: str = "SSE") -> pd.DataFrame:
        """
        获取指数列表
        
        Args:
            market: 市场，"SSE" 上交所，"SZSE" 深交所
            
        Returns:
            指数列表 DataFrame
        """
        cache_key = f"index_list_{market}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info(f"获取 {market} 指数列表...")
            
            df = self._retry_request(
                self.pro.index_basic,
                market=market
            )
            
            self.cache.set(cache_key, df, expire_hours=24)
            
            return df
            
        except Exception as e:
            logger.error(f"获取指数列表失败: {e}")
            raise
    
    def get_index_daily(
        self,
        index_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取指数日线数据
        
        Args:
            index_code: 指数代码，如 "000001.SH"（上证指数）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            指数日线 DataFrame
        """
        ts_code = normalize_stock_code(index_code)
        
        if start_date:
            start_date = start_date.replace('-', '')
        if end_date:
            end_date = end_date.replace('-', '')
        
        cache_key = f"index_daily_{ts_code}_{start_date or 'start'}_{end_date or 'end'}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info(f"获取指数 {index_code} 日线数据...")
            
            df = self._retry_request(
                self.pro.index_daily,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            # 标准化列名
            column_mapping = {
                'trade_date': 'date',
                'vol': 'volume'
            }
            df = df.rename(columns=column_mapping)
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            self.cache.set(cache_key, df)
            
            return df
            
        except Exception as e:
            logger.error(f"获取指数数据失败 {index_code}: {e}")
            raise
    
    # ============================================================
    # 资金流向数据
    # ============================================================
    
    def get_money_flow(self, stock_code: str) -> pd.DataFrame:
        """
        获取个股资金流向
        
        Args:
            stock_code: 股票代码
            
        Returns:
            资金流向 DataFrame
        """
        ts_code = normalize_stock_code(stock_code)
        
        try:
            logger.info(f"获取 {stock_code} 资金流向...")
            
            df = self._retry_request(
                self.pro.moneyflow,
                ts_code=ts_code
            )
            
            return df
            
        except Exception as e:
            logger.error(f"获取资金流向失败 {stock_code}: {e}")
            raise
    
    # ============================================================
    # 财务数据
    # ============================================================
    
    def get_income_statement(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取利润表
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            利润表 DataFrame
        """
        ts_code = normalize_stock_code(stock_code)
        
        try:
            logger.info(f"获取 {stock_code} 利润表...")
            
            df = self._retry_request(
                self.pro.income,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
            
        except Exception as e:
            logger.error(f"获取利润表失败 {stock_code}: {e}")
            raise
    
    def get_balance_sheet(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取资产负债表
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            资产负债表 DataFrame
        """
        ts_code = normalize_stock_code(stock_code)
        
        try:
            logger.info(f"获取 {stock_code} 资产负债表...")
            
            df = self._retry_request(
                self.pro.balancesheet,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
            
        except Exception as e:
            logger.error(f"获取资产负债表失败 {stock_code}: {e}")
            raise
    
    def get_cash_flow(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取现金流量表
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            现金流量表 DataFrame
        """
        ts_code = normalize_stock_code(stock_code)
        
        try:
            logger.info(f"获取 {stock_code} 现金流量表...")
            
            df = self._retry_request(
                self.pro.cashflow,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            return df
            
        except Exception as e:
            logger.error(f"获取现金流量表失败 {stock_code}: {e}")
            raise
    
    def get_financial_indicator(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取财务指标数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            财务指标 DataFrame
        """
        ts_code = normalize_stock_code(stock_code)
        
        cache_key = f"financial_{ts_code}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info(f"获取 {stock_code} 财务指标...")
            
            df = self._retry_request(
                self.pro.fina_indicator,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
            
            self.cache.set(cache_key, df, expire_hours=24 * 7)
            
            return df
            
        except Exception as e:
            logger.error(f"获取财务指标失败 {stock_code}: {e}")
            raise
    
    # ============================================================
    # 交易日历
    # ============================================================
    
    def get_trading_calendar(
        self,
        exchange: str = "SSE",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取交易日历
        
        Args:
            exchange: 交易所代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易日历 DataFrame
        """
        cache_key = f"trading_calendar_{exchange}_{start_date}_{end_date}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info("获取交易日历...")
            
            df = self._retry_request(
                self.pro.trade_cal,
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )
            
            # 筛选交易日
            df = df[df['is_open'] == 1]
            
            df['trade_date'] = pd.to_datetime(df['cal_date'])
            
            self.cache.set(cache_key, df, expire_hours=24 * 30)
            
            return df
            
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            raise
    
    def is_trading_day(
        self,
        check_date: Union[str, date],
        exchange: str = "SSE"
    ) -> bool:
        """
        判断是否为交易日
        
        Args:
            check_date: 要检查的日期
            exchange: 交易所代码
            
        Returns:
            是否为交易日
        """
        if isinstance(check_date, str):
            check_date_str = check_date.replace('-', '')
        else:
            check_date_str = check_date.strftime('%Y%m%d')
        
        try:
            calendar = self.get_trading_calendar(exchange)
            trading_dates = set(calendar['cal_date'].astype(str))
            
            return check_date_str in trading_dates
            
        except Exception:
            return check_date.weekday() < 5


if __name__ == "__main__":
    # 测试 Tushare 数据获取器
    print("=" * 60)
    print("测试 Tushare 数据获取器")
    print("=" * 60)
    
    print("\n注意：Tushare 需要 token 才能使用")
    print("请访问 https://tushare.pro 注册获取 token")
    print("然后设置环境变量 TUSHARE_TOKEN 或在初始化时传入 token")
    
    # 示例代码（需要 token）
    # fetcher = TushareFetcher(token="your_token")
    # df = fetcher.get_stock_list()
    # print(df.head())