"""
多因子选股策略

基于多个因子进行股票筛选和组合构建的策略
通过因子暴露和因子收益预测来选择股票

策略原理：
1. 选择有效的因子（价值、成长、质量、动量等）
2. 对因子进行标准化和加权
3. 计算综合得分
4. 选择得分最高的股票构建组合
5. 定期调仓

使用方法:
    from strategies.multi_factor import MultiFactorStrategy
    
    strategy = MultiFactorStrategy()
    signals = strategy.generate_signals(data, factor_data)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# 导入项目模块
from strategies.base import BaseStrategy, StrategyConfig, Signal
from core.utils.logger import get_logger
from core.utils.helpers import winsorize, standardize, safe_divide

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class FactorConfig:
    """
    因子配置数据类
    
    Attributes:
        name: 因子名称
        weight: 因子权重
        direction: 因子方向 (1=正向, -1=反向)
        winsorize_limit: 缩尾比例
    """
    
    name: str
    weight: float = 1.0
    direction: int = 1
    winsorize_limit: float = 0.01


@dataclass
class MultiFactorConfig(StrategyConfig):
    """
    多因子策略配置
    
    Attributes:
        factors: 因子配置列表
        rebalance_freq: 调仓频率（天）
        top_n: 选股数量
        min_score: 最低得分要求
        factor_neutralize: 是否进行行业中性化
    """
    
    name: str = "MultiFactor"
    description: str = "多因子选股策略"
    factors: List[FactorConfig] = None
    rebalance_freq: int = 20
    top_n: int = 10
    min_score: float = 0.0
    factor_neutralize: bool = False
    
    def __post_init__(self):
        """初始化后处理"""
        if self.factors is None:
            # 默认因子配置
            self.factors = [
                FactorConfig(name='value', weight=0.25, direction=1),      # 价值因子
                FactorConfig(name='growth', weight=0.25, direction=1),     # 成长因子
                FactorConfig(name='quality', weight=0.25, direction=1),    # 质量因子
                FactorConfig(name='momentum', weight=0.25, direction=1),   # 动量因子
            ]


class FactorCalculator:
    """
    因子计算器
    
    计算各类常用因子
    
    因子分类：
    1. 价值因子：PE、PB、PS、PCF 等
    2. 成长因子：营收增长、利润增长等
    3. 质量因子：ROE、ROA、毛利率等
    4. 动量因子：价格动量、盈余动量等
    5. 技术因子：波动率、换手率、流动性等
    """
    
    @staticmethod
    def calculate_value_factors(df: pd.DataFrame) -> pd.Series:
        """
        计算价值因子
        
        Args:
            df: 包含财务数据的 DataFrame
            
        Returns:
            价值因子得分
        """
        factors = {}
        
        # PE 因子（市盈率倒数）
        if 'pe' in df.columns:
            factors['ep'] = 1 / df['pe'].replace(0, np.nan)
        
        # PB 因子（市净率倒数）
        if 'pb' in df.columns:
            factors['bp'] = 1 / df['pb'].replace(0, np.nan)
        
        # PS 因子（市销率倒数）
        if 'ps' in df.columns:
            factors['sp'] = 1 / df['ps'].replace(0, np.nan)
        
        # 计算综合得分
        if factors:
            factor_df = pd.DataFrame(factors)
            # 标准化后取平均
            for col in factor_df.columns:
                factor_df[col] = standardize(factor_df[col])
            return factor_df.mean(axis=1)
        
        return pd.Series()
    
    @staticmethod
    def calculate_growth_factors(df: pd.DataFrame) -> pd.Series:
        """
        计算成长因子
        
        Args:
            df: 包含财务数据的 DataFrame
            
        Returns:
            成长因子得分
        """
        factors = {}
        
        # 营收增长率
        if 'revenue' in df.columns:
            factors['revenue_growth'] = df['revenue'].pct_change()
        
        # 净利润增长率
        if 'net_profit' in df.columns:
            factors['profit_growth'] = df['net_profit'].pct_change()
        
        # 计算综合得分
        if factors:
            factor_df = pd.DataFrame(factors)
            for col in factor_df.columns:
                factor_df[col] = standardize(factor_df[col])
            return factor_df.mean(axis=1)
        
        return pd.Series()
    
    @staticmethod
    def calculate_quality_factors(df: pd.DataFrame) -> pd.Series:
        """
        计算质量因子
        
        Args:
            df: 包含财务数据的 DataFrame
            
        Returns:
            质量因子得分
        """
        factors = {}
        
        # ROE
        if 'roe' in df.columns:
            factors['roe'] = df['roe']
        
        # ROA
        if 'roa' in df.columns:
            factors['roa'] = df['roa']
        
        # 毛利率
        if 'gross_margin' in df.columns:
            factors['gross_margin'] = df['gross_margin']
        
        # 净利率
        if 'net_margin' in df.columns:
            factors['net_margin'] = df['net_margin']
        
        # 计算综合得分
        if factors:
            factor_df = pd.DataFrame(factors)
            for col in factor_df.columns:
                factor_df[col] = standardize(factor_df[col])
            return factor_df.mean(axis=1)
        
        return pd.Series()
    
    @staticmethod
    def calculate_momentum_factors(df: pd.DataFrame) -> pd.Series:
        """
        计算动量因子
        
        Args:
            df: K 线数据
            
        Returns:
            动量因子得分
        """
        close = df['close']
        factors = {}
        
        # 1 个月动量
        factors['mom_1m'] = close.pct_change(20)
        
        # 3 个月动量
        factors['mom_3m'] = close.pct_change(60)
        
        # 6 个月动量
        factors['mom_6m'] = close.pct_change(120)
        
        # 12 个月动量（剔除最近1个月）
        factors['mom_12m'] = close.shift(20) / close.shift(240) - 1
        
        # 计算综合得分
        factor_df = pd.DataFrame(factors)
        for col in factor_df.columns:
            factor_df[col] = standardize(factor_df[col])
        
        return factor_df.mean(axis=1)
    
    @staticmethod
    def calculate_technical_factors(df: pd.DataFrame) -> pd.Series:
        """
        计算技术因子
        
        Args:
            df: K 线数据
            
        Returns:
            技术因子得分
        """
        factors = {}
        
        # 波动率（反向）
        returns = df['close'].pct_change()
        factors['volatility'] = -returns.rolling(20).std()
        
        # 换手率（反向）
        if 'turnover' in df.columns:
            factors['turnover'] = -df['turnover']
        
        # 流动性（正向）
        if 'amount' in df.columns:
            factors['liquidity'] = np.log(df['amount'] + 1)
        
        # 计算综合得分
        factor_df = pd.DataFrame(factors)
        for col in factor_df.columns:
            factor_df[col] = standardize(factor_df[col])
        
        return factor_df.mean(axis=1)


class MultiFactorStrategy(BaseStrategy):
    """
    多因子选股策略
    
    基于多个因子综合评分进行选股
    
    策略流程：
    1. 计算各因子值
    2. 因子预处理（缺失值处理、缩尾、标准化）
    3. 因子加权合成综合得分
    4. 按得分排序选股
    5. 定期调仓
    
    Attributes:
        config: 策略配置
        last_rebalance: 上次调仓日期
        current_holdings: 当前持仓
    """
    
    def __init__(self, config: Optional[MultiFactorConfig] = None):
        """
        初始化多因子策略
        
        Args:
            config: 策略配置
        """
        super().__init__(config or MultiFactorConfig())
        
        self.last_rebalance: Optional[datetime] = None
        self.current_holdings: List[str] = []
        self.factor_calculator = FactorCalculator()
    
    def generate_signals(
        self,
        data: Dict[str, pd.DataFrame],
        factor_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: K 线数据字典
            factor_data: 因子数据字典（可选）
            
        Returns:
            信号列表
        """
        signals = []
        
        # 检查是否需要调仓
        if not self._should_rebalance(data):
            return signals
        
        # 计算综合得分
        scores = self._calculate_scores(data, factor_data)
        
        if scores.empty:
            return signals
        
        # 选股
        selected_stocks = self._select_stocks(scores)
        
        # 生成调仓信号
        signals = self._generate_rebalance_signals(data, selected_stocks)
        
        # 更新持仓
        self.current_holdings = selected_stocks
        
        return signals
    
    def _should_rebalance(self, data: Dict[str, pd.DataFrame]) -> bool:
        """
        判断是否需要调仓
        
        Args:
            data: 数据字典
            
        Returns:
            是否需要调仓
        """
        if not data:
            return False
        
        # 获取当前日期
        first_df = list(data.values())[0]
        current_date = first_df['date'].iloc[-1]
        
        # 首次调仓
        if self.last_rebalance is None:
            self.last_rebalance = current_date
            return True
        
        # 检查调仓间隔
        days_since_last = (pd.to_datetime(current_date) - 
                          pd.to_datetime(self.last_rebalance)).days
        
        if days_since_last >= self.config.rebalance_freq:
            self.last_rebalance = current_date
            return True
        
        return False
    
    def _calculate_scores(
        self,
        data: Dict[str, pd.DataFrame],
        factor_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> pd.Series:
        """
        计算综合得分
        
        Args:
            data: K 线数据
            factor_data: 因子数据
            
        Returns:
            综合得分 Series
        """
        all_scores = {}
        
        for stock_code, df in data.items():
            if len(df) < 20:
                continue
            
            # 计算各类因子
            factor_scores = {}
            
            for factor_config in self.config.factors:
                factor_name = factor_config.name
                factor_score = self._calculate_single_factor(
                    stock_code, df, factor_name, factor_data
                )
                
                if factor_score is not None:
                    # 应用因子方向
                    factor_score *= factor_config.direction
                    factor_scores[factor_name] = factor_score * factor_config.weight
            
            # 计算综合得分
            if factor_scores:
                all_scores[stock_code] = sum(factor_scores.values())
        
        return pd.Series(all_scores)
    
    def _calculate_single_factor(
        self,
        stock_code: str,
        df: pd.DataFrame,
        factor_name: str,
        factor_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[float]:
        """
        计算单个因子得分
        
        Args:
            stock_code: 股票代码
            df: K 线数据
            factor_name: 因子名称
            factor_data: 因子数据
            
        Returns:
            因子得分
        """
        # 如果有预计算的因子数据
        if factor_data and stock_code in factor_data:
            factor_df = factor_data[stock_code]
            if factor_name in factor_df.columns:
                return factor_df[factor_name].iloc[-1]
        
        # 根据因子类型计算
        if factor_name == 'value':
            scores = self.factor_calculator.calculate_value_factors(df)
        elif factor_name == 'growth':
            scores = self.factor_calculator.calculate_growth_factors(df)
        elif factor_name == 'quality':
            scores = self.factor_calculator.calculate_quality_factors(df)
        elif factor_name == 'momentum':
            scores = self.factor_calculator.calculate_momentum_factors(df)
        elif factor_name == 'technical':
            scores = self.factor_calculator.calculate_technical_factors(df)
        else:
            return None
        
        if not scores.empty:
            return scores.iloc[-1]
        
        return None
    
    def _select_stocks(self, scores: pd.Series) -> List[str]:
        """
        选择股票
        
        Args:
            scores: 综合得分
            
        Returns:
            选中的股票代码列表
        """
        # 过滤最低得分
        scores = scores[scores >= self.config.min_score]
        
        # 排序并选择前 N 只
        scores = scores.sort_values(ascending=False)
        
        selected = scores.head(self.config.top_n).index.tolist()
        
        logger.info(f"选中 {len(selected)} 只股票: {selected[:5]}...")
        
        return selected
    
    def _generate_rebalance_signals(
        self,
        data: Dict[str, pd.DataFrame],
        selected_stocks: List[str]
    ) -> List[Signal]:
        """
        生成调仓信号
        
        Args:
            data: K 线数据
            selected_stocks: 选中的股票
            
        Returns:
            信号列表
        """
        signals = []
        
        # 卖出不在新组合中的股票
        for stock_code in self.current_holdings:
            if stock_code not in selected_stocks:
                if stock_code in data:
                    price = data[stock_code]['close'].iloc[-1]
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='sell',
                        price=price,
                        reason="调仓卖出"
                    ))
        
        # 买入新选入的股票
        for stock_code in selected_stocks:
            if stock_code not in self.current_holdings:
                if stock_code in data:
                    price = data[stock_code]['close'].iloc[-1]
                    signals.append(Signal(
                        stock_code=stock_code,
                        signal_type='buy',
                        price=price,
                        reason="调仓买入"
                    ))
        
        return signals


