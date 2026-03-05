#!/usr/bin/env python3
"""
回测脚本

用法:
    python backtest.py
    python backtest.py --start 2020-01-01 --end 2023-12-31
    python backtest.py --config config.yaml
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import yaml

from core.data_fetch.akshare_fetcher import AKShareFetcher
from core.backtest.engine import BacktestEngine
from strategy import DoubleMAStrategy


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_data(
    stock_codes: list,
    start_date: str,
    end_date: str,
    adjust: str = "qfq"
) -> pd.DataFrame:
    """
    获取回测数据
    
    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        adjust: 复权类型 (qfq/hfq/none)
        
    Returns:
        合并后的数据 DataFrame
    """
    fetcher = AKShareFetcher()
    all_data = []
    
    for code in stock_codes:
        try:
            df = fetcher.get_stock_data(
                stock_code=code,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            if df is not None and not df.empty:
                all_data.append(df)
        except Exception as e:
            print(f"获取 {code} 数据失败：{e}")
            continue
    
    if not all_data:
        raise ValueError("未获取到任何数据")
    
    return pd.concat(all_data, ignore_index=True)


def run_backtest(config: dict) -> dict:
    """
    运行回测
    
    Args:
        config: 配置字典
        
    Returns:
        回测结果
    """
    print("=" * 60)
    print("A 股量化策略回测系统")
    print("=" * 60)
    
    # 1. 提取配置
    backtest_cfg = config.get("backtest", {})
    trading_cfg = config.get("trading", {})
    strategy_cfg = config.get("strategy", {})
    data_cfg = config.get("data", {})
    
    # 2. 创建策略
    strategy = DoubleMAStrategy(params=strategy_cfg.get("params", {}))
    print(f"策略名称：{strategy.name}")
    
    # 3. 获取数据
    print(f"\n获取数据...")
    print(f"时间范围：{backtest_cfg.get('start_date')} 至 {backtest_cfg.get('end_date')}")
    
    # 示例股票池（实际使用应从配置读取）
    stock_pool = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH"]
    
    data = fetch_data(
        stock_codes=stock_pool,
        start_date=backtest_cfg.get("start_date"),
        end_date=backtest_cfg.get("end_date"),
        adjust=data_cfg.get("adjust", "qfq")
    )
    print(f"获取到 {len(data)} 条数据")
    
    # 4. 创建回测引擎
    engine = BacktestEngine(
        initial_cash=backtest_cfg.get("initial_cash", 1000000),
        commission=backtest_cfg.get("commission", 0.00025),
        stamp_tax=backtest_cfg.get("stamp_tax", 0.0005),
        slippage=backtest_cfg.get("slippage", 0.001)
    )
    
    # 5. 运行回测
    print(f"\n开始回测...")
    result = engine.run(
        data=data,
        strategy=strategy,
        position_size=trading_cfg.get("position_size", 0.1)
    )
    
    # 6. 输出结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    
    print(f"\n【收益指标】")
    print(f"  初始资金：  {result['initial_cash']:,.2f}")
    print(f"  最终资产：  {result['final_asset']:,.2f}")
    print(f"  总收益率：  {result['total_return']:.2%}")
    print(f"  年化收益：  {result['annual_return']:.2%}")
    print(f"  基准收益：  {result['benchmark_return']:.2%}")
    print(f"  超额收益：  {result['alpha']:.2%}")
    
    print(f"\n【风险指标】")
    print(f"  波动率：    {result['volatility']:.2%}")
    print(f"  最大回撤：  {result['max_drawdown']:.2%}")
    print(f"  夏普比率：  {result['sharpe_ratio']:.2f}")
    print(f"  索提诺比率：{result['sortino_ratio']:.2f}")
    
    print(f"\n【交易统计】")
    print(f"  交易次数：  {result['total_trades']}")
    print(f"  胜率：      {result['win_rate']:.2%}")
    print(f"  盈亏比：    {result['profit_loss_ratio']:.2f}")
    print(f"  平均持仓：  {result['avg_holding_days']} 天")
    
    # 7. 保存结果
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    # 保存交易记录
    if "trades" in result:
        trades_df = pd.DataFrame(result["trades"])
        trades_df.to_csv(results_dir / "trades.csv", index=False)
        print(f"\n交易记录已保存：{results_dir / 'trades.csv'}")
    
    # 保存权益曲线
    if "equity_curve" in result:
        equity_df = pd.DataFrame(result["equity_curve"])
        equity_df.to_csv(results_dir / "equity_curve.csv", index=False)
        print(f"权益曲线已保存：{results_dir / 'equity_curve.csv'}")
    
    # 生成图表
    try:
        from core.analysis.performance import plot_performance
        plot_performance(result, save_path=results_dir / "backtest_report.png")
        print(f"回测图表已保存：{results_dir / 'backtest_report.png'}")
    except ImportError:
        print("未安装 matplotlib，跳过图表生成")
    
    print("\n" + "=" * 60)
    print("回测完成!")
    print("=" * 60)
    
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="A 股量化策略回测")
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--start", 
        type=str, 
        default=None,
        help="开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end", 
        type=str, 
        default=None,
        help="结束日期 (YYYY-MM-DD)"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 覆盖日期配置
    if args.start:
        config["backtest"]["start_date"] = args.start
    if args.end:
        config["backtest"]["end_date"] = args.end
    
    # 运行回测
    run_backtest(config)


if __name__ == "__main__":
    main()
