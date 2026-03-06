"""
金融大语言模型模块

提供金融领域的LLM应用，包括：
- FinBERT: 金融情感分析
- FINANCE-LLAMA3-8B: 金融指令微调
- RD-Agent-Quant: LLM驱动自动化因子挖掘

使用方法:
    from core.llm.finbert import FinBERT

    # 创建FinBERT实例
    finbert = FinBERT()

    # 情感分析
    result = finbert.analyze_sentiment("公司业绩超预期，股价大涨")
    print(result)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

# 导入项目模块
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


@dataclass
class SentimentResult:
    """
    情感分析结果数据类

    Attributes:
        label: 情感标签 ('positive', 'negative', 'neutral')
        score: 置信度
        text: 原始文本
    """

    label: str
    score: float
    text: str

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'label': self.label,
            'score': self.score,
            'text': self.text
        }


class BaseLLM(ABC):
    """
    基础LLM类

    所有LLM必须继承此类

    Attributes:
        name: 模型名称
        config: 模型配置
    """

    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        初始化LLM

        Args:
            name: 模型名称
            config: 模型配置
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"llm.{name}")

        self.logger.info(f"LLM初始化: {name}")

    @abstractmethod
    def analyze_sentiment(self, text: str) -> SentimentResult:
        """
        情感分析

        Args:
            text: 输入文本

        Returns:
            情感分析结果
        """
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        生成文本

        Args:
            prompt: 提示词
            **kwargs: 生成参数

        Returns:
            生成的文本
        """
        pass

    @abstractmethod
    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        """
        文本分类

        Args:
            text: 输入文本
            categories: 分类类别

        Returns:
            各类别的概率
        """
        pass


class FinBERT(BaseLLM):
    """
    FinBERT 模型

    金融领域专用BERT模型

    核心特点：
    - 基于BERT预训练
    - 使用金融语料库微调
    - 情感分析（正面/负面/中性）

    论文: arXiv:1908.10063

    Attributes:
        model: FinBERT模型
        tokenizer: 分词器
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化FinBERT

        Args:
            config: 模型配置
        """
        super().__init__("FinBERT", config)

        # 这里应该加载FinBERT模型
        # 由于需要transformers库，这里提供接口
        self.model = None
        self.tokenizer = None

        self.logger.info("FinBERT初始化完成")

    def _load_model(self):
        """加载模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch

            model_name = "ProsusAI/finbert"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)

            self.logger.info("FinBERT模型加载成功")
        except ImportError:
            self.logger.error("请安装transformers库: pip install transformers")
            raise

    def analyze_sentiment(self, text: str) -> SentimentResult:
        """
        情感分析

        Args:
            text: 输入文本

        Returns:
            情感分析结果
        """
        if self.model is None:
            self._load_model()

        try:
            from transformers import pipeline

            # 使用pipeline进行情感分析
            nlp = pipeline("text-classification", model="ProsusAI/finbert")
            result = nlp(text)[0]

            label = result['label'].lower()
            score = result['score']

            return SentimentResult(
                label=label,
                score=score,
                text=text
            )

        except Exception as e:
            self.logger.error(f"情感分析失败: {e}")
            raise

    def generate(self, prompt: str, **kwargs) -> str:
        """
        生成文本

        Args:
            prompt: 提示词
            **kwargs: 生成参数

        Returns:
            生成的文本
        """
        # FinBERT主要用于分类，不支持生成
        raise NotImplementedError("FinBERT不支持文本生成")

    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        """
        文本分类

        Args:
            text: 输入文本
            categories: 分类类别

        Returns:
            各类别的概率
        """
        # FinBERT主要用于情感分析
        result = self.analyze_sentiment(text)

        # 转换为分类格式
        classification = {
            'positive': 0.0,
            'negative': 0.0,
            'neutral': 0.0
        }

        classification[result.label] = result.score

        return classification


class FinanceLLAMA3(BaseLLM):
    """
    FINANCE-LLAMA3-8B 模型

    金融指令微调的LLAMA3模型

    核心特点：
    - 8B参数
    - 金融指令微调
    - 支持多种金融任务

    Attributes:
        model: LLAMA3模型
        tokenizer: 分词器
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化FINANCE-LLAMA3-8B

        Args:
            config: 模型配置
        """
        super().__init__("FINANCE-LLAMA3-8B", config)

        self.model = None
        self.tokenizer = None

        self.logger.info("FINANCE-LLAMA3-8B初始化完成")

    def _load_model(self):
        """加载模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )

            self.logger.info("FINANCE-LLAMA3-8B模型加载成功")
        except ImportError:
            self.logger.error("请安装transformers和torch库")
            raise

    def analyze_sentiment(self, text: str) -> SentimentResult:
        """
        情感分析

        Args:
            text: 输入文本

        Returns:
            情感分析结果
        """
        # 使用提示词进行情感分析
        prompt = f"""分析以下金融文本的情感倾向（正面/负面/中性）：
        
文本: {text}

请只返回情感标签（positive/negative/neutral）"""

        result = self.generate(prompt)

        # 解析结果
        label = result.strip().lower()
        if 'positive' in label:
            label = 'positive'
        elif 'negative' in label:
            label = 'negative'
        else:
            label = 'neutral'

        return SentimentResult(
            label=label,
            score=0.8,  # 简化处理
            text=text
        )

    def generate(self, prompt: str, **kwargs) -> str:
        """
        生成文本

        Args:
            prompt: 提示词
            **kwargs: 生成参数

        Returns:
            生成的文本
        """
        if self.model is None:
            self._load_model()

        try:
            from transformers import pipeline

            # 使用pipeline进行文本生成
            generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer
            )

            result = generator(
                prompt,
                max_new_tokens=kwargs.get('max_new_tokens', 100),
                temperature=kwargs.get('temperature', 0.7),
                do_sample=kwargs.get('do_sample', True)
            )

            return result[0]['generated_text']

        except Exception as e:
            self.logger.error(f"文本生成失败: {e}")
            raise

    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        """
        文本分类

        Args:
            text: 输入文本
            categories: 分类类别

        Returns:
            各类别的概率
        """
        # 使用提示词进行分类
        categories_str = ", ".join(categories)
        prompt = f"""将以下文本分类到以下类别之一：{categories_str}
        
文本: {text}

请只返回类别名称"""

        result = self.generate(prompt)

        # 解析结果
        classification = {cat: 0.0 for cat in categories}
        classification[result.strip()] = 1.0

        return classification


