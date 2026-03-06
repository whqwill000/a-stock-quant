"""
iTransformer 模型

反转Transformer架构的时间序列预测模型

核心思想：
- 反转Transformer结构
- 在变量维度上做自注意力
- 更好地捕捉多变量间的相关性

论文: ICLR 2024 - iTransformer
"""

from core.ts_models.base import BaseModel


class iTransformerModel(BaseModel):
    """
    iTransformer 模型

    反转Transformer架构的时间序列预测模型

    核心思想：
    - 反转Transformer结构
    - 在变量维度上做自注意力
    - 更好地捕捉多变量间的相关性

    论文: ICLR 2024 - iTransformer
    """

    def __init__(
        self,
        input_len: int = 96,
        output_len: int = 24,
        hidden_dim: int = 256,
        num_layers: int = 3,
        n_heads: int = 8,
        dropout: float = 0.1
    ):
        """
        初始化iTransformer模型

        Args:
            input_len: 输入长度
            output_len: 输出长度
            hidden_dim: 隐藏层维度
            num_layers: 网络层数
            n_heads: 注意力头数
            dropout: Dropout率
        """
        super().__init__(input_len, output_len, hidden_dim, num_layers, dropout, "iTransformer")

        self.n_heads = n_heads

    def fit(self, X, y=None):
        """训练模型"""
        pass

    def predict(self, X):
        """预测"""
        pass

    def save(self, path):
        """保存模型"""
        pass

    def load(self, path):
        """加载模型"""
        pass
