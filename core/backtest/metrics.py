"""
绩效指标计算模块

计算回测的各种绩效指标，包括收益指标、风险指标、风险调整收益指标等

使用方法:
    from core.backtest.metrics import MetricsCalculator
    
    metrics = MetricsCalculator()
    result = metrics.calculate(returns, benchmark_returns)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# 导入项目模块
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """
    绩效指标数据类
    
    存储计算出的各种绩效指标
    
    Attributes:
        # 收益指标
        total_return: 总收益率
        annual_return: 年化收益率
        benchmark_return: 基准收益率
        excess_return: 超额收益
        
        # 风险指标
        volatility: 年化波动率
        max_drawdown: 最大回撤
        max_drawdown_duration: 最大回撤持续期
        var_95: 95% VaR
        cvar_95: 95% CVaR
        
        # 风险调整收益指标
        sharpe_ratio: 夏普比率
        sortino_ratio: 索提诺比率
        calmar_ratio: 卡玛比率
        information_ratio: 信息比率
        
        # 交易统计
        total_trades: 总交易次数
        win_rate: 胜率
        profit_loss_ratio: 盈亏比
        avg_holding_days: 平均持仓天数
    """
    
    # 收益指标
    total_return: float = 0.0
    annual_return: float = 0.0
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    
    # 风险指标
    volatility: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # 风险调整收益指标
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    
    # 交易统计
    total_trades: int = 0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    avg_holding_days: float = 0.0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            # 收益指标
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'benchmark_return': self.benchmark_return,
            'excess_return': self.excess_return,
            
            # 风险指标
            'volatility': self.volatility,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'var_95': self.var_95,
            'cvar_95': self.cvar_95,
            
            # 风险调整收益指标
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'information_ratio': self.information_ratio,
            
            # 交易统计
            'total_trades': self.total_trades,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'avg_holding_days': self.avg_holding_days
        }


class MetricsCalculator:
    """
    绩效指标计算器
    
    计算策略回测的各种绩效指标
    
    主要功能：
    1. 收益指标计算：总收益、年化收益、超额收益
    2. 风险指标计算：波动率、最大回撤、VaR
    3. 风险调整收益指标：夏普比率、索提诺比率、卡玛比率
    4. 交易统计：胜率、盈亏比、平均持仓
    
    Attributes:
        risk_free_rate: 无风险利率（年化）
        trading_days_per_year: 每年交易日数
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        trading_days_per_year: int = 252
    ):
        """
        初始化绩效指标计算器
        
        Args:
            risk_free_rate: 无风险利率，默认 3%
            trading_days_per_year: 每年交易日数，默认 252
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days_per_year = trading_days_per_year
        
        logger.info(
            f"绩效指标计算器初始化 - "
            f"无风险利率: {risk_free_rate*100:.1f}%, "
            f"年交易日: {trading_days_per_year}"
        )
    
    def calculate(
        self,
        equity_curve: pd.Series,
        benchmark_curve: Optional[pd.Series] = None,
        trades: Optional[pd.DataFrame] = None
    ) -> PerformanceMetrics:
        """
        计算所有绩效指标
        
        Args:
            equity_curve: 权益曲线（每日资产净值）
            benchmark_curve: 基准曲线（可选）
            trades: 交易记录 DataFrame（可选）
            
        Returns:
            绩效指标对象
            
        Example:
            >>> calculator = MetricsCalculator()
            >>> metrics = calculator.calculate(equity_curve, benchmark_curve)
        """
        metrics = PerformanceMetrics()
        
        # 计算收益率序列
        returns = equity_curve.pct_change().dropna()
        
        # 1. 计算收益指标
        metrics.total_return = self._calculate_total_return(equity_curve)
        metrics.annual_return = self._calculate_annual_return(equity_curve)
        
        if benchmark_curve is not None:
            metrics.benchmark_return = self._calculate_total_return(benchmark_curve)
            metrics.excess_return = metrics.total_return - metrics.benchmark_return
        
        # 2. 计算风险指标
        metrics.volatility = self._calculate_volatility(returns)
        metrics.max_drawdown, metrics.max_drawdown_duration = self._calculate_max_drawdown(equity_curve)
        metrics.var_95 = self._calculate_var(returns, 0.95)
        metrics.cvar_95 = self._calculate_cvar(returns, 0.95)
        
        # 3. 计算风险调整收益指标
        metrics.sharpe_ratio = self._calculate_sharpe_ratio(returns)
        metrics.sortino_ratio = self._calculate_sortino_ratio(returns)
        metrics.calmar_ratio = self._calculate_calmar_ratio(
            metrics.annual_return, metrics.max_drawdown
        )
        
        if benchmark_curve is not None:
            benchmark_returns = benchmark_curve.pct_change().dropna()
            metrics.information_ratio = self._calculate_information_ratio(
                returns, benchmark_returns
            )
        
        # 4. 计算交易统计
        if trades is not None and not trades.empty:
            metrics.total_trades = len(trades)
            metrics.win_rate = self._calculate_win_rate(trades)
            metrics.profit_loss_ratio = self._calculate_profit_loss_ratio(trades)
            metrics.avg_holding_days = self._calculate_avg_holding_days(trades)
        
        return metrics
    
    # ============================================================
    # 收益指标计算
    # ============================================================
    
    def _calculate_total_return(self, equity_curve: pd.Series) -> float:
        """
        计算总收益率
        
        Args:
            equity_curve: 权益曲线
            
        Returns:
            总收益率
        """
        if len(equity_curve) < 2:
            return 0.0
        
        return (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    
    def _calculate_annual_return(self, equity_curve: pd.Series) -> float:
        """
        计算年化收益率
        
        Args:
            equity_curve: 权益曲线
            
        Returns:
            年化收益率
        """
        if len(equity_curve) < 2:
            return 0.0
        
        total_return = self._calculate_total_return(equity_curve)
        days = len(equity_curve)
        
        # 年化收益率 = (1 + 总收益率)^(252/天数) - 1
        if days > 0 and total_return > -1:
            return (1 + total_return) ** (self.trading_days_per_year / days) - 1
        
        return 0.0
    
    # ============================================================
    # 风险指标计算
    # ============================================================
    
    def _calculate_volatility(self, returns: pd.Series) -> float:
        """
        计算年化波动率
        
        Args:
            returns: 日收益率序列
            
        Returns:
            年化波动率
        """
        if len(returns) < 2:
            return 0.0
        
        # 年化波动率 = 日波动率 * sqrt(252)
        return returns.std() * np.sqrt(self.trading_days_per_year)
    
    def _calculate_max_drawdown(
        self,
        equity_curve: pd.Series
    ) -> Tuple[float, int]:
        """
        计算最大回撤
        
        Args:
            equity_curve: 权益曲线
            
        Returns:
            (最大回撤, 最大回撤持续期)
        """
        if len(equity_curve) < 2:
            return 0.0, 0
        
        # 计算累计最大值
        cummax = equity_curve.cummax()
        
        # 计算回撤
        drawdown = (equity_curve - cummax) / cummax
        
        # 最大回撤
        max_dd = drawdown.min()
        
        # 计算最大回撤持续期
        # 找到最大回撤的位置
        max_dd_idx = drawdown.idxmin()
        
        # 找到最大回撤开始的位置（之前的最高点）
        peak_idx = equity_curve[:max_dd_idx].idxmax()
        
        # 计算持续期
        duration = len(equity_curve[peak_idx:max_dd_idx])
        
        return abs(max_dd), duration
    
    def _calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        计算 VaR (Value at Risk)
        
        Args:
            returns: 日收益率序列
            confidence: 置信水平
            
        Returns:
            VaR 值
        """
        if len(returns) < 10:
            return 0.0
        
        # 历史模拟法
        return -np.percentile(returns, (1 - confidence) * 100)
    
    def _calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        计算 CVaR (Conditional Value at Risk)
        
        也称为 Expected Shortfall (ES)
        
        Args:
            returns: 日收益率序列
            confidence: 置信水平
            
        Returns:
            CVaR 值
        """
        if len(returns) < 10:
            return 0.0
        
        # 计算 VaR
        var = self._calculate_var(returns, confidence)
        
        # 计算超过 VaR 的平均损失
        return -returns[returns < -var].mean()
    
    # ============================================================
    # 风险调整收益指标计算
    # ============================================================
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """
        计算夏普比率
        
        夏普比率 = (年化收益 - 无风险利率) / 年化波动率
        
        Args:
            returns: 日收益率序列
            
        Returns:
            夏普比率
        """
        if len(returns) < 10:
            return 0.0
        
        # 年化收益
        annual_return = returns.mean() * self.trading_days_per_year
        
        # 年化波动率
        volatility = self._calculate_volatility(returns)
        
        if volatility == 0:
            return 0.0
        
        # 日无风险利率
        daily_rf = self.risk_free_rate / self.trading_days_per_year
        
        # 夏普比率
        excess_return = returns.mean() - daily_rf
        sharpe = excess_return / returns.std() * np.sqrt(self.trading_days_per_year)
        
        return sharpe
    
    def _calculate_sortino_ratio(self, returns: pd.Series) -> float:
        """
        计算索提诺比率
        
        索提诺比率 = (年化收益 - 无风险利率) / 下行波动率
        
        与夏普比率的区别：只考虑下行风险
        
        Args:
            returns: 日收益率序列
            
        Returns:
            索提诺比率
        """
        if len(returns) < 10:
            return 0.0
        
        # 日无风险利率
        daily_rf = self.risk_free_rate / self.trading_days_per_year
        
        # 计算超额收益
        excess_returns = returns - daily_rf
        
        # 计算下行收益（只考虑负收益）
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf')
        
        # 下行波动率
        downside_std = np.sqrt((downside_returns ** 2).mean())
        
        if downside_std == 0:
            return 0.0
        
        # 索提诺比率
        sortino = excess_returns.mean() / downside_std * np.sqrt(self.trading_days_per_year)
        
        return sortino
    
    def _calculate_calmar_ratio(
        self,
        annual_return: float,
        max_drawdown: float
    ) -> float:
        """
        计算卡玛比率
        
        卡玛比率 = 年化收益 / 最大回撤
        
        Args:
            annual_return: 年化收益率
            max_drawdown: 最大回撤
            
        Returns:
            卡玛比率
        """
        if max_drawdown == 0:
            return float('inf') if annual_return > 0 else 0.0
        
        return annual_return / max_drawdown
    
    def _calculate_information_ratio(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """
        计算信息比率
        
        信息比率 = 超额收益 / 跟踪误差
        
        Args:
            returns: 策略收益率
            benchmark_returns: 基准收益率
            
        Returns:
            信息比率
        """
        if len(returns) < 10 or len(benchmark_returns) < 10:
            return 0.0
        
        # 对齐日期
        common_idx = returns.index.intersection(benchmark_returns.index)
        if len(common_idx) < 10:
            return 0.0
        
        returns = returns.loc[common_idx]
        benchmark_returns = benchmark_returns.loc[common_idx]
        
        # 计算超额收益
        excess_returns = returns - benchmark_returns
        
        # 跟踪误差
        tracking_error = excess_returns.std() * np.sqrt(self.trading_days_per_year)
        
        if tracking_error == 0:
            return 0.0
        
        # 信息比率
        ir = excess_returns.mean() / excess_returns.std() * np.sqrt(self.trading_days_per_year)
        
        return ir
    
    # ============================================================
    # 交易统计计算
    # ============================================================
    
    def _calculate_win_rate(self, trades: pd.DataFrame) -> float:
        """
        计算胜率
        
        Args:
            trades: 交易记录 DataFrame
            
        Returns:
            胜率
        """
        if trades.empty:
            return 0.0
        
        # 筛选卖出交易
        sells = trades[trades['type'] == 'sell'] if 'type' in trades.columns else trades
        
        if sells.empty:
            return 0.0
        
        # 计算盈利交易
        if 'realized_pnl' in sells.columns:
            wins = (sells['realized_pnl'] > 0).sum()
        else:
            return 0.0
        
        return wins / len(sells)
    
    def _calculate_profit_loss_ratio(self, trades: pd.DataFrame) -> float:
        """
        计算盈亏比
        
        Args:
            trades: 交易记录 DataFrame
            
        Returns:
            盈亏比
        """
        if trades.empty:
            return 0.0
        
        # 筛选卖出交易
        sells = trades[trades['type'] == 'sell'] if 'type' in trades.columns else trades
        
        if sells.empty or 'realized_pnl' not in sells.columns:
            return 0.0
        
        # 计算平均盈利和平均亏损
        profits = sells[sells['realized_pnl'] > 0]['realized_pnl']
        losses = sells[sells['realized_pnl'] < 0]['realized_pnl'].abs()
        
        if len(losses) == 0:
            return float('inf')
        
        if len(profits) == 0:
            return 0.0
        
        avg_profit = profits.mean()
        avg_loss = losses.mean()
        
        return avg_profit / avg_loss if avg_loss > 0 else 0.0
    
    def _calculate_avg_holding_days(self, trades: pd.DataFrame) -> float:
        """
        计算平均持仓天数
        
        Args:
            trades: 交易记录 DataFrame
            
        Returns:
            平均持仓天数
        """
        if trades.empty:
            return 0.0
        
        # 需要有买入和卖出的配对信息
        # 简化处理：假设交易记录中有持仓天数信息
        if 'holding_days' in trades.columns:
            return trades['holding_days'].mean()
        
        return 0.0
    
    # ============================================================
    # 其他计算方法
    # ============================================================
    
    def calculate_rolling_sharpe(
        self,
        returns: pd.Series,
        window: int = 60
    ) -> pd.Series:
        """
        计算滚动夏普比率
        
        Args:
            returns: 日收益率序列
            window: 滚动窗口大小
            
        Returns:
            滚动夏普比率序列
        """
        if len(returns) < window:
            return pd.Series()
        
        # 日无风险利率
        daily_rf = self.risk_free_rate / self.trading_days_per_year
        
        # 计算滚动均值和标准差
        rolling_mean = returns.rolling(window=window).mean()
        rolling_std = returns.rolling(window=window).std()
        
        # 计算滚动夏普比率
        rolling_sharpe = (rolling_mean - daily_rf) / rolling_std * np.sqrt(self.trading_days_per_year)
        
        return rolling_sharpe
    
    def calculate_drawdown_series(self, equity_curve: pd.Series) -> pd.Series:
        """
        计算回撤序列
        
        Args:
            equity_curve: 权益曲线
            
        Returns:
            回撤序列
        """
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        
        return drawdown


if __name__ == "__main__":
    # 测试绩效指标计算模块
    print("=" * 60)
    print("测试绩效指标计算模块")
    print("=" * 60)
    
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # 创建测试数据
    print("\n【创建测试数据】")
    dates = pd.date_range(start='2023-01-01', periods=252, freq='B')
    
    # 模拟权益曲线
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 252)  # 日均收益 0.1%，波动 2%
    equity = 1000000 * (1 + returns).cumprod()
    equity_curve = pd.Series(equity, index=dates)
    
    # 模拟基准曲线
    benchmark_returns = np.random.normal(0.0005, 0.015, 252)
    benchmark = 1000000 * (1 + benchmark_returns).cumprod()
    benchmark_curve = pd.Series(benchmark, index=dates)
    
    print(f"权益曲线长度: {len(equity_curve)}")
    print(f"初始资产: {equity_curve.iloc[0]:,.2f}")
    print(f"最终资产: {equity_curve.iloc[-1]:,.2f}")
    
    # 计算绩效指标
    print("\n【计算绩效指标】")
    calculator = MetricsCalculator()
    metrics = calculator.calculate(equity_curve, benchmark_curve)
    
    print(f"\n收益指标:")
    print(f"  总收益率: {metrics.total_return*100:.2f}%")
    print(f"  年化收益率: {metrics.annual_return*100:.2f}%")
    print(f"  基准收益率: {metrics.benchmark_return*100:.2f}%")
    print(f"  超额收益: {metrics.excess_return*100:.2f}%")
    
    print(f"\n风险指标:")
    print(f"  年化波动率: {metrics.volatility*100:.2f}%")
    print(f"  最大回撤: {metrics.max_drawdown*100:.2f}%")
    print(f"  最大回撤持续期: {metrics.max_drawdown_duration} 天")
    print(f"  VaR(95%): {metrics.var_95*100:.2f}%")
    print(f"  CVaR(95%): {metrics.cvar_95*100:.2f}%")
    
    print(f"\n风险调整收益指标:")
    print(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
    print(f"  索提诺比率: {metrics.sortino_ratio:.2f}")
    print(f"  卡玛比率: {metrics.calmar_ratio:.2f}")
    print(f"  信息比率: {metrics.information_ratio:.2f}")
    
    print("\n" + "=" * 60)
    print("绩效指标计算模块测试完成！")
    print("=" * 60)