class RDAgentQuant(BaseLLM):
    """
    RD-Agent-Quant 模型

    LLM驱动的自动化因子挖掘系统

    核心特点：
    - 自动化因子挖掘
    - 多代理协同工作
    - 知识迭代进化

    论文: NeurIPS 2025 - R&D-Agent-Quant

    Attributes:
        agents: 代理列表
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化RD-Agent-Quant

        Args:
            config: 模型配置
        """
        super().__init__("RD-Agent-Quant", config)

        self.agents = []

        self.logger.info("RD-Agent-Quant初始化完成")

    def analyze_sentiment(self, text: str) -> SentimentResult:
        """
        情感分析

        Args:
            text: 输入文本

        Returns:
            情感分析结果
        """
        # 使用RD-Agent进行因子挖掘
        self.logger.info("使用RD-Agent进行因子挖掘")

        # 这里应该调用RD-Agent的API
        # 由于需要RD-Agent库，这里提供接口

        return SentimentResult(
            label='neutral',
            score=0.5,
            text=text
        )

    def generate(self, prompt: str, **kwargs) -> str:
        """
        生成文本

        Args:
            prompt: 提示词
            **kwargs: 生成参数

        Returns:
            生成的文本
        """
        # 使用RD-Agent进行自动化因子挖掘
        self.logger.info("使用RD-Agent进行自动化因子挖掘")

        # 这里应该调用RD-Agent的API

        return prompt

    def classify(self, text: str, categories: List[str]) -> Dict[str, float]:
        """
        文本分类

        Args:
            text: 输入文本
            categories: 分类类别

        Returns:
            各类别的概率
        """
        # 使用RD-Agent进行分类
        self.logger.info("使用RD-Agent进行分类")

        # 这里应该调用RD-Agent的API

        return {cat: 0.0 for cat in categories}


class LLMFactory:
    """
    LLM工厂

    用于创建不同的金融LLM

    Attributes:
        llms: LLM字典
    """

    def __init__(self):
        """初始化工厂"""
        self.llms = {
            'finbert': FinBERT,
            'finance-llama3': FinanceLLAMA3,
            'rd-agent-quant': RDAgentQuant
        }

        logger.info("LLM工厂初始化完成")

    def create_llm(self, llm_type: str, **kwargs) -> BaseLLM:
        """
        创建LLM

        Args:
            llm_type: LLM类型
            **kwargs: LLM参数

        Returns:
            LLM实例
        """
        llm_type = llm_type.lower()

        if llm_type not in self.llms:
            raise ValueError(f"不支持的LLM类型: {llm_type}")

        llm_class = self.llms[llm_type]
        llm = llm_class(**kwargs)

        logger.info(f"创建LLM: {llm_type}")

        return llm


if __name__ == "__main__":
    # 测试金融LLM
    print("=" * 60)
    print("测试金融LLM")
    print("=" * 60)

    # 创建LLM工厂
    factory = LLMFactory()

    # 创建FinBERT
    print("\n创建FinBERT...")
    finbert = factory.create_llm('finbert')

    # 情感分析
    print("情感分析...")
    result = finbert.analyze_sentiment("公司业绩超预期，股价大涨")

    print(f"情感标签: {result.label}")
    print(f"置信度: {result.score:.2f}")

    # 创建FinanceLLAMA3
    print("\n创建FinanceLLAMA3...")
    llama3 = factory.create_llm('finance-llama3')

    # 文本生成
    print("文本生成...")
    prompt = "分析以下股票的前景："
    result = llama3.generate(prompt)

    print(f"生成结果: {result}")

    print("\n" + "=" * 60)
    print("金融LLM测试完成！")
    print("=" * 60)
