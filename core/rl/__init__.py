"""
多智能体强化学习模块

提供多智能体强化学习算法，用于量化交易
"""

from .multi_agent import (
    BaseAgent,
    TrendAgent,
    MomentumAgent,
    RiskAgent,
    MultiAgentSystem,
    AgentObservation,
    AgentAction
)

__all__ = [
    'BaseAgent',
    'TrendAgent',
    'MomentumAgent',
    'RiskAgent',
    'MultiAgentSystem',
    'AgentObservation',
    'AgentAction'
]
