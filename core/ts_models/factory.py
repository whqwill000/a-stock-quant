"""
时间序列模型工厂

用于创建不同的时间序列预测模型
"""

from core.ts_models.patchtst import PatchTSTModel
from core.ts_models.timesnet import TimesNetModel
from core.ts_models.itransformer import iTransformerModel


class TimeSeriesModelFactory:
    """
    时间序列模型工厂

    用于创建不同的时间序列预测模型

    Attributes:
        models: 模型字典
    """

    def __init__(self):
        """初始化工厂"""
        self.models = {
            'patchtst': PatchTSTModel,
            'timesnet': TimesNetModel,
            'itransformer': iTransformerModel
        }

    def create_model(self, model_type: str, **kwargs) -> 'BaseModel':
        """
        创建模型

        Args:
            model_type: 模型类型
            **kwargs: 模型参数

        Returns:
            模型实例
        """
        model_type = model_type.lower()

        if model_type not in self.models:
            raise ValueError(f"不支持的模型类型: {model_type}")

        model_class = self.models[model_type]
        model = model_class(**kwargs)

        return model
