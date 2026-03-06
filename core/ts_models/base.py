"""
基础时间序列模型类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging


@dataclass
class ModelConfig:
    """
    模型配置数据类
    """

    input_len: int = 96
    output_len: int = 24
    hidden_dim: int = 256
    num_layers: int = 3
    dropout: float = 0.1
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100


class BaseModel(ABC):
    """
    基础时间序列模型类

    所有时间序列模型必须继承此类
    """

    def __init__(
        self,
        input_len: int,
        output_len: int,
        hidden_dim: int,
        num_layers: int,
        dropout: float,
        name: str
    ):
        """
        初始化模型

        Args:
            input_len: 输入长度
            output_len: 输出长度
            hidden_dim: 隐藏层维度
            num_layers: 网络层数
            dropout: Dropout率
            name: 模型名称
        """
        self.config = ModelConfig(
            input_len=input_len,
            output_len=output_len,
            hidden_dim=hidden_dim,
            num_layers=num_layers,
            dropout=dropout
        )
        self.name = name
        self.logger = logging.getLogger(f"ts_model.{name}")
        self.is_fitted = False

    @abstractmethod
    def fit(self, X, y=None):
        """训练模型"""
        pass

    @abstractmethod
    def predict(self, X):
        """预测"""
        pass

    @abstractmethod
    def save(self, path):
        """保存模型"""
        pass

    @abstractmethod
    def load(self, path):
        """加载模型"""
        pass
