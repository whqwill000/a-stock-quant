"""
AKShare 数据获取器

使用 AKShare 库获取 A 股市场数据
AKShare 是一个免费开源的金融数据接口，数据来源丰富，无需注册

主要功能：
- 获取股票历史行情数据
- 获取股票列表
- 获取指数数据
- 获取财务数据
- 获取资金流向数据

使用方法:
    from core.data_fetch.akshare_fetcher import AKShareFetcher
    
    fetcher = AKShareFetcher()
    df = fetcher.get_stock_daily("000001", start_date="2023-01-01")
"""

import time
from datetime import datetime, date
from typing import Optional, List, Dict, Union
import pandas as pd
import numpy as np

# 导入 AKShare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

# 导入项目模块
from core.utils.logger import get_logger
from core.utils.helpers import normalize_stock_code, validate_stock_code
from core.data_fetch.data_cache import DataFrameCache

# 获取日志记录器
logger = get_logger(__name__)


class AKShareFetcher:
    """
    AKShare 数据获取器
    
    封装 AKShare 的常用接口，提供统一的 A 股数据获取功能
    支持数据缓存，减少重复请求
    
    Attributes:
        cache: 数据缓存实例
        retry_times: 请求失败重试次数
        retry_delay: 重试间隔（秒）
    """
    
    def __init__(
        self,
        cache_enabled: bool = True,
        cache_dir: str = "data/cache",
        cache_expire_hours: int = 24,
        retry_times: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初始化 AKShare 数据获取器
        
        Args:
            cache_enabled: 是否启用缓存
            cache_dir: 缓存目录
            cache_expire_hours: 缓存过期时间（小时）
            retry_times: 请求失败重试次数
            retry_delay: 重试间隔（秒）
        """
        # 检查 AKShare 是否可用
        if not AKSHARE_AVAILABLE:
            raise ImportError(
                "AKShare 未安装，请运行: pip install akshare"
            )
        
        # 初始化缓存
        self.cache = DataFrameCache(
            cache_dir=cache_dir,
            expire_hours=cache_expire_hours,
            enabled=cache_enabled
        )
        
        # 重试配置
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        
        logger.info("AKShare 数据获取器初始化完成")
    
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
    
    def get_stock_list(self, market: str = "A股") -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            market: 市场类型，可选 "A股"、"科创板"、"创业板" 等
            
        Returns:
            股票列表 DataFrame，包含代码、名称等信息
            
        Example:
            >>> fetcher = AKShareFetcher()
            >>> df = fetcher.get_stock_list()
            >>> print(df.head())
        """
        cache_key = f"stock_list_{market}"
        
        # 尝试从缓存获取
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            # 获取 A 股股票列表
            logger.info(f"获取 {market} 股票列表...")
            
            # 使用 AKShare 接口
            df = self._retry_request(ak.stock_info_a_code_name)
            
            # 标准化列名
            df.columns = ['code', 'name']
            
            # 添加交易所信息
            df['exchange'] = df['code'].apply(
                lambda x: 'SH' if x.startswith(('6', '9')) else 'SZ'
            )
            
            # 添加标准化代码
            df['code_normalized'] = df.apply(
                lambda row: f"{row['code']}.{row['exchange']}", axis=1
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
            stock_code: 股票代码
            
        Returns:
            股票基本信息字典
        """
        # 标准化股票代码
        code = stock_code.split('.')[0]
        
        try:
            # 获取股票信息
            df = self._retry_request(
                ak.stock_individual_info_em,
                symbol=code
            )
            
            # 转换为字典
            info = dict(zip(df['item'], df['value']))
            
            return info
            
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
            stock_code: 股票代码，如 "000001" 或 "000001.SZ"
            start_date: 开始日期，格式 "YYYY-MM-DD" 或 "YYYYMMDD"
            end_date: 结束日期，格式同上
            adjust: 复权类型
                - "qfq": 前复权（默认）
                - "hfq": 后复权
                - "": 不复权
                
        Returns:
            日线行情 DataFrame，包含开高低收量等数据
            
        Example:
            >>> fetcher = AKShareFetcher()
            >>> df = fetcher.get_stock_daily("000001", start_date="2023-01-01")
        """
        # 标准化股票代码
        code = stock_code.split('.')[0]
        
        # 处理日期
        if start_date:
            start_date = start_date.replace('-', '')
        if end_date:
            end_date = end_date.replace('-', '')
        
        # 构建缓存键
        cache_key = f"daily_{code}_{start_date or 'start'}_{end_date or 'end'}_{adjust}"
        
        # 尝试从缓存获取
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"从缓存获取日线数据: {stock_code}")
            return cached
        
        try:
            logger.info(f"获取 {stock_code} 日线数据...")
            
            # 使用 AKShare 接口
            df = self._retry_request(
                ak.stock_zh_a_hist,
                symbol=code,
                period="daily",
                start_date=start_date or "19900101",
                end_date=end_date or datetime.now().strftime("%Y%m%d"),
                adjust=adjust
            )
            
            # 标准化列名
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            }
            df = df.rename(columns=column_mapping)
            
            # 添加股票代码列
            df['stock_code'] = code
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            
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
        period: str = "1",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取股票分钟行情数据
        
        Args:
            stock_code: 股票代码
            period: 分钟周期，可选 "1", "5", "15", "30", "60"
            adjust: 复权类型
            
        Returns:
            分钟行情 DataFrame
        """
        code = stock_code.split('.')[0]
        
        try:
            logger.info(f"获取 {stock_code} {period}分钟数据...")
            
            # 使用 AKShare 接口
            df = self._retry_request(
                ak.stock_zh_a_hist_min_em,
                symbol=code,
                period=period,
                adjust=adjust
            )
            
            # 标准化列名
            column_mapping = {
                '时间': 'datetime',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount'
            }
            df = df.rename(columns=column_mapping)
            
            df['stock_code'] = code
            df['datetime'] = pd.to_datetime(df['datetime'])
            
            return df
            
        except Exception as e:
            logger.error(f"获取分钟数据失败 {stock_code}: {e}")
            raise
    
    def get_realtime_quote(self, stock_code: str) -> Dict:
        """
        获取实时行情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            实时行情字典
        """
        code = stock_code.split('.')[0]
        
        try:
            # 获取实时行情
            df = self._retry_request(
                ak.stock_zh_a_spot_em
            )
            
            # 筛选指定股票
            row = df[df['代码'] == code]
            
            if row.empty:
                logger.warning(f"未找到股票 {stock_code}")
                return {}
            
            # 转换为字典
            quote = row.iloc[0].to_dict()
            
            return quote
            
        except Exception as e:
            logger.error(f"获取实时行情失败 {stock_code}: {e}")
            return {}
    
    # ============================================================
    # 指数数据
    # ============================================================
    
    def get_index_list(self) -> pd.DataFrame:
        """
        获取指数列表
        
        Returns:
            指数列表 DataFrame
        """
        cache_key = "index_list"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info("获取指数列表...")
            
            # 获取上证指数列表
            sh_df = self._retry_request(ak.index_stock_info_sh)
            sh_df['exchange'] = 'SH'
            
            # 获取深证指数列表
            sz_df = self._retry_request(ak.index_stock_info_sz)
            sz_df['exchange'] = 'SZ'
            
            # 合并
            df = pd.concat([sh_df, sz_df], ignore_index=True)
            
            # 缓存
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
            index_code: 指数代码，如 "000001"（上证指数）
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            指数日线 DataFrame
        """
        code = index_code.split('.')[0]
        
        if start_date:
            start_date = start_date.replace('-', '')
        if end_date:
            end_date = end_date.replace('-', '')
        
        cache_key = f"index_daily_{code}_{start_date or 'start'}_{end_date or 'end'}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info(f"获取指数 {index_code} 日线数据...")
            
            # 判断交易所
            if code.startswith(('000', '880')):
                # 上证指数
                df = self._retry_request(
                    ak.index_zh_a_hist,
                    symbol=code,
                    period="daily",
                    start_date=start_date or "19900101",
                    end_date=end_date or datetime.now().strftime("%Y%m%d")
                )
            else:
                # 深证指数
                df = self._retry_request(
                    ak.index_zh_a_hist,
                    symbol=code,
                    period="daily",
                    start_date=start_date or "19900101",
                    end_date=end_date or datetime.now().strftime("%Y%m%d")
                )
            
            # 标准化列名
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount'
            }
            df = df.rename(columns=column_mapping)
            
            df['index_code'] = code
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
    
    def get_north_flow(self, days: int = 30) -> pd.DataFrame:
        """
        获取北向资金流向数据
        
        Args:
            days: 获取最近多少天的数据
            
        Returns:
            北向资金流向 DataFrame
        """
        cache_key = f"north_flow_{days}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info(f"获取北向资金数据（最近 {days} 天）...")
            
            # 获取北向资金数据
            df = self._retry_request(ak.stock_hsgt_north_net_flow_in_em)
            
            # 取最近 N 天
            df = df.tail(days)
            
            # 标准化列名
            column_mapping = {
                '日期': 'date',
                '当日净流入': 'net_inflow',
                '当日净流入占比': 'net_inflow_ratio'
            }
            df = df.rename(columns=column_mapping)
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            self.cache.set(cache_key, df, expire_hours=6)
            
            return df
            
        except Exception as e:
            logger.error(f"获取北向资金数据失败: {e}")
            raise
    
    def get_stock_fund_flow(self, stock_code: str) -> pd.DataFrame:
        """
        获取个股资金流向
        
        Args:
            stock_code: 股票代码
            
        Returns:
            资金流向 DataFrame
        """
        code = stock_code.split('.')[0]
        
        try:
            logger.info(f"获取 {stock_code} 资金流向...")
            
            df = self._retry_request(
                ak.stock_individual_fund_flow,
                symbol=code
            )
            
            return df
            
        except Exception as e:
            logger.error(f"获取资金流向失败 {stock_code}: {e}")
            raise
    
    # ============================================================
    # 财务数据
    # ============================================================
    
    def get_financial_indicator(self, stock_code: str) -> pd.DataFrame:
        """
        获取财务指标数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            财务指标 DataFrame
        """
        code = stock_code.split('.')[0]
        
        cache_key = f"financial_{code}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info(f"获取 {stock_code} 财务指标...")
            
            df = self._retry_request(
                ak.stock_financial_analysis_indicator,
                symbol=code
            )
            
            self.cache.set(cache_key, df, expire_hours=24 * 7)  # 财务数据缓存一周
            
            return df
            
        except Exception as e:
            logger.error(f"获取财务指标失败 {stock_code}: {e}")
            raise
    
    # ============================================================
    # 交易日历
    # ============================================================
    
    def get_trading_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取交易日历
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易日历 DataFrame
        """
        cache_key = f"trading_calendar_{start_date}_{end_date}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            logger.info("获取交易日历...")
            
            # 获取交易日历
            df = self._retry_request(ak.tool_trade_date_hist_sina)
            
            df.columns = ['trade_date']
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            
            # 筛选日期范围
            if start_date:
                start = pd.to_datetime(start_date)
                df = df[df['trade_date'] >= start]
            if end_date:
                end = pd.to_datetime(end_date)
                df = df[df['trade_date'] <= end]
            
            self.cache.set(cache_key, df, expire_hours=24 * 30)  # 缓存一个月
            
            return df
            
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            raise
    
    def is_trading_day(self, check_date: Union[str, date]) -> bool:
        """
        判断是否为交易日
        
        Args:
            check_date: 要检查的日期
            
        Returns:
            是否为交易日
        """
        if isinstance(check_date, str):
            check_date = pd.to_datetime(check_date).date()
        
        try:
            calendar = self.get_trading_calendar()
            trading_dates = set(calendar['trade_date'].dt.date)
            
            return check_date in trading_dates
            
        except Exception:
            # 如果获取失败，简单判断是否为周末
            return check_date.weekday() < 5


if __name__ == "__main__":
    # 测试 AKShare 数据获取器
    print("=" * 60)
    print("测试 AKShare 数据获取器")
    print("=" * 60)
    
    try:
        # 创建获取器实例
        fetcher = AKShareFetcher(cache_enabled=True)
        
        # 测试获取股票列表
        print("\n【测试获取股票列表】")
        stock_list = fetcher.get_stock_list()
        print(f"获取到 {len(stock_list)} 只股票")
        print(stock_list.head())
        
        # 测试获取日线数据
        print("\n【测试获取日线数据】")
        daily = fetcher.get_stock_daily(
            "000001",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        print(f"获取到 {len(daily)} 条日线数据")
        print(daily.head())
        
        # 测试交易日历
        print("\n【测试交易日历】")
        calendar = fetcher.get_trading_calendar("2024-01-01", "2024-01-31")
        print(f"2024年1月共有 {len(calendar)} 个交易日")
        
        print("\n" + "=" * 60)
        print("AKShare 数据获取器测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试失败: {e}")