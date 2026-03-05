"""
数据下载脚本

从 AKShare 下载 A 股历史数据并保存到本地

运行方式:
    python scripts/download_data.py --start 2023-01-01 --end 2023-12-31
"""

import argparse
import sys
import os
from datetime import datetime
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_fetch.akshare_fetcher import AKShareFetcher
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


def download_stock_list(fetcher: AKShareFetcher, output_dir: str):
    """
    下载股票列表
    
    Args:
        fetcher: 数据获取器
        output_dir: 输出目录
    """
    logger.info("下载股票列表...")
    
    try:
        df = fetcher.get_stock_list()
        
        # 保存到文件
        output_path = os.path.join(output_dir, "stock_list.csv")
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"股票列表已保存到: {output_path}")
        logger.info(f"共 {len(df)} 只股票")
        
        return df
        
    except Exception as e:
        logger.error(f"下载股票列表失败: {e}")
        return None


def download_stock_daily(
    fetcher: AKShareFetcher,
    stock_codes: list,
    start_date: str,
    end_date: str,
    output_dir: str
):
    """
    下载股票日线数据
    
    Args:
        fetcher: 数据获取器
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        output_dir: 输出目录
    """
    logger.info(f"下载股票日线数据: {start_date} ~ {end_date}")
    
    # 创建日线数据目录
    daily_dir = os.path.join(output_dir, "daily")
    os.makedirs(daily_dir, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    
    total = len(stock_codes)
    
    for i, stock_code in enumerate(stock_codes):
        try:
            # 显示进度
            if (i + 1) % 10 == 0 or i == total - 1:
                logger.info(f"进度: {i+1}/{total} ({(i+1)/total*100:.1f}%)")
            
            # 下载数据
            df = fetcher.get_stock_daily(
                stock_code,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df is not None and not df.empty:
                # 保存到文件
                output_path = os.path.join(daily_dir, f"{stock_code}.csv")
                df.to_csv(output_path, index=False)
                success_count += 1
            else:
                fail_count += 1
                
        except Exception as e:
            logger.warning(f"下载 {stock_code} 失败: {e}")
            fail_count += 1
    
    logger.info(f"日线数据下载完成: 成功 {success_count}, 失败 {fail_count}")


def download_index_data(
    fetcher: AKShareFetcher,
    index_codes: list,
    start_date: str,
    end_date: str,
    output_dir: str
):
    """
    下载指数数据
    
    Args:
        fetcher: 数据获取器
        index_codes: 指数代码列表
        start_date: 开始日期
        end_date: 结束日期
        output_dir: 输出目录
    """
    logger.info("下载指数数据...")
    
    # 创建指数数据目录
    index_dir = os.path.join(output_dir, "index")
    os.makedirs(index_dir, exist_ok=True)
    
    for index_code in index_codes:
        try:
            df = fetcher.get_index_daily(
                index_code,
                start_date=start_date,
                end_date=end_date
            )
            
            if df is not None and not df.empty:
                output_path = os.path.join(index_dir, f"{index_code}.csv")
                df.to_csv(output_path, index=False)
                logger.info(f"指数 {index_code} 数据已保存")
                
        except Exception as e:
            logger.warning(f"下载指数 {index_code} 失败: {e}")


def download_trading_calendar(fetcher: AKShareFetcher, output_dir: str):
    """
    下载交易日历
    
    Args:
        fetcher: 数据获取器
        output_dir: 输出目录
    """
    logger.info("下载交易日历...")
    
    try:
        df = fetcher.get_trading_calendar()
        
        output_path = os.path.join(output_dir, "trading_calendar.csv")
        df.to_csv(output_path, index=False)
        
        logger.info(f"交易日历已保存到: {output_path}")
        
    except Exception as e:
        logger.error(f"下载交易日历失败: {e}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="下载A股历史数据")
    parser.add_argument("--start", type=str, default="2020-01-01", help="开始日期")
    parser.add_argument("--end", type=str, default="2023-12-31", help="结束日期")
    parser.add_argument("--output", type=str, default="data", help="输出目录")
    parser.add_argument("--stocks", type=int, default=100, help="下载股票数量")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("A股数据下载脚本")
    print("=" * 60)
    print(f"开始日期: {args.start}")
    print(f"结束日期: {args.end}")
    print(f"输出目录: {args.output}")
    print(f"股票数量: {args.stocks}")
    print("=" * 60)
    
    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)
    
    # 创建数据获取器
    try:
        fetcher = AKShareFetcher(
            cache_enabled=True,
            cache_dir=os.path.join(args.output, "cache")
        )
    except ImportError as e:
        print(f"错误: {e}")
        print("请安装 akshare: pip install akshare")
        return
    
    # 下载股票列表
    stock_list = download_stock_list(fetcher, args.output)
    
    if stock_list is not None:
        # 选择要下载的股票
        stock_codes = stock_list['code'].head(args.stocks).tolist()
        
        # 下载日线数据
        download_stock_daily(
            fetcher,
            stock_codes,
            args.start,
            args.end,
            args.output
        )
    
    # 下载主要指数
    index_codes = [
        "000001",  # 上证指数
        "000300",  # 沪深300
        "000016",  # 上证50
        "000905",  # 中证500
        "000852",  # 中证1000
        "399001",  # 深证成指
        "399006",  # 创业板指
    ]
    
    download_index_data(fetcher, index_codes, args.start, args.end, args.output)
    
    # 下载交易日历
    download_trading_calendar(fetcher, args.output)
    
    print("\n" + "=" * 60)
    print("数据下载完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()