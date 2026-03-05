"""
回测引擎模块

提供完整的策略回测功能，包括数据加载、策略执行、交易模拟、绩效分析

使用方法:
    from core.backtest.engine import BacktestEngine
    
    engine = BacktestEngine(initial_cash=1000000)
    result = engine.run(strategy, data)
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Callable, Any
import pandas as pd
import numpy as np
from pathlib import Path
import json

# 导入项目模块
from core.utils.logger import get_logger
from core.utils.config import Config
from core.simulator.account import Account
from core.simulator.order import Order, OrderManager, Trade
from core.simulator.matching import MatchingEngine, MarketData
from core.simulator.risk_control import RiskControl, RiskConfig
from core.backtest.metrics import MetricsCalculator, PerformanceMetrics

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class BacktestConfig:
    """
    回测配置数据类
    
    存储回测的各项参数配置
    
    Attributes:
        initial_cash: 初始资金
        start_date: 开始日期
        end_date: 结束日期
        commission_rate: 佣金费率
        stamp_tax_rate: 印花税率
        slippage: 滑点
        benchmark: 基准指数
    """
    
    initial_cash: float = 1000000.0
    start_date: str = "2020-01-01"
    end_date: str = "2023-12-31"
    commission_rate: float = 0.00025
    stamp_tax_rate: float = 0.0005
    slippage: float = 0.0
    benchmark: str = "000300.SH"  # 沪深300


@dataclass
class BacktestResult:
    """
    回测结果数据类
    
    存储回测的完整结果
    
    Attributes:
        config: 回测配置
        metrics: 绩效指标
        equity_curve: 权益曲线
        benchmark_curve: 基准曲线
        trades: 交易记录
        positions: 持仓记录
        daily_stats: 每日统计
    """
    
    config: BacktestConfig
    metrics: PerformanceMetrics
    equity_curve: pd.Series
    benchmark_curve: Optional[pd.Series] = None
    trades: pd.DataFrame = field(default_factory=pd.DataFrame)
    positions: pd.DataFrame = field(default_factory=pd.DataFrame)
    daily_stats: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    def summary(self) -> str:
        """
        生成回测结果摘要
        
        Returns:
            摘要文本
        """
        lines = [
            "=" * 60,
            "回测结果摘要",
            "=" * 60,
            "",
            "【回测配置】",
            f"  初始资金: {self.config.initial_cash:,.2f} 元",
            f"  回测区间: {self.config.start_date} ~ {self.config.end_date}",
            f"  基准指数: {self.config.benchmark}",
            "",
            "【收益指标】",
            f"  总收益率: {self.metrics.total_return*100:.2f}%",
            f"  年化收益率: {self.metrics.annual_return*100:.2f}%",
            f"  基准收益率: {self.metrics.benchmark_return*100:.2f}%",
            f"  超额收益: {self.metrics.excess_return*100:.2f}%",
            "",
            "【风险指标】",
            f"  年化波动率: {self.metrics.volatility*100:.2f}%",
            f"  最大回撤: {self.metrics.max_drawdown*100:.2f}%",
            f"  最大回撤持续期: {self.metrics.max_drawdown_duration} 天",
            "",
            "【风险调整收益】",
            f"  夏普比率: {self.metrics.sharpe_ratio:.2f}",
            f"  索提诺比率: {self.metrics.sortino_ratio:.2f}",
            f"  卡玛比率: {self.metrics.calmar_ratio:.2f}",
            "",
            "【交易统计】",
            f"  总交易次数: {self.metrics.total_trades}",
            f"  胜率: {self.metrics.win_rate*100:.2f}%",
            f"  盈亏比: {self.metrics.profit_loss_ratio:.2f}",
            "",
            "=" * 60
        ]
        
        return "\n".join(lines)
    
    def save(self, output_dir: str) -> None:
        """
        保存回测结果
        
        Args:
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存权益曲线
        if not self.equity_curve.empty:
            self.equity_curve.to_csv(output_path / "equity_curve.csv")
        
        # 保存基准曲线
        if self.benchmark_curve is not None and not self.benchmark_curve.empty:
            self.benchmark_curve.to_csv(output_path / "benchmark_curve.csv")
        
        # 保存交易记录
        if not self.trades.empty:
            self.trades.to_csv(output_path / "trades.csv", index=False)
        
        # 保存持仓记录
        if not self.positions.empty:
            self.positions.to_csv(output_path / "positions.csv", index=False)
        
        # 保存绩效指标
        metrics_dict = self.metrics.to_dict()
        with open(output_path / "metrics.json", 'w', encoding='utf-8') as f:
            json.dump(metrics_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"回测结果已保存到: {output_path}")


