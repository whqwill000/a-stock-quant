"""
多智能体强化学习模块

提供多智能体强化学习交易系统，支持：
- 多智能体协作交易
- 智能体间通信与协调
- 分布式决策制定

使用方法:
    from core.rl.multi_agent import MultiAgentSystem

    # 创建多智能体系统
    system = MultiAgentSystem(
        agent_configs=[
            {'name': 'trend_agent', 'type': 'trend'},
            {'name': 'momentum_agent', 'type': 'momentum'},
            {'name': 'risk_agent', 'type': 'risk'}
        ]
    )

    # 运行交易
    result = system.run(data)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
import numpy as np
import logging

# 导入项目模块
from core.utils.logger import get_logger
from core.utils.config import Config

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class AgentAction:
    """
    智能体动作数据类

    存储智能体的动作信息

    Attributes:
        stock_code: 股票代码
        action_type: 动作类型 ('buy', 'sell', 'hold')
        quantity: 数量
        confidence: 置信度 (0-1)
        timestamp: 动作时间
    """

    stock_code: str
    action_type: str
    quantity: int = 0
    confidence: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'action_type': self.action_type,
            'quantity': self.quantity,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class AgentObservation:
    """
    智能体观察数据类

    存储智能体的观察信息

    Attributes:
        stock_code: 股票代码
        price: 当前价格
        volume: 当前成交量
        features: 特征向量
        timestamp: 观察时间
    """

    stock_code: str
    price: float
    volume: int
    features: np.ndarray = None
    timestamp: datetime = None

    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'price': self.price,
            'volume': self.volume,
            'features': self.features.tolist() if self.features is not None else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class BaseAgent(ABC):
    """
    基础智能体类

    所有智能体必须继承此类并实现相关方法

    Attributes:
        name: 智能体名称
        config: 智能体配置
    """

    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        初始化智能体

        Args:
            name: 智能体名称
            config: 智能体配置
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"agent.{name}")

        self.logger.info(f"智能体初始化: {name}")

    @abstractmethod
    def observe(self, observation: AgentObservation) -> None:
        """
        接收观察

        Args:
            observation: 观察数据
        """
        pass

    @abstractmethod
    def decide(self) -> Optional[AgentAction]:
        """
        做出决策

        Returns:
            动作（可选）
        """
        pass

    @abstractmethod
    def receive_message(self, message: Dict) -> None:
        """
        接收消息

        Args:
            message: 消息内容
        """
        pass

    @abstractmethod
    def update(self, reward: float, next_observation: AgentObservation) -> None:
        """
        更新智能体

        Args:
            reward: 奖励
            next_observation: 下一时刻观察
        """
        pass


class TrendAgent(BaseAgent):
    """
    趋势跟踪智能体

    基于技术指标的趋势跟踪策略

    Attributes:
        ma_short: 短期均线周期
        ma_long: 长期均线周期
        data: 历史数据
    """

    def __init__(self, name: str = "trend_agent", config: Optional[Dict] = None):
        """
        初始化趋势智能体

        Args:
            name: 智能体名称
            config: 智能体配置
        """
        super().__init__(name, config)

        self.ma_short = self.config.get('ma_short', 5)
        self.ma_long = self.config.get('ma_long', 20)
        self.data: Dict[str, pd.DataFrame] = {}

    def observe(self, observation: AgentObservation) -> None:
        """
        接收观察

        Args:
            observation: 观察数据
        """
        stock_code = observation.stock_code

        if stock_code not in self.data:
            self.data[stock_code] = pd.DataFrame()

        # 添加新数据
        new_data = pd.DataFrame([{
            'date': observation.timestamp,
            'close': observation.price,
            'volume': observation.volume
        }])

        self.data[stock_code] = pd.concat([self.data[stock_code], new_data], ignore_index=True)

    def decide(self) -> Optional[AgentAction]:
        """
        做出决策

        Returns:
            动作（可选）
        """
        for stock_code, df in self.data.items():
            if len(df) < self.ma_long:
                continue

            # 计算均线
            df['ma_short'] = df['close'].rolling(self.ma_short).mean()
            df['ma_long'] = df['close'].rolling(self.ma_long).mean()

            # 金叉买入
            if df['ma_short'].iloc[-1] > df['ma_long'].iloc[-1] and \
               df['ma_short'].iloc[-2] <= df['ma_long'].iloc[-2]:
                return AgentAction(
                    stock_code=stock_code,
                    action_type='buy',
                    quantity=100,
                    confidence=0.8
                )

            # 死叉卖出
            if df['ma_short'].iloc[-1] < df['ma_long'].iloc[-1] and \
               df['ma_short'].iloc[-2] >= df['ma_long'].iloc[-2]:
                return AgentAction(
                    stock_code=stock_code,
                    action_type='sell',
                    quantity=100,
                    confidence=0.8
                )

        return None

    def receive_message(self, message: Dict) -> None:
        """
        接收消息

        Args:
            message: 消息内容
        """
        self.logger.info(f"接收消息: {message}")

    def update(self, reward: float, next_observation: AgentObservation) -> None:
        """
        更新智能体

        Args:
            reward: 奖励
            next_observation: 下一时刻观察
        """
        pass


class MomentumAgent(BaseAgent):
    """
    动量智能体

    基于动量效应的交易策略

    Attributes:
        momentum_period: 动量周期
        threshold: 动量阈值
        data: 历史数据
    """

    def __init__(self, name: str = "momentum_agent", config: Optional[Dict] = None):
        """
        初始化动量智能体

        Args:
            name: 智能体名称
            config: 智能体配置
        """
        super().__init__(name, config)

        self.momentum_period = self.config.get('momentum_period', 20)
        self.threshold = self.config.get('threshold', 0.05)
        self.data: Dict[str, pd.DataFrame] = {}

    def observe(self, observation: AgentObservation) -> None:
        """
        接收观察

        Args:
            observation: 观察数据
        """
        stock_code = observation.stock_code

        if stock_code not in self.data:
            self.data[stock_code] = pd.DataFrame()

        new_data = pd.DataFrame([{
            'date': observation.timestamp,
            'close': observation.price,
            'volume': observation.volume
        }])

        self.data[stock_code] = pd.concat([self.data[stock_code], new_data], ignore_index=True)

    def decide(self) -> Optional[AgentAction]:
        """
        做出决策

        Returns:
            动作（可选）
        """
        for stock_code, df in self.data.items():
            if len(df) < self.momentum_period + 1:
                continue

            # 计算动量
            returns = df['close'].pct_change(self.momentum_period).iloc[-1]

            if returns > self.threshold:
                return AgentAction(
                    stock_code=stock_code,
                    action_type='buy',
                    quantity=100,
                    confidence=min(returns / self.threshold, 1.0)
                )
            elif returns < -self.threshold:
                return AgentAction(
                    stock_code=stock_code,
                    action_type='sell',
                    quantity=100,
                    confidence=min(abs(returns) / self.threshold, 1.0)
                )

        return None

    def receive_message(self, message: Dict) -> None:
        """
        接收消息

        Args:
            message: 消息内容
        """
        self.logger.info(f"接收消息: {message}")

    def update(self, reward: float, next_observation: AgentObservation) -> None:
        """
        更新智能体

        Args:
            reward: 奖励
            next_observation: 下一时刻观察
        """
        pass


class RiskAgent(BaseAgent):
    """
    风控智能体

    负责风险管理的智能体

    Attributes:
        max_position: 最大仓位
        max_drawdown: 最大回撤
        current_position: 当前仓位
    """

    def __init__(self, name: str = "risk_agent", config: Optional[Dict] = None):
        """
        初始化风控智能体

        Args:
            name: 智能体名称
            config: 智能体配置
        """
        super().__init__(name, config)

        self.max_position = self.config.get('max_position', 0.3)
        self.max_drawdown = self.config.get('max_drawdown', 0.1)
        self.current_position = 0.0
        self.peak_value = 1.0

    def observe(self, observation: AgentObservation) -> None:
        """
        接收观察

        Args:
            observation: 观察数据
        """
        pass

    def decide(self) -> Optional[AgentAction]:
        """
        做出决策

        Returns:
            动作（可选）
        """
        # 检查最大回撤
        if self.peak_value > 0:
            drawdown = (self.peak_value - 1.0) / self.peak_value

            if drawdown >= self.max_drawdown:
                return AgentAction(
                    stock_code='ALL',
                    action_type='sell',
                    quantity=0,
                    confidence=1.0
                )

        return None

    def receive_message(self, message: Dict) -> None:
        """
        接收消息

        Args:
            message: 消息内容
        """
        if 'position' in message:
            self.current_position = message['position']

        if 'value' in message:
            self.peak_value = max(self.peak_value, message['value'])

    def update(self, reward: float, next_observation: AgentObservation) -> None:
        """
        更新智能体

        Args:
            reward: 奖励
            next_observation: 下一时刻观察
        """
        pass


class MultiAgentSystem:
    """
    多智能体系统

    协调多个智能体进行交易决策

    Attributes:
        agents: 智能体列表
        message_bus: 消息总线
    """

    def __init__(self, agent_configs: List[Dict] = None):
        """
        初始化多智能体系统

        Args:
            agent_configs: 智能体配置列表
        """
        self.agents: List[BaseAgent] = []
        self.message_bus: Dict[str, List[Dict]] = {}

        # 创建智能体
        for config in agent_configs or []:
            agent_type = config.get('type', 'trend')
            agent_name = config.get('name', f"agent_{len(self.agents)}")

            if agent_type == 'trend':
                agent = TrendAgent(agent_name, config)
            elif agent_type == 'momentum':
                agent = MomentumAgent(agent_name, config)
            elif agent_type == 'risk':
                agent = RiskAgent(agent_name, config)
            else:
                agent = BaseAgent(agent_name, config)

            self.agents.append(agent)
            self.message_bus[agent_name] = []

        logger.info(f"多智能体系统初始化完成，共 {len(self.agents)} 个智能体")

    def observe(self, observation: AgentObservation) -> None:
        """
        所有智能体接收观察

        Args:
            observation: 观察数据
        """
        for agent in self.agents:
            agent.observe(observation)

    def decide(self) -> List[AgentAction]:
        """
        所有智能体做出决策

        Returns:
            动作列表
        """
        actions = []

        for agent in self.agents:
            action = agent.decide()
            if action is not None:
                actions.append(action)

        return actions

    def aggregate_decisions(self, actions: List[AgentAction]) -> List[AgentAction]:
        """
        聚合智能体决策

        Args:
            actions: 动作列表

        Returns:
            聚合后的动作列表
        """
        # 简单聚合：合并所有买入和卖出信号
        buy_actions = [a for a in actions if a.action_type == 'buy']
        sell_actions = [a for a in actions if a.action_type == 'sell']

        # 如果有风控智能体的卖出信号，优先执行
        risk_sell_actions = [a for a in sell_actions if a.stock_code == 'ALL']

        if risk_sell_actions:
            return risk_sell_actions

        return actions

    def broadcast_message(self, message: Dict) -> None:
        """
        广播消息给所有智能体

        Args:
            message: 消息内容
        """
        for agent_name in self.message_bus.keys():
            self.message_bus[agent_name].append(message)

        for agent in self.agents:
            agent.receive_message(message)

    def update(self, rewards: Dict[str, float], observations: Dict[str, AgentObservation]) -> None:
        """
        更新所有智能体

        Args:
            rewards: 奖励字典
            observations: 观察字典
        """
        for agent in self.agents:
            reward = rewards.get(agent.name, 0.0)
            observation = observations.get(agent.name)
            if observation is not None:
                agent.update(reward, observation)

    def run(self, data: pd.DataFrame, initial_cash: float = 1000000.0) -> Dict:
        """
        运行多智能体系统

        Args:
            data: 数据
            initial_cash: 初始资金

        Returns:
            结果字典
        """
        logger.info("开始运行多智能体系统")

        # 初始化
        cash = initial_cash
        positions: Dict[str, int] = {}
        actions_history: List[AgentAction] = []
        portfolio_values: List[float] = []

        # 遍历数据
        for idx, row in data.iterrows():
            # 创建观察
            observation = AgentObservation(
                stock_code=row.get('code', '000001'),
                price=row.get('close', 0.0),
                volume=row.get('volume', 0),
                timestamp=row.get('date', datetime.now())
            )

            # 所有智能体接收观察
            self.observe(observation)

            # 智能体做出决策
            actions = self.decide()

            # 聚合决策
            aggregated_actions = self.aggregate_decisions(actions)

            # 执行动作
            for action in aggregated_actions:
                if action.action_type == 'buy':
                    cost = action.quantity * observation.price
                    if cash >= cost:
                        cash -= cost
                        positions[action.stock_code] = positions.get(action.stock_code, 0) + action.quantity
                        actions_history.append(action)

                elif action.action_type == 'sell':
                    if action.stock_code == 'ALL':
                        # 清仓
                        for stock_code, quantity in positions.items():
                            cash += quantity * observation.price
                            positions[stock_code] = 0
                            actions_history.append(action)
                    elif action.stock_code in positions:
                        quantity = min(action.quantity, positions[action.stock_code])
                        cash += quantity * observation.price
                        positions[action.stock_code] -= quantity
                        if positions[action.stock_code] == 0:
                            del positions[action.stock_code]
                        actions_history.append(action)

            # 计算投资组合价值
            portfolio_value = cash + sum(
                qty * observation.price for qty in positions.values()
            )
            portfolio_values.append(portfolio_value)

        logger.info("多智能体系统运行完成")

        return {
            'final_cash': cash,
            'final_positions': positions,
            'actions_history': actions_history,
            'portfolio_values': portfolio_values,
            'total_return': (portfolio_values[-1] - initial_cash) / initial_cash if portfolio_values else 0
        }


if __name__ == "__main__":
    # 测试多智能体系统
    print("=" * 60)
    print("测试多智能体系统")
    print("=" * 60)

    # 创建多智能体系统
    system = MultiAgentSystem(
        agent_configs=[
            {'name': 'trend_agent', 'type': 'trend', 'ma_short': 5, 'ma_long': 20},
            {'name': 'momentum_agent', 'type': 'momentum', 'momentum_period': 20},
            {'name': 'risk_agent', 'type': 'risk', 'max_drawdown': 0.1}
        ]
    )

    # 创建测试数据
    dates = pd.date_range(start='2023-01-01', periods=100, freq='B')
    np.random.seed(42)

    prices = 10 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
    data = pd.DataFrame({
        'date': dates,
        'code': '000001',
        'close': prices,
        'volume': np.random.randint(100000, 1000000, 100)
    })

    # 运行系统
    result = system.run(data)

    print(f"\n最终资金: {result['final_cash']:,.2f} 元")
    print(f"最终持仓: {result['final_positions']}")
    print(f"总收益: {result['total_return'] * 100:.2f}%")
    print(f"动作数量: {len(result['actions_history'])}")

    print("\n" + "=" * 60)
    print("多智能体系统测试完成！")
    print("=" * 60)
