#!/usr/bin/env python3
"""
环境检查脚本

检查 Python 环境、依赖包、配置等是否满足要求
"""

import sys
import subprocess
from pathlib import Path


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_python_version():
    """检查 Python 版本"""
    print_header("Python 版本检查")
    version = sys.version_info
    print(f"Python 版本：{version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Python 版本过低，需要 3.10 或更高版本")
        return False
    else:
        print("✅ Python 版本满足要求")
        return True


def check_packages():
    """检查依赖包"""
    print_header("依赖包检查")
    
    required_packages = {
        "pandas": "数据处理",
        "numpy": "数值计算",
        "matplotlib": "数据可视化",
        "akshare": "A 股数据获取",
        "yaml": "配置管理",
    }
    
    missing = []
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✅ {package} ({description}) - 已安装")
        except ImportError:
            print(f"❌ {package} ({description}) - 未安装")
            missing.append(package)
    
    if missing:
        print(f"\n需要安装的包：{', '.join(missing)}")
        print("运行：pip install -r requirements.txt")
        return False
    else:
        print("\n✅ 所有依赖包已安装")
        return True


def check_directories():
    """检查目录结构"""
    print_header("目录结构检查")
    
    required_dirs = [
        "core",
        "strategies",
        "docs",
        "notebooks",
        "data",
        "tests",
    ]
    
    project_root = Path(__file__).parent.parent
    missing = []
    
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"✅ {dir_name}/ - 存在")
        else:
            print(f"❌ {dir_name}/ - 不存在")
            missing.append(dir_name)
    
    if missing:
        print(f"\n缺少目录：{', '.join(missing)}")
        return False
    else:
        print("\n✅ 目录结构完整")
        return True


def check_data_source():
    """检查数据源"""
    print_header("数据源检查")
    
    try:
        import akshare as ak
        # 尝试获取少量数据测试
        stock_info = ak.stock_info_a_code_name()
        print("✅ AKShare 数据源可用")
        return True
    except Exception as e:
        print(f"❌ AKShare 数据源不可用：{e}")
        print("请检查网络连接")
        return False


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "A 股量化平台 - 环境检查" + " " * 15 + "║")
    print("╚" + "=" * 58 + "╝")
    
    results = []
    
    results.append(("Python 版本", check_python_version()))
    results.append(("依赖包", check_packages()))
    results.append(("目录结构", check_directories()))
    results.append(("数据源", check_data_source()))
    
    # 总结
    print_header("检查总结")
    
    all_passed = all(result[1] for result in results)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    print()
    if all_passed:
        print("🎉 所有检查通过！环境配置正确。")
        print("\n下一步:")
        print("  1. 阅读 docs/05-快速开始.md")
        print("  2. 运行第一个策略回测")
    else:
        print("⚠️  部分检查未通过，请先修复问题。")
        print("\n建议:")
        print("  1. 安装缺失的依赖：pip install -r requirements.txt")
        print("  2. 检查目录结构是否完整")
        print("  3. 检查网络连接")
    
    print()


if __name__ == "__main__":
    main()
