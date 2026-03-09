#!/usr/bin/env python3
"""
共享浏览器会话层 - 真实 Chrome + Patchright CDP
统一管理 Chrome 启动、CDP 连接、Profile 复用、登录态检测

职责：
- 启动真实 Chrome
- 连接 Patchright
- Profile 锁文件清理
- 端口检测
- 登录态检测
"""

import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

try:
    from patchright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
    from patchright.sync_api import Error as PlaywrightError
    from patchright.sync_api import TimeoutError as PlaywrightTimeoutError
except ImportError:
    # 降级处理：如果 patchright 未安装
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    Browser = object
    BrowserContext = object
    Page = object
    Playwright = object
    sync_playwright = None

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CHROME_BINARY = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
DEFAULT_REMOTE_DEBUGGING_PORT = 19222
DEFAULT_PROFILE_DIR = Path.cwd() / "chrome_data_mirror"

# 登录检测选择器
LOGIN_INDICATORS = [
    'a[href="/login"]',
    'a[href*="flow/login"]',
    'input[autocomplete="username"]',
    'input[name="text"]',
    'input[autocomplete="current-password"]',
]


class ChromeCDPSession:
    """Chrome CDP 会话管理器"""
    
    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        chrome_binary: Optional[Path] = None,
        remote_debugging_port: Optional[int] = None,
    ):
        """
        初始化 Chrome CDP 会话
        
        Args:
            profile_dir: Chrome profile 目录（默认：chrome_data_mirror）
            chrome_binary: Chrome 可执行文件路径
            remote_debugging_port: CDP 端口（默认：19222）
        """
        self.profile_dir = profile_dir or Path(os.environ.get("XPOST_PROFILE_DIR", DEFAULT_PROFILE_DIR))
        self.chrome_binary = chrome_binary or DEFAULT_CHROME_BINARY
        self.remote_debugging_port = remote_debugging_port or int(
            os.environ.get("XPOST_REMOTE_DEBUGGING_PORT", DEFAULT_REMOTE_DEBUGGING_PORT)
        )
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.chrome_process: Optional[subprocess.Popen] = None
        
        # 确保 profile 目录存在
        self.profile_dir.mkdir(parents=True, exist_ok=True)
    
    def _clean_profile_locks(self):
        """清理 profile 锁文件"""
        try:
            lock_file = self.profile_dir / "SingletonLock"
            if lock_file.exists():
                lock_file.unlink()
                logger.info(f"已清理锁文件: {lock_file}")
        except Exception as e:
            logger.warning(f"清理锁文件失败: {e}")
    
    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        try:
            response = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
            response.read()
            return True
        except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
            return False
    
    def _start_chrome(self) -> bool:
        """
        启动真实 Chrome
        
        Returns:
            bool: 启动成功返回 True
        """
        # 检查 Chrome 是否存在
        if not self.chrome_binary.exists():
            raise FileNotFoundError(f"Chrome 未找到: {self.chrome_binary}")
        
        # 清理锁文件
        self._clean_profile_locks()
        
        # 检查端口是否已被占用
        if self._is_port_in_use(self.remote_debugging_port):
            logger.info(f"CDP 端口 {self.remote_debugging_port} 已在使用，尝试复用现有会话")
            return True
        
        # 启动 Chrome
        logger.info(f"启动 Chrome: {self.chrome_binary}")
        logger.info(f"Profile: {self.profile_dir}")
        logger.info(f"CDP 端口: {self.remote_debugging_port}")
        
        try:
            self.chrome_process = subprocess.Popen(
                [
                    str(self.chrome_binary),
                    f"--remote-debugging-port={self.remote_debugging_port}",
                    f"--user-data-dir={self.profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-popup-blocking",
                    "--disable-infobars",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            
            # 等待 CDP 端口就绪
            for attempt in range(30):
                if self._is_port_in_use(self.remote_debugging_port):
                    logger.info(f"Chrome CDP 端口就绪（尝试 {attempt + 1}/30）")
                    return True
                time.sleep(0.5)
            
            raise RuntimeError(f"Chrome CDP 端口 {self.remote_debugging_port} 未就绪")
            
        except Exception as e:
            logger.error(f"启动 Chrome 失败: {e}")
            raise
    
    def _connect_playwright(self) -> Tuple[Browser, BrowserContext, Page]:
        """
        连接 Patchright 到 Chrome
        
        Returns:
            Tuple[Browser, BrowserContext, Page]: 浏览器、上下文、页面
        """
        if sync_playwright is None:
            raise ImportError("patchright 未安装，请运行: pip install patchright")
        
        logger.info("连接 Patchright 到 Chrome...")
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{self.remote_debugging_port}"
            )
            
            # 获取或创建上下文
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                logger.info(f"复用现有上下文（共 {len(contexts)} 个）")
            else:
                self.context = self.browser.new_context()
                logger.info("创建新上下文")
            
            # 获取或创建页面
            pages = self.context.pages
            if pages:
                self.page = pages[0]
                logger.info(f"复用现有页面（共 {len(pages)} 个）")
            else:
                self.page = self.context.new_page()
                logger.info("创建新页面")
            
            return self.browser, self.context, self.page
            
        except Exception as e:
            logger.error(f"连接 Patchright 失败: {e}")
            raise
    
    def start(self) -> Tuple[Browser, BrowserContext, Page]:
        """
        启动 Chrome 并连接 Patchright
        
        Returns:
            Tuple[Browser, BrowserContext, Page]: 浏览器、上下文、页面
        """
        # 1. 启动 Chrome
        self._start_chrome()
        
        # 2. 连接 Patchright
        return self._connect_playwright()
    
    def check_login_status(self, url: str = "https://x.com/home", timeout: int = 10000) -> bool:
        """
        检查登录状态
        
        Args:
            url: 检查的 URL（默认：X 首页）
            timeout: 超时时间（毫秒）
        
        Returns:
            bool: 已登录返回 True
        """
        if not self.page:
            raise RuntimeError("页面未初始化，请先调用 start()")
        
        try:
            logger.info(f"检查登录状态: {url}")
            self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            time.sleep(2)  # 等待页面稳定
            
            # 检查是否存在登录指示器
            for selector in LOGIN_INDICATORS:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.is_visible():
                        logger.info(f"发现登录指示器: {selector}")
                        return False
                except:
                    continue
            
            # 检查 URL 是否包含 login
            current_url = self.page.url
            if "login" in current_url.lower() or "flow/login" in current_url.lower():
                logger.info(f"URL 包含 login: {current_url}")
                return False
            
            logger.info("已登录")
            return True
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False
    
    def wait_for_login(self, timeout: int = 300) -> bool:
        """
        等待用户手动登录
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            bool: 登录成功返回 True
        """
        print()
        print("⚠️  检测到未登录状态！")
        print("=" * 60)
        print("📢 请在当前打开的 Chrome 浏览器中完成登录：")
        print("   1. 输入您的 X 用户名/邮箱")
        print("   2. 输入密码")
        print("   3. 完成所有安全验证")
        print("   4. 登录成功后脚本将自动继续")
        print()
        print(f"⏳ 等待登录中... (超时: {timeout}秒)")
        print("=" * 60)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.check_login_status():
                print("✅ 登录成功！")
                return True
            time.sleep(3)
        
        print("❌ 登录超时")
        return False
    
    def close(self):
        """关闭会话"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            if self.chrome_process:
                self.chrome_process.terminate()
                self.chrome_process.wait(timeout=5)
        except Exception as e:
            logger.error(f"关闭会话失败: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def create_session(
    profile_dir: Optional[Path] = None,
    chrome_binary: Optional[Path] = None,
    remote_debugging_port: Optional[int] = None,
) -> ChromeCDPSession:
    """
    创建 Chrome CDP 会话（便捷函数）
    
    Args:
        profile_dir: Chrome profile 目录
        chrome_binary: Chrome 可执行文件路径
        remote_debugging_port: CDP 端口
    
    Returns:
        ChromeCDPSession: 会话实例
    """
    return ChromeCDPSession(
        profile_dir=profile_dir,
        chrome_binary=chrome_binary,
        remote_debugging_port=remote_debugging_port,
    )


# 示例用法
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 方式 1：使用上下文管理器
    with create_session() as session:
        browser, context, page = session.start()
        
        # 检查登录状态
        if not session.check_login_status():
            session.wait_for_login()
        
        # 使用 page 进行操作
        page.goto("https://x.com/home")
        print(f"当前 URL: {page.url}")
    
    # 方式 2：手动管理
    # session = create_session()
    # browser, context, page = session.start()
    # ...
    # session.close()
