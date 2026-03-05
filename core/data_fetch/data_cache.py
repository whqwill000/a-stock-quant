"""
数据缓存模块

提供数据缓存功能，减少重复请求，提高数据获取效率
支持本地文件缓存，可配置缓存过期时间

使用方法:
    from core.data_fetch.data_cache import DataCache
    
    cache = DataCache(cache_dir="data/cache", expire_hours=24)
    
    # 保存数据到缓存
    cache.set("stock_000001", data)
    
    # 从缓存获取数据
    data = cache.get("stock_000001")
"""

import os
import json
import pickle
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import pandas as pd

# 导入日志工具
from core.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class DataCache:
    """
    数据缓存类
    
    提供数据的缓存、获取、过期检查等功能
    支持多种数据格式：DataFrame、字典、列表等
    
    Attributes:
        cache_dir: 缓存目录
        expire_hours: 缓存过期时间（小时）
        enabled: 是否启用缓存
    """
    
    def __init__(
        self,
        cache_dir: str = "data/cache",
        expire_hours: int = 24,
        enabled: bool = True
    ):
        """
        初始化数据缓存
        
        Args:
            cache_dir: 缓存目录路径
            expire_hours: 缓存过期时间，默认 24 小时
            enabled: 是否启用缓存，默认启用
        """
        self.cache_dir = Path(cache_dir)
        self.expire_hours = expire_hours
        self.enabled = enabled
        
        # 创建缓存目录
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"数据缓存初始化完成，缓存目录: {self.cache_dir}")
    
    def _get_cache_path(self, key: str) -> Path:
        """
        获取缓存文件路径
        
        使用 MD5 哈希作为文件名，避免特殊字符问题
        
        Args:
            key: 缓存键
            
        Returns:
            缓存文件路径
        """
        # 对键进行哈希处理
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def _get_meta_path(self, key: str) -> Path:
        """
        获取缓存元数据文件路径
        
        Args:
            key: 缓存键
            
        Returns:
            元数据文件路径
        """
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.meta"
    
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据，如果不存在或已过期则返回 None
            
        Example:
            >>> cache = DataCache()
            >>> data = cache.get("stock_000001_20240101")
        """
        if not self.enabled:
            return None
        
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        # 检查缓存文件是否存在
        if not cache_path.exists():
            logger.debug(f"缓存不存在: {key}")
            return None
        
        # 检查是否过期
        if self._is_expired(meta_path):
            logger.debug(f"缓存已过期: {key}")
            self.delete(key)
            return None
        
        try:
            # 读取缓存数据
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            logger.debug(f"从缓存读取数据: {key}")
            return data
            
        except Exception as e:
            logger.warning(f"读取缓存失败: {key}, 错误: {e}")
            return None
    
    def set(
        self,
        key: str,
        data: Any,
        expire_hours: Optional[int] = None
    ) -> bool:
        """
        保存数据到缓存
        
        Args:
            key: 缓存键
            data: 要缓存的数据
            expire_hours: 过期时间（小时），如果为 None 则使用默认值
            
        Returns:
            是否保存成功
            
        Example:
            >>> cache = DataCache()
            >>> cache.set("stock_000001", df)
            True
        """
        if not self.enabled:
            return False
        
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        try:
            # 保存数据
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            # 保存元数据
            expire = expire_hours or self.expire_hours
            meta = {
                'key': key,
                'created_at': datetime.now().isoformat(),
                'expire_at': (datetime.now() + timedelta(hours=expire)).isoformat(),
                'expire_hours': expire
            }
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"数据已缓存: {key}")
            return True
            
        except Exception as e:
            logger.error(f"缓存数据失败: {key}, 错误: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        try:
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            
            logger.debug(f"缓存已删除: {key}")
            return True
            
        except Exception as e:
            logger.error(f"删除缓存失败: {key}, 错误: {e}")
            return False
    
    def clear(self) -> int:
        """
        清空所有缓存
        
        Returns:
            删除的缓存文件数量
        """
        count = 0
        
        try:
            for file in self.cache_dir.glob("*.cache"):
                file.unlink()
                count += 1
            
            for file in self.cache_dir.glob("*.meta"):
                file.unlink()
            
            logger.info(f"已清空 {count} 个缓存文件")
            return count
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return count
    
    def clear_expired(self) -> int:
        """
        清理过期缓存
        
        Returns:
            删除的过期缓存数量
        """
        count = 0
        
        try:
            for meta_file in self.cache_dir.glob("*.meta"):
                if self._is_expired(meta_file):
                    # 从元数据文件名推导缓存文件名
                    cache_file = meta_file.with_suffix('.cache')
                    
                    if cache_file.exists():
                        cache_file.unlink()
                    meta_file.unlink()
                    count += 1
            
            if count > 0:
                logger.info(f"已清理 {count} 个过期缓存")
            return count
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return count
    
    def _is_expired(self, meta_path: Path) -> bool:
        """
        检查缓存是否过期
        
        Args:
            meta_path: 元数据文件路径
            
        Returns:
            是否已过期
        """
        if not meta_path.exists():
            return True
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            expire_at = datetime.fromisoformat(meta['expire_at'])
            return datetime.now() > expire_at
            
        except Exception:
            return True
    
    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在且未过期
        
        Args:
            key: 缓存键
            
        Returns:
            缓存是否存在且有效
        """
        if not self.enabled:
            return False
        
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        if not cache_path.exists():
            return False
        
        return not self._is_expired(meta_path)
    
    def get_cache_info(self, key: str) -> Optional[Dict]:
        """
        获取缓存信息
        
        Args:
            key: 缓存键
            
        Returns:
            缓存信息字典，如果不存在则返回 None
        """
        meta_path = self._get_meta_path(key)
        
        if not meta_path.exists():
            return None
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total_files = 0
        total_size = 0
        expired_count = 0
        
        try:
            for file in self.cache_dir.glob("*.cache"):
                total_files += 1
                total_size += file.stat().st_size
            
            for meta_file in self.cache_dir.glob("*.meta"):
                if self._is_expired(meta_file):
                    expired_count += 1
            
            return {
                'total_files': total_files,
                'total_size_mb': total_size / (1024 * 1024),
                'expired_count': expired_count,
                'cache_dir': str(self.cache_dir),
                'enabled': self.enabled,
                'expire_hours': self.expire_hours
            }
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}


