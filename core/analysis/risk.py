"""
风险分析模块

提供详细的风险分析功能，包括 VaR、CVaR、压力测试、风险归因等

使用方法:
    from core.analysis.risk import RiskAnalyzer
    
    analyzer = RiskAnalyzer()
    report = analyzer.analyze(returns, positions)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats

# 导入项目模块
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class RiskReport:
    """
    风险分析报告数据类
    
    存储详细的风险分析结果
    
    Attributes:
        var_metrics: VaR 指标
        volatility_metrics: 波动率指标
        drawdown_metrics: 回撤指标
        correlation_matrix: 相关性矩阵
        stress_test_results: 压力测试结果
        risk_attribution: 风险归因
    """
    
    var_metrics: Dict = None
    volatility_metrics: Dict = None
    drawdown_metrics: Dict = None
    correlation_matrix: pd.DataFrame = None
    stress_test_results: pd.DataFrame = None
    risk_attribution: Dict = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        result = {}
        
        if self.var_metrics:
            result['var_metrics'] = self.var_metrics
        
        if self.volatility_metrics:
            result['volatility_metrics'] = self.volatility_metrics
        
        if self.drawdown_metrics:
            result['drawdown_metrics'] = self.drawdown_metrics
        
        if self.risk_attribution:
            result['risk_attribution'] = self.risk_attribution
        
        return result


class RiskAnalyzer:
    """
    风险分析器
    
    提供全面的风险分析功能
    
    主要功能：
    1. VaR 分析：历史模拟法、参数法、蒙特卡洛模拟
    2. 波动率分析：历史波动率、GARCH 模型
    3. 回撤分析：最大回撤、回撤持续期
    4. 压力测试：历史情景、假设情景
    5. 风险归因：因子归因、行业归因
    
    Attributes:
        confidence_levels: 置信水平列表
    """
    
    def __init__(self, confidence_levels: List[float] = None):
        """
        初始化风险分析器
        
        Args:
            confidence_levels: 置信水平列表，默认 [0.90, 0.95, 0.99]
        """
        self.confidence_levels = confidence_levels or [0.90, 0.95, 0.99]
        
        logger.info("风险分析器初始化完成")
    
    def analyze(
        self,
        returns: pd.Series,
        positions: Optional[pd.DataFrame] = None,
        benchmark_returns: Optional[pd.Series] = None
    ) -> RiskReport:
        """
        执行完整风险分析
        
        Args:
            returns: 策略收益率序列
            positions: 持仓数据（可选）
            benchmark_returns: 基准收益率（可选）
            
        Returns:
            风险分析报告
        """
        logger.info("开始风险分析...")
        
        # 计算 VaR 指标
        var_metrics = self._calculate_var_metrics(returns)
        
        # 计算波动率指标
        volatility_metrics = self._calculate_volatility_metrics(returns)
        
        # 计算回撤指标
        drawdown_metrics = self._calculate_drawdown_metrics(returns)
        
        # 压力测试
        stress_test_results = self._run_stress_tests(returns)
        
        # 风险归因
        risk_attribution = None
        if positions is not None and not positions.empty:
            risk_attribution = self._calculate_risk_attribution(returns, positions)
        
        # 创建报告
        report = RiskReport(
            var_metrics=var_metrics,
            volatility_metrics=volatility_metrics,
            drawdown_metrics=drawdown_metrics,
            stress_test_results=stress_test_results,
            risk_attribution=risk_attribution
        )
        
        logger.info("风险分析完成")
        
        return report
    
    # ============================================================
    # VaR 分析
    # ============================================================
    
    def _calculate_var_metrics(self, returns: pd.Series) -> Dict:
        """
        计算 VaR 指标
        
        使用多种方法计算 VaR
        
        Args:
            returns: 收益率序列
            
        Returns:
            VaR 指标字典
        """
        metrics = {}
        
        for confidence in self.confidence_levels:
            # 历史模拟法
            var_historical = self._var_historical(returns, confidence)
            
            # 参数法（正态分布假设）
            var_parametric = self._var_parametric(returns, confidence)
            
            # CVaR (Expected Shortfall)
            cvar = self._cvar(returns, confidence)
            
            metrics[f'{int(confidence*100)}%'] = {
                'var_historical': var_historical,
                'var_parametric': var_parametric,
                'cvar': cvar
            }
        
        return metrics
    
    def _var_historical(
        self,
        returns: pd.Series,
        confidence: float
    ) -> float:
        """
        历史模拟法计算 VaR
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            
        Returns:
            VaR 值
        """
        return -np.percentile(returns, (1 - confidence) * 100)
    
    def _var_parametric(
        self,
        returns: pd.Series,
        confidence: float
    ) -> float:
        """
        参数法计算 VaR（正态分布假设）
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            
        Returns:
            VaR 值
        """
        mean = returns.mean()
        std = returns.std()
        
        # 计算分位数
        z_score = stats.norm.ppf(1 - confidence)
        
        return -(mean + z_score * std)
    
    def _cvar(
        self,
        returns: pd.Series,
        confidence: float
    ) -> float:
        """
        计算 CVaR (Conditional VaR / Expected Shortfall)
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            
        Returns:
            CVaR 值
        """
        var = self._var_historical(returns, confidence)
        
        # 计算超过 VaR 的平均损失
        tail_returns = returns[returns < -var]
        
        if len(tail_returns) == 0:
            return var
        
        return -tail_returns.mean()
    
    def var_monte_carlo(
        self,
        returns: pd.Series,
        confidence: float,
        simulations: int = 10000,
        horizon: int = 1
    ) -> float:
        """
        蒙特卡洛模拟计算 VaR
        
        Args:
            returns: 收益率序列
            confidence: 置信水平
            simulations: 模拟次数
            horizon: 时间跨度（天）
            
        Returns:
            VaR 值
        """
        mean = returns.mean()
        std = returns.std()
        
        # 生成模拟收益
        simulated_returns = np.random.normal(mean, std, simulations)
        
        # 计算分位数
        return -np.percentile(simulated_returns, (1 - confidence) * 100)
    
    # ============================================================
    # 波动率分析
    # ============================================================
    
    def _calculate_volatility_metrics(self, returns: pd.Series) -> Dict:
        """
        计算波动率指标
        
        Args:
            returns: 收益率序列
            
        Returns:
            波动率指标字典
        """
        # 日波动率
        daily_vol = returns.std()
        
        # 年化波动率
        annual_vol = daily_vol * np.sqrt(252)
        
        # 滚动波动率（20日）
        rolling_vol_20 = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
        
        # 滚动波动率（60日）
        rolling_vol_60 = returns.rolling(60).std().iloc[-1] * np.sqrt(252)
        
        # 下行波动率
        negative_returns = returns[returns < 0]
        downside_vol = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
        
        return {
            'daily_volatility': daily_vol,
            'annual_volatility': annual_vol,
            'rolling_volatility_20d': rolling_vol_20,
            'rolling_volatility_60d': rolling_vol_60,
            'downside_volatility': downside_vol
        }
    
    def calculate_garch_volatility(
        self,
        returns: pd.Series,
        p: int = 1,
        q: int = 1
    ) -> pd.Series:
        """
        使用 GARCH 模型估计波动率
        
        简化版本，实际应使用 arch 库
        
        Args:
            returns: 收益率序列
            p: GARCH 阶数
            q: ARCH 阶数
            
        Returns:
            波动率序列
        """
        # 简化：使用指数加权移动平均
        lambda_param = 0.94
        
        # 计算方差
        variance = returns.ewm(alpha=1-lambda_param).var()
        
        # 转换为波动率
        volatility = np.sqrt(variance) * np.sqrt(252)
        
        return volatility
    
    # ============================================================
    # 回撤分析
    # ============================================================
    
    def _calculate_drawdown_metrics(self, returns: pd.Series) -> Dict:
        """
        计算回撤指标
        
        Args:
            returns: 收益率序列
            
        Returns:
            回撤指标字典
        """
        # 计算累计收益
        cumulative = (1 + returns).cumprod()
        
        # 计算回撤
        cummax = cumulative.cummax()
        drawdown = (cumulative - cummax) / cummax
        
        # 最大回撤
        max_drawdown = drawdown.min()
        
        # 平均回撤
        avg_drawdown = drawdown.mean()
        
        # 回撤持续期
        in_drawdown = drawdown < 0
        drawdown_periods = []
        current_period = 0
        
        for dd in in_drawdown:
            if dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        
        if current_period > 0:
            drawdown_periods.append(current_period)
        
        # 平均回撤持续期
        avg_drawdown_duration = np.mean(drawdown_periods) if drawdown_periods else 0
        
        # 最大回撤持续期
        max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
        
        # 回撤频率
        drawdown_frequency = len(drawdown_periods) / len(returns) * 252
        
        return {
            'max_drawdown': max_drawdown,
            'avg_drawdown': avg_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'avg_drawdown_duration': avg_drawdown_duration,
            'drawdown_frequency': drawdown_frequency
        }
    
    # ============================================================
    # 压力测试
    # ============================================================
    
    def _run_stress_tests(self, returns: pd.Series) -> pd.DataFrame:
        """
        运行压力测试
        
        Args:
            returns: 收益率序列
            
        Returns:
            压力测试结果 DataFrame
        """
        results = []
        
        # 历史情景
        scenarios = {
            '2008金融危机': -0.05,      # 单日最大跌幅约 5%
            '2020疫情冲击': -0.03,       # 单日跌幅约 3%
            '2015股灾': -0.04,           # 单日跌幅约 4%
            '极端下跌': -0.10,           # 假设极端情况
            '温和下跌': -0.02,           # 温和下跌
            '大幅上涨': 0.05             # 大幅上涨
        }
        
        current_value = 1000000  # 假设当前资产 100 万
        
        for scenario, shock in scenarios.items():
            # 计算冲击后的资产价值
            shocked_value = current_value * (1 + shock)
            
            # 计算损失
            loss = current_value - shocked_value
            
            results.append({
                'scenario': scenario,
                'shock': shock,
                'shocked_value': shocked_value,
                'loss': loss,
                'loss_pct': shock
            })
        
        # 基于历史分布的压力测试
        var_99 = self._var_historical(returns, 0.99)
        var_95 = self._var_historical(returns, 0.95)
        
        results.extend([
            {
                'scenario': 'VaR 99% 冲击',
                'shock': -var_99,
                'shocked_value': current_value * (1 - var_99),
                'loss': current_value * var_99,
                'loss_pct': -var_99
            },
            {
                'scenario': 'VaR 95% 冲击',
                'shock': -var_95,
                'shocked_value': current_value * (1 - var_95),
                'loss': current_value * var_95,
                'loss_pct': -var_95
            }
        ])
        
        return pd.DataFrame(results)
    
    # ============================================================
    # 风险归因
    # ============================================================
    
    def _calculate_risk_attribution(
        self,
        returns: pd.Series,
        positions: pd.DataFrame
    ) -> Dict:
        """
        计算风险归因
        
        分析各持仓对组合风险的贡献
        
        Args:
            returns: 组合收益率
            positions: 持仓数据
            
        Returns:
            风险归因字典
        """
        # 简化版本：按持仓权重分析
        if positions.empty:
            return {}
        
        # 计算各持仓权重
        total_value = positions['market_value'].sum()
        
        if total_value == 0:
            return {}
        
        positions['weight'] = positions['market_value'] / total_value
        
        # 计算风险贡献（简化：假设各持仓独立）
        attribution = {
            'positions': [],
            'concentration_risk': 0.0,
            'diversification_ratio': 0.0
        }
        
        # 计算集中度风险（赫芬达尔指数）
        hhi = (positions['weight'] ** 2).sum()
        attribution['concentration_risk'] = hhi
        
        # 分散化比率
        attribution['diversification_ratio'] = 1 - hhi
        
        # 各持仓风险贡献
        for _, row in positions.iterrows():
            attribution['positions'].append({
                'stock_code': row['stock_code'],
                'weight': row['weight'],
                'risk_contribution': row['weight'] ** 2  # 简化计算
            })
        
        return attribution
    
    # ============================================================
    # 相关性分析
    # ============================================================
    
    def calculate_correlation_matrix(
        self,
        returns_dict: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """
        计算相关性矩阵
        
        Args:
            returns_dict: 收益率字典 {资产名称: 收益率序列}
            
        Returns:
            相关性矩阵
        """
        # 合并收益率
        df = pd.DataFrame(returns_dict)
        
        # 计算相关性
        corr_matrix = df.corr()
        
        return corr_matrix
    
    def calculate_rolling_correlation(
        self,
        returns1: pd.Series,
        returns2: pd.Series,
        window: int = 60
    ) -> pd.Series:
        """
        计算滚动相关性
        
        Args:
            returns1: 第一个收益率序列
            returns2: 第二个收益率序列
            window: 滚动窗口
            
        Returns:
            滚动相关性序列
        """
        # 对齐日期
        common_idx = returns1.index.intersection(returns2.index)
        r1 = returns1.loc[common_idx]
        r2 = returns2.loc[common_idx]
        
        # 计算滚动相关性
        rolling_corr = r1.rolling(window).corr(r2)
        
        return rolling_corr
    
    # ============================================================
    # 报告生成
    # ============================================================
    
    def generate_report_text(self, report: RiskReport) -> str:
        """
        生成文本报告
        
        Args:
            report: 风险分析报告
            
        Returns:
            报告文本
        """
        lines = [
            "=" * 70,
            "风险分析报告",
            "=" * 70,
            "",
            "一、VaR 指标",
            "-" * 70,
        ]
        
        # VaR 指标
        if report.var_metrics:
            for level, metrics in report.var_metrics.items():
                lines.append(f"  置信水平 {level}:")
                lines.append(f"    VaR (历史模拟): {metrics['var_historical']*100:.2f}%")
                lines.append(f"    VaR (参数法):   {metrics['var_parametric']*100:.2f}%")
                lines.append(f"    CVaR:           {metrics['cvar']*100:.2f}%")
        
        lines.extend([
            "",
            "二、波动率指标",
            "-" * 70,
        ])
        
        # 波动率指标
        if report.volatility_metrics:
            metrics = report.volatility_metrics
            lines.append(f"  日波动率:       {metrics['daily_volatility']*100:.2f}%")
            lines.append(f"  年化波动率:     {metrics['annual_volatility']*100:.2f}%")
            lines.append(f"  20日滚动波动率: {metrics['rolling_volatility_20d']*100:.2f}%")
            lines.append(f"  60日滚动波动率: {metrics['rolling_volatility_60d']*100:.2f}%")
            lines.append(f"  下行波动率:     {metrics['downside_volatility']*100:.2f}%")
        
        lines.extend([
            "",
            "三、回撤指标",
            "-" * 70,
        ])
        
        # 回撤指标
        if report.drawdown_metrics:
            metrics = report.drawdown_metrics
            lines.append(f"  最大回撤:       {metrics['max_drawdown']*100:.2f}%")
            lines.append(f"  平均回撤:       {metrics['avg_drawdown']*100:.2f}%")
            lines.append(f"  最大回撤持续期: {metrics['max_drawdown_duration']} 天")
            lines.append(f"  平均回撤持续期: {metrics['avg_drawdown_duration']:.1f} 天")
        
        lines.extend([
            "",
            "四、压力测试结果",
            "-" * 70,
        ])
        
        # 压力测试结果
        if report.stress_test_results is not None and not report.stress_test_results.empty:
            for _, row in report.stress_test_results.iterrows():
                lines.append(
                    f"  {row['scenario']}: "
                    f"冲击 {row['shock']*100:.1f}%, "
                    f"损失 {row['loss']:,.0f} 元"
                )
        
        lines.extend([
            "",
            "=" * 70
        ])
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试风险分析模块
    print("=" * 60)
    print("测试风险分析模块")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=252, freq='B')
    np.random.seed(42)
    
    # 模拟收益率
    returns = pd.Series(np.random.normal(0.001, 0.02, 252), index=dates)
    
    # 创建分析器
    analyzer = RiskAnalyzer()
    
    # 执行分析
    report = analyzer.analyze(returns)
    
    # 打印报告
    print(analyzer.generate_report_text(report))
    
    print("\n" + "=" * 60)
    print("风险分析模块测试完成！")
    print("=" * 60)