class FamaFrenchStrategy(BaseStrategy):
    """
    Fama-French 多因子策略
    
    基于经典的三因子/五因子模型
    
    三因子：
    - 市场因子 (MKT)
    - 规模因子 (SMB)
    - 价值因子 (HML)
    
    五因子增加：
    - 盈利因子 (RMW)
    - 投资因子 (CMA)
    """
    
    def __init__(
        self,
        factors: List[str] = None,
        top_n: int = 20
    ):
        """
        初始化 Fama-French 策略
        
        Args:
            factors: 使用的因子列表
            top_n: 选股数量
        """
        config = StrategyConfig(
            name="FamaFrench",
            description="Fama-French多因子策略"
        )
        super().__init__(config)
        
        self.factors = factors or ['size', 'value', 'momentum']
        self.top_n = top_n
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        # 计算各因子暴露
        factor_exposures = {}
        
        for stock_code, df in data.items():
            if len(df) < 60:
                continue
            
            exposures = {}
            
            # 规模因子（市值反向，小市值溢价）
            if 'market_cap' in df.columns:
                exposures['size'] = -np.log(df['market_cap'].iloc[-1])
            
            # 价值因子（B/P）
            if 'pb' in df.columns:
                exposures['value'] = 1 / df['pb'].iloc[-1]
            
            # 动量因子
            exposures['momentum'] = df['close'].pct_change(60).iloc[-1]
            
            factor_exposures[stock_code] = exposures
        
        if not factor_exposures:
            return signals
        
        # 计算综合得分
        scores = pd.Series()
        for stock_code, exposures in factor_exposures.items():
            score = 0
            for factor in self.factors:
                if factor in exposures:
                    score += exposures[factor]
            scores[stock_code] = score
        
        # 标准化得分
        scores = (scores - scores.mean()) / scores.std()
        
        # 选择得分最高的股票
        selected = scores.nlargest(self.top_n).index.tolist()
        
        # 生成买入信号
        for stock_code in selected:
            if stock_code in data:
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    reason=f"多因子选股，得分: {scores[stock_code]:.2f}"
                ))
        
        return signals