class DataFrameCache(DataCache):
    """
    DataFrame 专用缓存类
    
    针对 DataFrame 数据进行优化，支持 CSV 和 Parquet 格式存储
    """
    
    def __init__(
        self,
        cache_dir: str = "data/cache",
        expire_hours: int = 24,
        enabled: bool = True,
        format: str = "parquet"
    ):
        """
        初始化 DataFrame 缓存
        
        Args:
            cache_dir: 缓存目录
            expire_hours: 过期时间
            enabled: 是否启用
            format: 存储格式，可选 "parquet" 或 "csv"
        """
        super().__init__(cache_dir, expire_hours, enabled)
        self.format = format
    
    def _get_cache_path(self, key: str) -> Path:
        """
        获取缓存文件路径（重写以支持不同格式）
        """
        key_hash = hashlib.md5(key.encode()).hexdigest()
        suffix = ".parquet" if self.format == "parquet" else ".csv"
        return self.cache_dir / f"{key_hash}{suffix}"
    
    def get(self, key: str) -> Optional[pd.DataFrame]:
        """
        从缓存获取 DataFrame
        
        Args:
            key: 缓存键
            
        Returns:
            DataFrame 或 None
        """
        if not self.enabled:
            return None
        
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        if not cache_path.exists():
            return None
        
        if self._is_expired(meta_path):
            self.delete(key)
            return None
        
        try:
            if self.format == "parquet":
                df = pd.read_parquet(cache_path)
            else:
                df = pd.read_csv(cache_path)
            
            logger.debug(f"从缓存读取 DataFrame: {key}, 形状: {df.shape}")
            return df
            
        except Exception as e:
            logger.warning(f"读取 DataFrame 缓存失败: {key}, 错误: {e}")
            return None
    
    def set(
        self,
        key: str,
        data: pd.DataFrame,
        expire_hours: Optional[int] = None
    ) -> bool:
        """
        保存 DataFrame 到缓存
        
        Args:
            key: 缓存键
            data: DataFrame 数据
            expire_hours: 过期时间
            
        Returns:
            是否成功
        """
        if not self.enabled:
            return False
        
        if not isinstance(data, pd.DataFrame):
            logger.warning(f"数据类型不是 DataFrame: {type(data)}")
            return False
        
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        try:
            if self.format == "parquet":
                data.to_parquet(cache_path, index=False)
            else:
                data.to_csv(cache_path, index=False)
            
            # 保存元数据
            expire = expire_hours or self.expire_hours
            meta = {
                'key': key,
                'created_at': datetime.now().isoformat(),
                'expire_at': (datetime.now() + timedelta(hours=expire)).isoformat(),
                'expire_hours': expire,
                'shape': list(data.shape),
                'columns': list(data.columns)
            }
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"DataFrame 已缓存: {key}, 形状: {data.shape}")
            return True
            
        except Exception as e:
            logger.error(f"缓存 DataFrame 失败: {key}, 错误: {e}")
            return False


if __name__ == "__main__":
    # 测试缓存模块
    print("=" * 60)
    print("测试数据缓存模块")
    print("=" * 60)
    
    # 创建缓存实例
    cache = DataCache(cache_dir="data/cache/test", expire_hours=1)
    
    # 测试基本功能
    print("\n【测试基本缓存功能】")
    test_data = {"name": "测试数据", "value": [1, 2, 3, 4, 5]}
    
    # 保存数据
    cache.set("test_key", test_data)
    print(f"数据已保存: {test_data}")
    
    # 读取数据
    retrieved = cache.get("test_key")
    print(f"数据已读取: {retrieved}")
    
    # 检查是否存在
    print(f"缓存是否存在: {cache.exists('test_key')}")
    
    # 获取缓存信息
    info = cache.get_cache_info("test_key")
    print(f"缓存信息: {info}")
    
    # 获取统计信息
    stats = cache.get_stats()
    print(f"缓存统计: {stats}")
    
    # 测试 DataFrame 缓存
    print("\n【测试 DataFrame 缓存】")
    df_cache = DataFrameCache(cache_dir="data/cache/test_df", format="parquet")
    
    test_df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5),
        'close': [10.0, 10.5, 11.0, 10.8, 11.2],
        'volume': [1000, 1200, 1100, 1300, 1500]
    })
    
    df_cache.set("test_df", test_df)
    print(f"DataFrame 已保存，形状: {test_df.shape}")
    
    retrieved_df = df_cache.get("test_df")
    print(f"DataFrame 已读取，形状: {retrieved_df.shape}")
    print(retrieved_df.head())
    
    # 清理测试缓存
    print("\n【清理测试缓存】")
    cache.clear()
    df_cache.clear()
    
    print("\n" + "=" * 60)
    print("数据缓存模块测试完成！")
    print("=" * 60)