class BacktestEngine:
    """
    回测引擎类
    
    提供完整的策略回测功能
    
    回测流程：
    1. 初始化账户和风控
    2. 加载历史数据
    3. 遍历每个交易日
    4. 执行策略逻辑，生成交易信号
    5. 撮合订单，更新账户
    6. 记录每日资产和持仓
    7. 计算绩效指标
    
    Attributes:
        config: 回测配置
        account: 交易账户
        order_manager: 订单管理器
        matching_engine: 撮合引擎
        risk_control: 风控模块
        metrics_calculator: 绩效计算器
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置，如果为 None 则使用默认配置
        """
        self.config = config or BacktestConfig()
        
        # 初始化各组件
        self.account = Account(initial_cash=self.config.initial_cash)
        self.order_manager = OrderManager()
        self.matching_engine = MatchingEngine(
            commission_rate=self.config.commission_rate,
            stamp_tax_rate=self.config.stamp_tax_rate
        )
        self.risk_control = RiskControl()
        self.metrics_calculator = MetricsCalculator()
        
        # 数据存储
        self.data: Dict[str, pd.DataFrame] = {}
        self.benchmark_data: Optional[pd.DataFrame] = None
        
        # 回测状态
        self.current_date: Optional[date] = None
        self.trading_days: List[date] = []
        
        # 结果记录
        self.equity_curve: List[float] = []
        self.benchmark_curve: List[float] = []
        self.daily_positions: List[dict] = []
        
        logger.info(
            f"回测引擎初始化完成 - "
            f"初始资金: {self.config.initial_cash:,.2f}, "
            f"区间: {self.config.start_date} ~ {self.config.end_date}"
        )
    
    def load_data(
        self,
        stock_data: Dict[str, pd.DataFrame],
        benchmark_data: Optional[pd.DataFrame] = None
    ) -> None:
        """
        加载回测数据
        
        Args:
            stock_data: 股票数据字典 {股票代码: DataFrame}
            benchmark_data: 基准数据 DataFrame
        """
        self.data = stock_data
        self.benchmark_data = benchmark_data
        
        # 获取交易日列表
        if stock_data:
            first_stock = list(stock_data.values())[0]
            self.trading_days = pd.to_datetime(first_stock['date']).dt.date.tolist()
        
        logger.info(
            f"数据加载完成 - "
            f"股票数量: {len(stock_data)}, "
            f"交易日数: {len(self.trading_days)}"
        )
    
    def run(
        self,
        strategy: Callable,
        **strategy_params
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy: 策略函数，接收 (engine, date, data) 参数
            **strategy_params: 策略参数
            
        Returns:
            回测结果对象
            
        Example:
            >>> def my_strategy(engine, date, data):
            ...     # 策略逻辑
            ...     engine.buy("000001.SZ", 1000, 10.5)
            >>> 
            >>> result = engine.run(my_strategy)
        """
        logger.info("开始回测...")
        
        # 重置状态
        self._reset()
        
        # 遍历每个交易日
        total_days = len(self.trading_days)
        
        for i, trade_date in enumerate(self.trading_days):
            self.current_date = trade_date
            
            # 更新账户日期（处理 T+1）
            self.account.update_t_plus1(trade_date)
            
            # 获取当日数据
            daily_data = self._get_daily_data(trade_date)
            
            if not daily_data:
                continue
            
            # 更新持仓价格
            self._update_position_prices(daily_data)
            
            # 执行策略
            try:
                strategy(self, trade_date, daily_data, **strategy_params)
            except Exception as e:
                logger.error(f"策略执行错误 {trade_date}: {e}")
                continue
            
            # 撮合订单
            self._match_orders(daily_data)
            
            # 记录每日状态
            self._record_daily_state(trade_date, daily_data)
            
            # 进度显示
            if (i + 1) % 50 == 0 or i == total_days - 1:
                logger.info(f"回测进度: {i+1}/{total_days} ({(i+1)/total_days*100:.1f}%)")
        
        # 生成结果
        result = self._generate_result()
        
        logger.info("回测完成！")
        
        return result
    
    def _reset(self) -> None:
        """重置回测状态"""
        self.account.reset()
        self.order_manager.reset()
        self.risk_control.reset_daily()
        
        self.equity_curve = []
        self.benchmark_curve = []
        self.daily_positions = []
    
    def _get_daily_data(self, trade_date: date) -> Dict[str, pd.Series]:
        """
        获取指定日期的所有股票数据
        
        Args:
            trade_date: 交易日期
            
        Returns:
            当日数据字典 {股票代码: Series}
        """
        daily_data = {}
        
        for stock_code, df in self.data.items():
            # 筛选当日数据
            mask = pd.to_datetime(df['date']).dt.date == trade_date
            
            if mask.any():
                daily_data[stock_code] = df[mask].iloc[0]
        
        return daily_data
    
    def _update_position_prices(self, daily_data: Dict[str, pd.Series]) -> None:
        """
        更新持仓价格
        
        Args:
            daily_data: 当日数据
        """
        prices = {}
        
        for stock_code, row in daily_data.items():
            prices[stock_code] = row['close']
        
        self.account.update_all_prices(prices)
    
    def _match_orders(self, daily_data: Dict[str, pd.Series]) -> None:
        """
        撮合订单
        
        Args:
            daily_data: 当日数据
        """
        # 获取活动订单
        active_orders = self.order_manager.get_active_orders()
        
        if not active_orders:
            return
        
        # 遍历订单进行撮合
        for order in active_orders:
            stock_data = daily_data.get(order.stock_code)
            
            if stock_data is None:
                continue
            
            # 创建市场数据对象
            prev_close = stock_data.get('pre_close', stock_data['close'])
            limit_up, limit_down = self.matching_engine.price_limit_rule.calculate_limit_prices(
                order.stock_code, prev_close
            )
            
            market_data = MarketData(
                stock_code=order.stock_code,
                date=pd.Timestamp(self.current_date),
                open=stock_data['open'],
                high=stock_data['high'],
                low=stock_data['low'],
                close=stock_data['close'],
                volume=stock_data.get('volume', 0),
                limit_up=limit_up,
                limit_down=limit_down
            )
            
            # 撮合订单
            trades = self.matching_engine.match(order, market_data, self.account)
            
            # 处理成交
            for trade in trades:
                self._process_trade(trade)
    
    def _process_trade(self, trade: Trade) -> None:
        """
        处理成交
        
        Args:
            trade: 成交记录
        """
        if trade.direction == 'buy':
            # 买入
            self.account.buy(
                stock_code=trade.stock_code,
                volume=trade.volume,
                price=trade.price,
                commission=trade.commission,
                transfer_fee=trade.transfer_fee
            )
        else:
            # 卖出
            self.account.sell(
                stock_code=trade.stock_code,
                volume=trade.volume,
                price=trade.price,
                commission=trade.commission,
                stamp_tax=trade.stamp_tax,
                transfer_fee=trade.transfer_fee
            )
        
        # 添加成交记录
        self.order_manager.add_trade(trade)
        
        # 更新风控统计
        self.risk_control.update_daily_turnover(trade.amount)
    
    def _record_daily_state(
        self,
        trade_date: date,
        daily_data: Dict[str, pd.Series]
    ) -> None:
        """
        记录每日状态
        
        Args:
            trade_date: 交易日期
            daily_data: 当日数据
        """
        # 记录权益
        self.equity_curve.append({
            'date': trade_date,
            'equity': self.account.total_asset,
            'cash': self.account.total_cash,
            'market_value': self.account.total_market_value
        })
        
        # 记录基准
        if self.benchmark_data is not None:
            mask = pd.to_datetime(self.benchmark_data['date']).dt.date == trade_date
            if mask.any():
                benchmark_value = self.benchmark_data[mask].iloc[0]['close']
                self.benchmark_curve.append({
                    'date': trade_date,
                    'value': benchmark_value
                })
        
        # 记录持仓
        positions_df = self.account.get_positions_df()
        if not positions_df.empty:
            for _, pos in positions_df.iterrows():
                self.daily_positions.append({
                    'date': trade_date,
                    'stock_code': pos['stock_code'],
                    'volume': pos['total_volume'],
                    'avg_cost': pos['avg_cost'],
                    'market_value': pos['market_value'],
                    'profit_loss': pos['profit_loss']
                })
    
    def _generate_result(self) -> BacktestResult:
        """
        生成回测结果
        
        Returns:
            回测结果对象
        """
        # 转换权益曲线
        equity_df = pd.DataFrame(self.equity_curve)
        equity_series = equity_df.set_index('date')['equity'] if not equity_df.empty else pd.Series()
        
        # 转换基准曲线
        benchmark_series = None
        if self.benchmark_curve:
            benchmark_df = pd.DataFrame(self.benchmark_curve)
            # 归一化基准
            if not benchmark_df.empty:
                first_value = benchmark_df['value'].iloc[0]
                benchmark_df['normalized'] = benchmark_df['value'] / first_value * self.config.initial_cash
                benchmark_series = benchmark_df.set_index('date')['normalized']
        
        # 转换交易记录
        trades_df = self.account.get_trade_history_df()
        
        # 转换持仓记录
        positions_df = pd.DataFrame(self.daily_positions) if self.daily_positions else pd.DataFrame()
        
        # 计算绩效指标
        metrics = self.metrics_calculator.calculate(
            equity_series,
            benchmark_series,
            trades_df
        )
        
        return BacktestResult(
            config=self.config,
            metrics=metrics,
            equity_curve=equity_series,
            benchmark_curve=benchmark_series,
            trades=trades_df,
            positions=positions_df
        )
    
    # ============================================================
    # 交易接口（供策略调用）
    # ============================================================
    
    def buy(
        self,
        stock_code: str,
        volume: int,
        price: Optional[float] = None,
        order_type: str = "limit"
    ) -> Optional[Order]:
        """
        买入股票
        
        Args:
            stock_code: 股票代码
            volume: 买入数量
            price: 委托价格（市价单可以为 None）
            order_type: 订单类型 "limit" 或 "market"
            
        Returns:
            订单对象，失败返回 None
        """
        # 获取当前价格
        if price is None:
            daily_data = self._get_daily_data(self.current_date)
            if stock_code not in daily_data:
                logger.warning(f"无法获取 {stock_code} 的价格")
                return None
            price = daily_data[stock_code]['open']
        
        # 创建订单
        order = self.order_manager.create_order(
            stock_code=stock_code,
            direction="buy",
            order_type=order_type,
            price=price,
            volume=volume
        )
        
        # 风控检查
        passed, reason = self.risk_control.check_buy_order(
            order, self.account, price
        )
        
        if not passed:
            logger.warning(f"买入订单被风控拒绝: {reason}")
            self.order_manager.cancel_order(order.order_id)
            return None
        
        # 冻结资金
        amount = price * volume
        commission = self.matching_engine._calculate_commission(amount)
        total_cash = amount + commission
        
        if not self.account.freeze_cash(total_cash):
            logger.warning(f"资金冻结失败")
            self.order_manager.cancel_order(order.order_id)
            return None
        
        # 提交订单
        self.order_manager.submit_order(order.order_id)
        
        return order
    
    def sell(
        self,
        stock_code: str,
        volume: int,
        price: Optional[float] = None,
        order_type: str = "limit"
    ) -> Optional[Order]:
        """
        卖出股票
        
        Args:
            stock_code: 股票代码
            volume: 卖出数量
            price: 委托价格
            order_type: 订单类型
            
        Returns:
            订单对象，失败返回 None
        """
        # 获取当前价格
        if price is None:
            daily_data = self._get_daily_data(self.current_date)
            if stock_code not in daily_data:
                logger.warning(f"无法获取 {stock_code} 的价格")
                return None
            price = daily_data[stock_code]['open']
        
        # 创建订单
        order = self.order_manager.create_order(
            stock_code=stock_code,
            direction="sell",
            order_type=order_type,
            price=price,
            volume=volume
        )
        
        # 风控检查
        passed, reason = self.risk_control.check_sell_order(order, self.account)
        
        if not passed:
            logger.warning(f"卖出订单被风控拒绝: {reason}")
            self.order_manager.cancel_order(order.order_id)
            return None
        
        # 冻结持仓
        if not self.account.freeze_position(stock_code, volume):
            logger.warning(f"持仓冻结失败")
            self.order_manager.cancel_order(order.order_id)
            return None
        
        # 提交订单
        self.order_manager.submit_order(order.order_id)
        
        return order
    
    def get_position(self, stock_code: str) -> int:
        """
        获取可用持仓
        
        Args:
            stock_code: 股票代码
            
        Returns:
            可用持仓数量
        """
        return self.account.get_available_volume(stock_code)
    
    def get_cash(self) -> float:
        """
        获取可用资金
        
        Returns:
            可用资金
        """
        return self.account.available_cash
    
    def get_total_asset(self) -> float:
        """
        获取总资产
        
        Returns:
            总资产
        """
        return self.account.total_asset


if __name__ == "__main__":
    # 测试回测引擎
    print("=" * 60)
    print("测试回测引擎模块")
    print("=" * 60)
    
    # 创建测试数据
    print("\n【创建测试数据】")
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    
    # 模拟股票数据
    np.random.seed(42)
    stock_data = {}
    
    for stock_code in ['000001.SZ', '000002.SZ', '600000.SH']:
        returns = np.random.normal(0.001, 0.02, 100)
        prices = 10 * (1 + returns).cumprod()
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
            'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
            'low': prices * (1 + np.random.uniform(-0.02, 0, 100)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })
        stock_data[stock_code] = df
    
    print(f"创建了 {len(stock_data)} 只股票的数据")
    
    # 创建回测引擎
    config = BacktestConfig(
        initial_cash=1000000,
        start_date="2023-01-01",
        end_date="2023-05-31"
    )
    engine = BacktestEngine(config)
    
    # 加载数据
    engine.load_data(stock_data)
    
    # 定义简单策略
    def simple_strategy(engine, date, data):
        """简单买入持有策略"""
        # 第一天买入
        if date == engine.trading_days[0]:
            for stock_code in data:
                engine.buy(stock_code, 1000)
    
    # 运行回测
    print("\n【运行回测】")
    result = engine.run(simple_strategy)
    
    # 打印结果
    print(result.summary())
    
    print("\n" + "=" * 60)
    print("回测引擎模块测试完成！")
    print("=" * 60)