class BarraRiskModelStrategy(BaseStrategy):
    """
    Barra 风险模型策略
    
    基于 Barra 风险模型的因子投资策略
    
    主要因子类别：
    - 风格因子：规模、动量、价值、波动率等
    - 行业因子：各行业暴露
    """
    
    def __init__(
        self,
        style_factors: List[str] = None,
        target_weights: Dict[str, float] = None,
        top_n: int = 30
    ):
        """
        初始化 Barra 策略
        
        Args:
            style_factors: 风格因子列表
            target_weights: 目标因子权重
            top_n: 选股数量
        """
        config = StrategyConfig(
            name="BarraRiskModel",
            description="Barra风险模型策略"
        )
        super().__init__(config)
        
        self.style_factors = style_factors or [
            'size', 'momentum', 'value', 'volatility', 'liquidity'
        ]
        self.target_weights = target_weights or {
            'size': -0.2,      # 偏向小盘
            'momentum': 0.3,   # 偏向动量
            'value': 0.2,      # 偏向价值
            'volatility': -0.2, # 偏向低波动
            'liquidity': 0.1   # 偏向流动性
        }
        self.top_n = top_n
    
    def generate_signals(self, data: Dict[str, pd.DataFrame]) -> List[Signal]:
        """生成交易信号"""
        signals = []
        
        # 计算因子暴露矩阵
        exposures = {}
        
        for stock_code, df in data.items():
            if len(df) < 60:
                continue
            
            stock_exposures = {}
            
            # 规模
            if 'market_cap' in df.columns:
                stock_exposures['size'] = np.log(df['market_cap'].iloc[-1])
            
            # 动量
            stock_exposures['momentum'] = df['close'].pct_change(60).iloc[-1]
            
            # 价值
            if 'pe' in df.columns:
                stock_exposures['value'] = -df['pe'].iloc[-1]  # PE 越低越好
            
            # 波动率
            stock_exposures['volatility'] = -df['close'].pct_change().rolling(20).std().iloc[-1]
            
            # 流动性
            if 'amount' in df.columns:
                stock_exposures['liquidity'] = np.log(df['amount'].rolling(20).mean().iloc[-1])
            
            exposures[stock_code] = stock_exposures
        
        if not exposures:
            return signals
        
        # 计算预期收益
        expected_returns = {}
        for stock_code, exp in exposures.items():
            ret = 0
            for factor, exposure in exp.items():
                if factor in self.target_weights:
                    ret += exposure * self.target_weights[factor]
            expected_returns[stock_code] = ret
        
        # 排序选股
        sorted_stocks = sorted(
            expected_returns.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        selected = [s[0] for s in sorted_stocks[:self.top_n]]
        
        # 生成信号
        for stock_code in selected:
            if stock_code in data:
                price = data[stock_code]['close'].iloc[-1]
                signals.append(Signal(
                    stock_code=stock_code,
                    signal_type='buy',
                    price=price,
                    reason=f"Barra因子选股"
                ))
        
        return signals


if __name__ == "__main__":
    # 测试多因子策略
    print("=" * 60)
    print("测试多因子选股策略")
    print("=" * 60)
    
    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    np.random.seed(42)
    
    data = {}
    for i, code in enumerate(['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']):
        prices = 10 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
            'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
            'low': prices * (1 + np.random.uniform(-0.02, 0, 100)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 100),
            'amount': np.random.randint(1000000, 10000000, 100),
            'pe': np.random.uniform(10, 50, 100),
            'pb': np.random.uniform(1, 5, 100),
            'roe': np.random.uniform(0.05, 0.25, 100)
        })
        data[code] = df
    
    # 测试多因子策略
    print("\n【测试多因子策略】")
    strategy = MultiFactorStrategy()
    signals = strategy.generate_signals(data)
    
    print(f"生成信号数量: {len(signals)}")
    for signal in signals:
        print(f"  {signal.signal_type} {signal.stock_code} @ {signal.price:.2f}")
        print(f"    原因: {signal.reason}")
    
    print("\n" + "=" * 60)
    print("多因子选股策略测试完成！")
    print("=" * 60)