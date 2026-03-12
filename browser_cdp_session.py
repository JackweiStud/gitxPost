#!/usr/bin/env python3
"""
共享浏览器会话层 - 真实 Chrome + Playwright CDP
统一管理 Chrome 启动、CDP 连接、Profile 复用、登录态检测

职责：
- 启动真实 Chrome
- 连接 Playwright
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
import sys
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

    def _fetch_cdp_version_info(self) -> dict:
        """读取当前 CDP 实例的版本信息"""
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.remote_debugging_port}/json/version",
                timeout=2,
            ) as response:
                import json

                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"读取 CDP 版本信息失败: {e}")
            return {}

    def _terminate_existing_debug_browser(self):
        """终止占用当前 CDP 端口的浏览器进程"""
        try:
            result = subprocess.run(
                ["/usr/sbin/lsof", "-ti", f"tcp:{self.remote_debugging_port}"],
                capture_output=True,
                text=True,
                check=False,
            )
            pids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if not pids:
                logger.warning(f"未找到占用端口 {self.remote_debugging_port} 的进程")
                return

            logger.warning(
                "检测到需要重启 CDP 浏览器，准备终止端口 %s 上的进程: %s",
                self.remote_debugging_port,
                ",".join(pids),
            )
            subprocess.run(["/bin/kill", "-TERM", *pids], check=False)

            for _ in range(20):
                if not self._is_port_in_use(self.remote_debugging_port):
                    return
                time.sleep(0.5)

            subprocess.run(["/bin/kill", "-KILL", *pids], check=False)
            for _ in range(10):
                if not self._is_port_in_use(self.remote_debugging_port):
                    return
                time.sleep(0.5)
        except Exception as e:
            logger.warning(f"终止现有 CDP 浏览器失败: {e}")
    
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
    
    def _start_chrome(self, headless: bool = True) -> bool: # Modified to accept headless
        """
        启动真实 Chrome
        
        Args:
            headless: 是否以无头模式启动 Chrome (默认: True)
        
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
            version_info = self._fetch_cdp_version_info()
            user_agent = version_info.get("User-Agent", "")
            is_headless_browser = "HeadlessChrome" in user_agent

            if not headless and is_headless_browser:
                logger.warning(
                    "现有 CDP 浏览器为 headless，会终止后重新启动可见 Chrome"
                )
                self._terminate_existing_debug_browser()
            else:
                logger.info(
                    f"CDP 端口 {self.remote_debugging_port} 已在使用，尝试复用现有会话"
                )
                return True
        
        # 启动 Chrome
        logger.info(f"启动 Chrome: {self.chrome_binary}")
        logger.info(f"Profile: {self.profile_dir}")
        logger.info(f"CDP 端口: {self.remote_debugging_port}")
        logger.info(f"Headless: {headless}") # 添加 headless 状态日志
        
        chrome_args = [
            str(self.chrome_binary),
            f"--remote-debugging-port={self.remote_debugging_port}",
            f"--user-data-dir={self.profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--disable-infobars",
            "--start-maximized", # Ensure the browser starts maximized for better visibility
        ]
        
        if headless:
            chrome_args.append("--headless=new") # Use new headless mode

        logger.info(f"Chrome args: {chrome_args}") # 打印命令行参数
        
        try:
            self.chrome_process = subprocess.Popen(
                chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid # macOS/Linux 防止父进程退出时子进程也退出
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
    
    def _connect_playwright(self, headless: bool = True) -> Tuple[Browser, BrowserContext, Page]:
        """
        连接 Playwright 到 Chrome
        
        Args:
            headless: 是否以无头模式启动浏览器 (默认: True)
        
        Returns:
            Tuple[Browser, BrowserContext, Page]: 浏览器、上下文、页面
        """
        if sync_playwright is None:
            raise ImportError("patchright 未安装，请运行: pip install patchright")
        
        logger.info("连接 Playwright 到 Chrome...")

        def _start_sync_playwright(retry_bypass_asyncio_check: bool = False):
            if not retry_bypass_asyncio_check:
                return sync_playwright().start()

            import asyncio

            original_get_running_loop = asyncio.get_running_loop

            def _fake_get_running_loop():
                raise RuntimeError("no running event loop")

            try:
                asyncio.get_running_loop = _fake_get_running_loop
                logger.warning("检测到 Sync API asyncio 误判，已启用一次性绕过重试")
                return sync_playwright().start()
            finally:
                asyncio.get_running_loop = original_get_running_loop
        
        try:
            # 不在这里主动阻塞 asyncio 环境。
            # 某些宿主（例如 OpenClaw）会污染事件循环检测，但独立子进程仍可正常运行。
            # 这里直接交给 patchright 自己决定是否能启动 Sync API，避免误杀可运行场景。
            try:
                self.playwright = _start_sync_playwright()
            except Exception as exc:
                if "inside the asyncio loop" not in str(exc).lower():
                    raise
                logger.warning("Patchright Sync API 命中 asyncio 检查，准备按兼容模式重试")
                self.playwright = _start_sync_playwright(retry_bypass_asyncio_check=True)
            
            # Connect over CDP for existing Chrome process
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
            logger.error(f"连接 Playwright 失败: {e}")
            raise
    
    def start(self, headless: bool = True) -> Tuple[Browser, BrowserContext, Page]:
        """
        启动 Chrome 并连接 Playwright
        
        Args:
            headless: 是否以无头模式启动浏览器 (默认: True)
            注意：当使用 CDP 连接已运行的 Chrome 实例时，此参数可能不直接控制其可见性。
            Chrome 启动时的 `--headless` 参数才是决定因素。
        
        Returns:
            Tuple[Browser, BrowserContext, Page]: 浏览器、上下文、页面
        """
        # 1. 启动 Chrome
        # 这里需要调整，以 `--headless` 参数控制 Chrome 的启动方式
        self._start_chrome(headless=headless) # Pass headless state here
        
        # 2. 连接 Playwright
        return self._connect_playwright(headless=headless) # Also pass to connect, mainly for consistency

    def create_task_page(self, reuse_existing: bool = False) -> Page:
        """为当前任务选择一个稳定页面，默认新建标签页避免复用到脏页面"""
        if not self.context:
            raise RuntimeError("浏览器上下文未初始化，请先调用 start()")

        candidate_pages = []
        for existing_page in self.context.pages:
            try:
                current_url = existing_page.url or ""
                if current_url.startswith("chrome://") or current_url.startswith("devtools://"):
                    continue
                candidate_pages.append(existing_page)
            except Exception:
                continue

        if reuse_existing and candidate_pages:
            page = candidate_pages[-1]
        else:
            page = self.context.new_page()

        self.page = page
        try:
            page.bring_to_front()
        except Exception:
            pass
        return page
    
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
            # 1. 先关闭 Playwright 资源
            if self.page:
                try:
                    self.page.close()
                except Exception as e:
                    logger.warning(f"关闭页面失败: {e}")
            
            if self.context:
                try:
                    self.context.close()
                except Exception as e:
                    logger.warning(f"关闭上下文失败: {e}")
            
            if self.browser:
                try:
                    self.browser.close()
                except Exception as e:
                    logger.warning(f"关闭浏览器失败: {e}")
            
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    logger.warning(f"停止 Playwright 失败: {e}")
            
            # 2. 再关闭 Chrome 进程（如果存在）
            if self.chrome_process:
                try:
                    self.chrome_process.terminate()
                    try:
                        self.chrome_process.wait(timeout=3)
                        logger.info("Chrome 进程已正常终止")
                    except subprocess.TimeoutExpired:
                        logger.warning("Chrome 进程终止超时，强制 kill")
                        self.chrome_process.kill()
                        self.chrome_process.wait(timeout=2)
                except Exception as e:
                    logger.warning(f"关闭 Chrome 进程失败: {e}")
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
    headless: bool = False, # 默认使用可见 Chrome，避免静默复用到旧的 headless 会话
) -> ChromeCDPSession:
    """
    创建 Chrome CDP 会话（便捷函数）
    
    Args:
        profile_dir: Chrome profile 目录
        chrome_binary: Chrome 可执行文件路径
        remote_debugging_port: CDP 端口
        headless: 是否以无头模式启动浏览器 (默认: True)
    
    Returns:
        ChromeCDPSession: 会话实例
    """
    session = ChromeCDPSession(
        profile_dir=profile_dir,
        chrome_binary=chrome_binary,
        remote_debugging_port=remote_debugging_port,
    )
    # The start method of the session instance will now take the headless parameter.
    session.start(headless=headless)
    return session


# 示例用法
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 方式 1：使用上下文管理器
    with create_session(headless=False) as session: # Example usage with headless=False
        browser, context, page = session.browser, session.context, session.page # Access page from session object
        
        # 检查登录状态
        if not session.check_login_status():
            session.wait_for_login()
        
        # 使用 page 进行操作
        page.goto("https://x.com/home")
        print(f"当前 URL: {page.url}")
    
    # 方式 2：手动管理
    # session = create_session(headless=False)
    # browser, context, page = session.browser, session.context, session.page
    # ...
    # session.close()
