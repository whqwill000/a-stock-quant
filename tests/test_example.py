"""
测试用例示例

用法:
    pytest tests/
    pytest tests/ -v
    pytest tests/ --cov=core
"""

import pytest


def test_example():
    """示例测试"""
    assert 1 + 1 == 2


class TestExample:
    """示例测试类"""
    
    def test_addition(self):
        """测试加法"""
        assert 2 + 2 == 4
    
    def test_subtraction(self):
        """测试减法"""
        assert 5 - 3 == 2
