import os
import time
import logging
from nodes import *


import sys


class PrintInfo:
    def __init__(self):
        print("开始检测 ComfyUI 环境...")
        check_python_version()
        check_pip_version()
        check_network_connection()
        check_sdk_installation()
        check_comfyui_environment()
        print("检测完成。")

    def check_python_version(self):
        print("\n检查 Python 版本...")
        version = sys.version
        print(f"当前 Python 版本: {version}")
        if sys.version_info.major != 3 or sys.version_info.minor < 8:
            print("警告: ComfyUI 推荐使用 Python 3.8 或更高版本。")
        else:
            print("Python 版本符合要求。")

    def check_pip_version():
        print("\n检查 pip 版本...")
        try:
            result = subprocess.run(["pip", "--version"], capture_output=True, text=True)
            print(result.stdout.strip())
        except Exception as e:
            print(f"无法检测 pip 版本: {e}")

    def check_network_connection():
        print("\n检查网络连接...")
        test_urls = [
            "https://pypi.org",
            "https://pypi.tuna.tsinghua.edu.cn",
            "https://github.com"
        ]
        for url in test_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"可以访问 {url}")
                else:
                    print(f"无法访问 {url} (状态码: {response.status_code})")
            except requests.RequestException as e:
                print(f"无法访问 {url}: {e}")

    def check_sdk_installation():
        print("\n检查 SDK 安装情况...")
        try:
            import qcloud_cos
            print(f"qcloud_cos SDK 已安装，版本: {qcloud_cos.__version__}")
        except ImportError:
            print("qcloud_cos SDK 未安装。尝试安装...")
            try:
                subprocess.run(["pip", "install", "cos-python-sdk-v5"], check=True)
                print("安装成功。")
            except subprocess.CalledProcessError as e:
                print(f"安装失败: {e}")

    def check_comfyui_environment():
        print("\n检查 ComfyUI 环境...")
        comfyui_path = os.getenv("COMFYUI_PATH")
        if comfyui_path and os.path.exists(comfyui_path):
            print(f"ComfyUI 路径已设置: {comfyui_path}")
        else:
            print("未检测到 ComfyUI 环境变量或路径。")

NODE_CLASS_MAPPINGS = {"PrintInfo": PrintInfo}
NODE_DISPLAY_NAME_MAPPINGS = {"PrintInfo": "🚩 PrintInfo"}