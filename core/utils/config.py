"""
配置管理模块

提供统一的配置管理功能，支持 YAML 配置文件的加载、保存和访问
支持配置的层级访问、默认值设置、配置验证等功能

使用方法:
    from core.utils.config import ConfigManager
    
    # 加载配置
    config = ConfigManager.load("config/default.yaml")
    
    # 访问配置
    value = config.get("data.cache.enabled", default=True)
    
    # 设置配置
    config.set("data.cache.enabled", False)
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml
from dataclasses import dataclass, field


@dataclass
class Config:
    """
    配置数据类
    
    存储配置信息，支持字典式访问和属性访问
    
    Attributes:
        data: 配置数据字典
        file_path: 配置文件路径
    """
    
    data: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持层级访问
        
        Args:
            key: 配置键，支持点号分隔的层级访问，如 "data.cache.enabled"
            default: 默认值，当键不存在时返回
            
        Returns:
            配置值
            
        Example:
            >>> config.get("data.cache.enabled", default=True)
            True
        """
        # 将键按点号分割
        keys = key.split(".")
        value = self.data
        
        # 逐层访问
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值，支持层级设置
        
        Args:
            key: 配置键，支持点号分隔的层级设置
            value: 配置值
            
        Example:
            >>> config.set("data.cache.enabled", False)
        """
        keys = key.split(".")
        data = self.data
        
        # 逐层创建字典
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        
        # 设置最终值
        data[keys[-1]] = value
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        批量更新配置
        
        Args:
            data: 要更新的配置字典
        """
        self._deep_update(self.data, data)
    
    def _deep_update(self, target: dict, source: dict) -> None:
        """
        深度更新字典
        
        Args:
            target: 目标字典
            source: 源字典
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def save(self, file_path: Optional[str] = None) -> None:
        """
        保存配置到文件
        
        Args:
            file_path: 文件路径，如果为 None 则使用加载时的路径
        """
        path = file_path or self.file_path
        if path is None:
            raise ValueError("未指定保存路径")
        
        # 确保目录存在
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self.data, f, allow_unicode=True, default_flow_style=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            配置数据的字典副本
        """
        return self.data.copy()
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典式设置"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return self.get(key) is not None


class ConfigManager:
    """
    配置管理器
    
    提供配置的加载、保存、缓存和管理功能
    支持多个配置文件的管理，支持环境变量覆盖
    
    Example:
        >>> # 加载配置
        >>> config = ConfigManager.load("config/default.yaml")
        >>> 
        >>> # 访问配置
        >>> cache_enabled = config.get("data.cache.enabled", default=True)
        >>> 
        >>> # 修改配置
        >>> config.set("data.cache.enabled", False)
        >>> config.save()
    """
    
    # 配置缓存
    _configs: Dict[str, Config] = {}
    
    # 默认配置目录
    DEFAULT_CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
    
    @classmethod
    def load(
        cls,
        file_path: str,
        use_cache: bool = True,
        merge_env: bool = True
    ) -> Config:
        """
        加载配置文件
        
        Args:
            file_path: 配置文件路径，可以是相对路径或绝对路径
            use_cache: 是否使用缓存，如果为 True 则返回已缓存的配置
            merge_env: 是否合并环境变量
            
        Returns:
            配置对象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 解析错误
            
        Example:
            >>> config = ConfigManager.load("config/default.yaml")
        """
        # 转换为绝对路径
        path = Path(file_path)
        if not path.is_absolute():
            path = cls.DEFAULT_CONFIG_DIR / path
        
        path_str = str(path)
        
        # 检查缓存
        if use_cache and path_str in cls._configs:
            return cls._configs[path_str]
        
        # 检查文件是否存在
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        
        # 读取 YAML 文件
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        # 创建配置对象
        config = Config(data=data, file_path=path_str)
        
        # 合并环境变量
        if merge_env:
            cls._merge_env_vars(config)
        
        # 缓存配置
        if use_cache:
            cls._configs[path_str] = config
        
        return config
    
    @classmethod
    def _merge_env_vars(cls, config: Config, prefix: str = "A_STOCK_") -> None:
        """
        合并环境变量到配置
        
        环境变量格式：A_STOCK_SECTION_KEY=value
        例如：A_STOCK_DATA_CACHE_ENABLED=false
        
        Args:
            config: 配置对象
            prefix: 环境变量前缀
        """
        for key, value in os.environ.items():
            # 检查前缀
            if not key.startswith(prefix):
                continue
            
            # 解析配置键
            config_key = key[len(prefix):].lower().replace("_", ".")
            
            # 转换值类型
            parsed_value = cls._parse_env_value(value)
            
            # 设置配置
            config.set(config_key, parsed_value)
    
    @classmethod
    def _parse_env_value(cls, value: str) -> Any:
        """
        解析环境变量值
        
        Args:
            value: 环境变量字符串值
            
        Returns:
            解析后的值（可能是 bool、int、float 或 str）
        """
        # 布尔值
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # 整数
        try:
            return int(value)
        except ValueError:
            pass
        
        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 字符串
        return value
    
    @classmethod
    def save(cls, config: Config, file_path: Optional[str] = None) -> None:
        """
        保存配置到文件
        
        Args:
            config: 配置对象
            file_path: 文件路径，如果为 None 则使用配置对象的路径
        """
        config.save(file_path)
    
    @classmethod
    def get_cached(cls, file_path: str) -> Optional[Config]:
        """
        获取缓存的配置
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            缓存的配置对象，如果不存在则返回 None
        """
        path = str(Path(file_path).resolve())
        return cls._configs.get(path)
    
    @classmethod
    def clear_cache(cls) -> None:
        """清空配置缓存"""
        cls._configs.clear()
    
    @classmethod
    def merge_configs(cls, *configs: Config) -> Config:
        """
        合并多个配置
        
        后面的配置会覆盖前面的配置
        
        Args:
            *configs: 要合并的配置对象
            
        Returns:
            合并后的新配置对象
        """
        merged_data = {}
        
        for config in configs:
            cls._deep_update(merged_data, config.data)
        
        return Config(data=merged_data)
    
    @staticmethod
    def _deep_update(target: dict, source: dict) -> None:
        """
        深度更新字典
        
        Args:
            target: 目标字典
            source: 源字典
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                ConfigManager._deep_update(target[key], value)
            else:
                target[key] = value


def get_config(key: str = "default") -> Config:
    """
    获取配置的便捷函数
    
    Args:
        key: 配置键，默认为 "default"
        
    Returns:
        配置对象
    """
    # 尝试加载默认配置
    config_path = ConfigManager.DEFAULT_CONFIG_DIR / "default.yaml"
    
    if config_path.exists():
        return ConfigManager.load(str(config_path))
    
    # 返回空配置
    return Config()


if __name__ == "__main__":
    # 测试配置管理
    print("测试配置管理模块...")
    
    # 创建测试配置
    config = Config({
        "app": {
            "name": "A 股量化平台",
            "version": "0.1.0"
        },
        "data": {
            "cache": {
                "enabled": True,
                "expire_hours": 24
            }
        }
    })
    
    # 测试获取配置
    print(f"应用名称: {config.get('app.name')}")
    print(f"缓存启用: {config.get('data.cache.enabled')}")
    print(f"不存在的键: {config.get('not.exist', default='默认值')}")
    
    # 测试设置配置
    config.set("data.cache.enabled", False)
    print(f"修改后缓存启用: {config.get('data.cache.enabled')}")
    
    # 测试字典式访问
    print(f"字典式访问: {config['app']['name']}")
    
    print("\n配置管理模块测试完成！")