#!/usr/bin/env python3
"""
Python环境检测脚本
检测Python版本、路径、以及Playwright安装状态
"""

import sys
import os
import subprocess
from pathlib import Path

def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_python_version():
    """检查Python版本"""
    print_section("Python 版本信息")
    print(f"Python 版本: {sys.version}")
    print(f"Python 可执行文件路径: {sys.executable}")
    print(f"Python 版本号: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # 检查是否满足最低版本要求（Python 3.7+）
    if sys.version_info >= (3, 7):
        print("✅ Python 版本符合要求 (>= 3.7)")
    else:
        print("❌ Python 版本过低，建议升级到 3.7 或更高版本")

def check_pip():
    """检查pip安装状态"""
    print_section("pip 信息")
    try:
        import pip
        print(f"✅ pip 已安装")
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                              capture_output=True, text=True)
        print(f"pip 版本: {result.stdout.strip()}")
    except ImportError:
        print("❌ pip 未安装")

def check_playwright():
    """检查Playwright安装状态"""
    print_section("Playwright 安装状态")
    try:
        import playwright
        print(f"✅ Playwright 已安装")
        # Playwright 没有 __version__ 属性，使用 importlib.metadata 获取版本
        try:
            from importlib.metadata import version
            pw_version = version("playwright")
            print(f"Playwright 版本: {pw_version}")
        except Exception:
            print(f"Playwright 版本: 无法获取")
        print(f"Playwright 安装路径: {playwright.__file__}")
        
        # 检查浏览器是否已安装
        print("\n检查 Playwright 浏览器...")
        try:
            result = subprocess.run([sys.executable, "-m", "playwright", "install", "--dry-run"],
                                  capture_output=True, text=True, timeout=10)
            if "chromium" in result.stdout.lower() or "chrome" in result.stdout.lower():
                print("ℹ️  浏览器可能需要安装，运行: python -m playwright install chromium")
            else:
                print("✅ 浏览器已安装")
        except subprocess.TimeoutExpired:
            print("⚠️  检测超时，请手动运行: python -m playwright install --dry-run")
        except Exception as e:
            print(f"⚠️  无法检测浏览器状态: {e}")
            
    except ImportError:
        print("❌ Playwright 未安装")
        print("\n安装命令:")
        print("  pip install playwright")
        print("  python -m playwright install chromium")

def check_environment_paths():
    """检查环境路径"""
    print_section("环境路径信息")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"HOME 目录: {Path.home()}")
    print(f"系统 PATH 环境变量:")
    for path in os.environ.get('PATH', '').split(os.pathsep):
        if path:  # 跳过空路径
            print(f"  - {path}")

def check_system_info():
    """检查系统信息"""
    print_section("系统信息")
    print(f"操作系统: {sys.platform}")
    print(f"Python 实现: {sys.implementation.name}")
    
    # 检查是否在WSL中
    if sys.platform == "linux":
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read()
                if 'microsoft' in version_info.lower() or 'wsl' in version_info.lower():
                    print("🐧 运行环境: WSL (Windows Subsystem for Linux)")
                else:
                    print("🐧 运行环境: 原生 Linux")
        except:
            print("🐧 运行环境: Linux")
    elif sys.platform == "win32":
        print("🪟 运行环境: Windows")
    elif sys.platform == "darwin":
        print("🍎 运行环境: macOS")

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  Python & Playwright 环境检测工具")
    print("=" * 60)
    
    check_system_info()
    check_python_version()
    check_pip()
    check_playwright()
    check_environment_paths()
    
    print("\n" + "=" * 60)
    print("  检测完成！")
    print("=" * 60)
    
    # 给出建议
    print("\n📋 下一步建议:")
    try:
        import playwright
        print("✅ 环境已就绪，可以开始编写自动化脚本")
    except ImportError:
        print("❌ 请先安装 Playwright:")
        print("   pip install playwright")
        print("   python -m playwright install chromium")

if __name__ == "__main__":
    main()