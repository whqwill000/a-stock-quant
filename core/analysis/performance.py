"""
绩效分析模块

提供详细的绩效分析功能，包括收益分解、风险分析、归因分析等

使用方法:
    from core.analysis.performance import PerformanceAnalyzer
    
    analyzer = PerformanceAnalyzer()
    report = analyzer.analyze(equity_curve, trades)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# 导入项目模块
from core.utils.logger import get_logger
from core.backtest.metrics import MetricsCalculator, PerformanceMetrics

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class PerformanceReport:
    """
    绩效分析报告数据类
    
    存储详细的绩效分析结果
    
    Attributes:
        metrics: 基础绩效指标
        monthly_returns: 月度收益
        yearly_returns: 年度收益
        sector_analysis: 行业分析
        top_winners: 最佳盈利交易
        top_losers: 最大亏损交易
        drawdown_periods: 回撤期间
    """
    
    metrics: PerformanceMetrics
    monthly_returns: pd.DataFrame = None
    yearly_returns: pd.DataFrame = None
    sector_analysis: pd.DataFrame = None
    top_winners: pd.DataFrame = None
    top_losers: pd.DataFrame = None
    drawdown_periods: pd.DataFrame = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            'metrics': self.metrics.to_dict()
        }
        
        if self.monthly_returns is not None:
            result['monthly_returns'] = self.monthly_returns.to_dict()
        
        if self.yearly_returns is not None:
            result['yearly_returns'] = self.yearly_returns.to_dict()
        
        return result


class PerformanceAnalyzer:
    """
    绩效分析器
    
    提供全面的绩效分析功能
    
    主要功能：
    1. 基础指标计算：收益率、波动率、夏普比率等
    2. 时间序列分析：月度收益、年度收益
    3. 交易分析：胜率、盈亏比、持仓分析
    4. 回撤分析：回撤期间、恢复时间
    
    Attributes:
        metrics_calculator: 绩效指标计算器
    """
    
    def __init__(self, risk_free_rate: float = 0.03):
        """
        初始化绩效分析器
        
        Args:
            risk_free_rate: 无风险利率
        """
        self.metrics_calculator = MetricsCalculator(risk_free_rate=risk_free_rate)
        
        logger.info("绩效分析器初始化完成")
    
    def analyze(
        self,
        equity_curve: pd.Series,
        trades: Optional[pd.DataFrame] = None,
        benchmark_curve: Optional[pd.Series] = None
    ) -> PerformanceReport:
        """
        执行完整绩效分析
        
        Args:
            equity_curve: 权益曲线
            trades: 交易记录
            benchmark_curve: 基准曲线
            
        Returns:
            绩效分析报告
        """
        logger.info("开始绩效分析...")
        
        # 计算基础指标
        metrics = self.metrics_calculator.calculate(
            equity_curve, benchmark_curve, trades
        )
        
        # 计算月度收益
        monthly_returns = self._calculate_monthly_returns(equity_curve)
        
        # 计算年度收益
        yearly_returns = self._calculate_yearly_returns(equity_curve)
        
        # 分析交易
        top_winners = None
        top_losers = None
        
        if trades is not None and not trades.empty:
            top_winners, top_losers = self._analyze_trades(trades)
        
        # 分析回撤
        drawdown_periods = self._analyze_drawdowns(equity_curve)
        
        # 创建报告
        report = PerformanceReport(
            metrics=metrics,
            monthly_returns=monthly_returns,
            yearly_returns=yearly_returns,
            top_winners=top_winners,
            top_losers=top_losers,
            drawdown_periods=drawdown_periods
        )
        
        logger.info("绩效分析完成")
        
        return report
    
    def _calculate_monthly_returns(self, equity_curve: pd.Series) -> pd.DataFrame:
        """
        计算月度收益
        
        Args:
            equity_curve: 权益曲线
            
        Returns:
            月度收益 DataFrame
        """
        if equity_curve.empty:
            return pd.DataFrame()
        
        # 确保索引为日期
        if not isinstance(equity_curve.index, pd.DatetimeIndex):
            equity_curve.index = pd.to_datetime(equity_curve.index)
        
        # 按月重采样，取月末值
        monthly = equity_curve.resample('M').last()
        
        # 计算月度收益率
        monthly_returns = monthly.pct_change().dropna()
        
        # 创建月度收益表
        df = pd.DataFrame({
            'return': monthly_returns
        })
        
        # 添加年月信息
        df['year'] = df.index.year
        df['month'] = df.index.month
        
        return df
    
    def _calculate_yearly_returns(self, equity_curve: pd.Series) -> pd.DataFrame:
        """
        计算年度收益
        
        Args:
            equity_curve: 权益曲线
            
        Returns:
            年度收益 DataFrame
        """
        if equity_curve.empty:
            return pd.DataFrame()
        
        # 确保索引为日期
        if not isinstance(equity_curve.index, pd.DatetimeIndex):
            equity_curve.index = pd.to_datetime(equity_curve.index)
        
        # 按年重采样
        yearly = equity_curve.resample('Y').last()
        
        # 计算年度收益率
        yearly_returns = yearly.pct_change().dropna()
        
        df = pd.DataFrame({
            'year': yearly_returns.index.year,
            'return': yearly_returns.values
        })
        
        return df
    
    def _analyze_trades(
        self,
        trades: pd.DataFrame,
        top_n: int = 10
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        分析交易记录
        
        Args:
            trades: 交易记录
            top_n: 返回前 N 条
            
        Returns:
            (最佳盈利交易, 最大亏损交易)
        """
        # 筛选卖出交易
        sells = trades[trades['type'] == 'sell'] if 'type' in trades.columns else trades
        
        if sells.empty:
            return pd.DataFrame(), pd.DataFrame()
        
        # 按盈亏排序
        if 'realized_pnl' in sells.columns:
            sorted_trades = sells.sort_values('realized_pnl', ascending=False)
            
            top_winners = sorted_trades.head(top_n)
            top_losers = sorted_trades.tail(top_n)
            
            return top_winners, top_losers
        
        return pd.DataFrame(), pd.DataFrame()
    
    def _analyze_drawdowns(
        self,
        equity_curve: pd.Series,
        top_n: int = 5
    ) -> pd.DataFrame:
        """
        分析回撤期间
        
        Args:
            equity_curve: 权益曲线
            top_n: 返回前 N 个最大回撤
            
        Returns:
            回撤期间 DataFrame
        """
        if equity_curve.empty:
            return pd.DataFrame()
        
        # 计算回撤
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax
        
        # 找到回撤期间
        drawdown_periods = []
        in_drawdown = False
        dd_start = None
        dd_low = 0
        dd_low_date = None
        
        for date, value in drawdown.items():
            if value < 0 and not in_drawdown:
                # 开始回撤
                in_drawdown = True
                dd_start = date
                dd_low = value
                dd_low_date = date
            elif value < 0 and in_drawdown:
                # 继续回撤
                if value < dd_low:
                    dd_low = value
                    dd_low_date = date
            elif value == 0 and in_drawdown:
                # 回撤结束
                drawdown_periods.append({
                    'start_date': dd_start,
                    'low_date': dd_low_date,
                    'end_date': date,
                    'drawdown': dd_low,
                    'duration': len(equity_curve[dd_start:date])
                })
                in_drawdown = False
        
        # 如果还在回撤中
        if in_drawdown:
            drawdown_periods.append({
                'start_date': dd_start,
                'low_date': dd_low_date,
                'end_date': None,
                'drawdown': dd_low,
                'duration': len(equity_curve[dd_start:])
            })
        
        # 转换为 DataFrame 并排序
        df = pd.DataFrame(drawdown_periods)
        
        if not df.empty:
            df = df.sort_values('drawdown').head(top_n)
        
        return df
    
    def calculate_rolling_metrics(
        self,
        equity_curve: pd.Series,
        window: int = 60
    ) -> pd.DataFrame:
        """
        计算滚动指标
        
        Args:
            equity_curve: 权益曲线
            window: 滚动窗口
            
        Returns:
            滚动指标 DataFrame
        """
        if len(equity_curve) < window:
            return pd.DataFrame()
        
        returns = equity_curve.pct_change().dropna()
        
        # 滚动收益
        rolling_return = returns.rolling(window=window).sum()
        
        # 滚动波动率
        rolling_vol = returns.rolling(window=window).std() * np.sqrt(252)
        
        # 滚动夏普比率
        rolling_sharpe = self.metrics_calculator.calculate_rolling_sharpe(returns, window)
        
        # 滚动最大回撤
        rolling_max_dd = pd.Series(index=equity_curve.index, dtype=float)
        for i in range(window, len(equity_curve)):
            window_data = equity_curve.iloc[i-window:i]
            max_dd, _ = self.metrics_calculator._calculate_max_drawdown(window_data)
            rolling_max_dd.iloc[i] = max_dd
        
        df = pd.DataFrame({
            'rolling_return': rolling_return,
            'rolling_volatility': rolling_vol,
            'rolling_sharpe': rolling_sharpe,
            'rolling_max_drawdown': rolling_max_dd
        })
        
        return df.dropna()
    
    def generate_report_text(self, report: PerformanceReport) -> str:
        """
        生成文本报告
        
        Args:
            report: 绩效分析报告
            
        Returns:
            报告文本
        """
        lines = [
            "=" * 70,
            "绩效分析报告",
            "=" * 70,
            "",
            "一、收益指标",
            "-" * 70,
            f"  总收益率:     {report.metrics.total_return*100:>10.2f}%",
            f"  年化收益率:   {report.metrics.annual_return*100:>10.2f}%",
            f"  基准收益率:   {report.metrics.benchmark_return*100:>10.2f}%",
            f"  超额收益:     {report.metrics.excess_return*100:>10.2f}%",
            "",
            "二、风险指标",
            "-" * 70,
            f"  年化波动率:   {report.metrics.volatility*100:>10.2f}%",
            f"  最大回撤:     {report.metrics.max_drawdown*100:>10.2f}%",
            f"  VaR(95%):     {report.metrics.var_95*100:>10.2f}%",
            f"  CVaR(95%):    {report.metrics.cvar_95*100:>10.2f}%",
            "",
            "三、风险调整收益",
            "-" * 70,
            f"  夏普比率:     {report.metrics.sharpe_ratio:>10.2f}",
            f"  索提诺比率:   {report.metrics.sortino_ratio:>10.2f}",
            f"  卡玛比率:     {report.metrics.calmar_ratio:>10.2f}",
            f"  信息比率:     {report.metrics.information_ratio:>10.2f}",
            "",
            "四、交易统计",
            "-" * 70,
            f"  总交易次数:   {report.metrics.total_trades:>10}",
            f"  胜率:         {report.metrics.win_rate*100:>10.2f}%",
            f"  盈亏比:       {report.metrics.profit_loss_ratio:>10.2f}",
            "",
        ]
        
        # 添加月度收益
        if report.monthly_returns is not None and not report.monthly_returns.empty:
            lines.extend([
                "五、月度收益",
                "-" * 70,
            ])
            
            # 创建月度收益表格
            monthly_pivot = report.monthly_returns.pivot(
                index='year',
                columns='month',
                values='return'
            )
            
            for year in monthly_pivot.index:
                row = f"  {year}: "
                for month in range(1, 13):
                    if month in monthly_pivot.columns:
                        val = monthly_pivot.loc[year, month]
                        if pd.notna(val):
                            row += f"{val*100:>6.1f}% "
                        else:
                            row += "       "
                lines.append(row)
            
            lines.append("")
        
        # 添加回撤期间
        if report.drawdown_periods is not None and not report.drawdown_periods.empty:
            lines.extend([
                "六、主要回撤期间",
                "-" * 70,
            ])
            
            for _, row in report.drawdown_periods.iterrows():
                lines.append(
                    f"  {row['start_date'].strftime('%Y-%m-%d')} ~ "
                    f"{row['end_date'].strftime('%Y-%m-%d') if pd.notna(row['end_date']) else '至今'}: "
                    f"{row['drawdown']*100:.2f}% ({row['duration']}天)"
                )
            
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试绩效分析模块
    print("=" * 60)
    print("测试绩效分析模块")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=252, freq='B')
    np.random.seed(42)
    
    # 模拟权益曲线
    returns = np.random.normal(0.001, 0.02, 252)
    equity = 1000000 * (1 + returns).cumprod()
    equity_curve = pd.Series(equity, index=dates)
    
    # 创建分析器
    analyzer = PerformanceAnalyzer()
    
    # 执行分析
    report = analyzer.analyze(equity_curve)
    
    # 打印报告
    print(analyzer.generate_report_text(report))
    
    print("\n" + "=" * 60)
    print("绩效分析模块测试完成！")
    print("=" * 60)