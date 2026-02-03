#!/usr/bin/env python3
"""
X Article 全自动发布脚本
包含完整的反机器人检测机制
"""

import asyncio
import random
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright, Page
import time

# 添加脚本路径
script_dir = Path(__file__).parent / "pasreMarkDown/skills/x-article-publisher/scripts"
sys.path.insert(0, str(script_dir))

from parse_markdown import parse_markdown_file
from copy_to_clipboard import copy_html_to_clipboard, copy_image_to_clipboard

import shutil

# Chrome 用户数据目录
CHROME_USER_DATA_DIR = Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'User Data'
# 临时副本目录 (在当前项目下)
TEMP_USER_DATA_DIR = Path.cwd() / "chrome_data_mirror"


def prepare_user_data_dir():
    """准备用户数据目录副本（保留登录状态，排除垃圾文件）"""
    print(f"   📁 检查浏览器配置镜像...")
    
    if not CHROME_USER_DATA_DIR.exists():
        print(f"❌ 未找到源 Chrome 数据: {CHROME_USER_DATA_DIR}")
        return None
        
    # 如果副本不存在，或者源文件更新时间更近（可选，这里简化为存在即复用，除非强制刷新）
    # 为了保证登录状态最新，我们只克隆关键文件，或者每次增量更新
    # 简单策略：如果不存在则复制。如果用户发现登录失效，可以手动删掉 chrome_data_mirror 文件夹
    
    if TEMP_USER_DATA_DIR.exists():
        print(f"   ✅ 使用现有的配置镜像: {TEMP_USER_DATA_DIR}")
        print(f"      (如果登录失效，请手动删除此文件夹)")
        return TEMP_USER_DATA_DIR
    
    print(f"   🔄 正在创建配置镜像（首次运行较慢，请稍候）...")
    print(f"      源: {CHROME_USER_DATA_DIR}")
    print(f"      目标: {TEMP_USER_DATA_DIR}")
    
    try:
        # 定义要排除的目录（缓存、临时文件等）
        def ignore_patterns(path, names):
            return [n for n in names if n in {
                'Cache', 'Code Cache', 'GPUCache', 'ShaderCache', 
                'Service Worker', 'CacheStorage', 'File System',
                'Crashpad', 'BrowserMetrics', 'Safe Browsing', 'GraphiteDawnCache'
            }]

        shutil.copytree(CHROME_USER_DATA_DIR, TEMP_USER_DATA_DIR, ignore=ignore_patterns)
        print(f"   ✅ 镜像创建完成")
        return TEMP_USER_DATA_DIR
    except Exception as e:
        print(f"   ⚠️  创建镜像失败: {e}")
        return CHROME_USER_DATA_DIR


class HumanBehaviorSimulator:
    """模拟人类行为，避免机器人检测"""
    
    @staticmethod
    async def random_delay(min_ms: int = 500, max_ms: int = 2000):
        """随机延迟"""
        delay = random.uniform(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)
    
    @staticmethod
    async def human_type(page: Page, selector: str, text: str, delay_range=(50, 150)):
        """模拟人类打字速度"""
        try:
            element = await page.wait_for_selector(selector, timeout=10000)
            await element.click()
            await HumanBehaviorSimulator.random_delay(300, 800)
            
            for char in text:
                await element.type(char, delay=random.uniform(*delay_range))
                # 偶尔停顿（模拟思考）
                if random.random() < 0.1:
                    await asyncio.sleep(random.uniform(0.3, 1.0))
        except Exception as e:
            print(f"⚠️  打字模拟失败: {e}")
            # 降级方案：直接填写
            await page.fill(selector, text)
    
    @staticmethod
    async def human_click(page: Page, selector: str):
        """模拟人类点击（带随机偏移）"""
        try:
            element = await page.wait_for_selector(selector, timeout=10000)
            
            # 先移动鼠标到元素附近
            box = await element.bounding_box()
            if box:
                # 随机偏移
                x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
                y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
                
                # 模拟鼠标移动轨迹
                await page.mouse.move(x - 100, y - 100)
                await HumanBehaviorSimulator.random_delay(100, 300)
                await page.mouse.move(x, y)
                await HumanBehaviorSimulator.random_delay(200, 500)
            
            await element.click()
            await HumanBehaviorSimulator.random_delay(300, 800)
        except Exception as e:
            print(f"⚠️  点击模拟失败: {e}")
            # 降级方案：直接点击
            await page.click(selector)
    
    @staticmethod
    async def scroll_smoothly(page: Page, distance: int = 300):
        """平滑滚动"""
        try:
            steps = random.randint(5, 10)
            step_distance = distance / steps
            
            for _ in range(steps):
                await page.evaluate(f"window.scrollBy(0, {step_distance})")
                await asyncio.sleep(random.uniform(0.05, 0.15))
        except:
            pass
    
    @staticmethod
    async def warmup_page(page: Page):
        """页面预热 - 模拟真实用户行为"""
        print("   🔥 页面预热中...")
        
        # 随机滚动
        await HumanBehaviorSimulator.scroll_smoothly(page, random.randint(100, 300))
        await HumanBehaviorSimulator.random_delay(500, 1500)
        
        # 随机移动鼠标
        try:
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await HumanBehaviorSimulator.random_delay(200, 600)
        except:
            pass
        
        print("   ✅ 预热完成")


async def setup_stealth_browser(playwright):
    """配置隐身浏览器（反检测）"""
    
    # 准备用户数据副本
    user_data_dir = prepare_user_data_dir() or CHROME_USER_DATA_DIR
    
    # 启动持久化上下文（使用用户配置）
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        channel="chrome",
        headless=False,
        slow_mo=50,
        # 忽略默认参数以避免冲突
        ignore_default_args=["--enable-automation"],
        args=[
            '--profile-directory=Default',
            # 反自动化检测
            '--disable-blink-features=AutomationControlled',
            # 模拟真实浏览器
            '--start-maximized',
            '--disable-infobars',
            '--disable-notifications',
            # 屏蔽崩溃恢复弹窗
            '--disable-session-crashed-bubble',
            '--hide-crash-restore-bubble',
            # 禁用扩展（防止代理插件干扰）
            '--disable-extensions',
            # 强制直连（配合 VPN Tun 模式）
            '--no-proxy-server',
            # 性能优化
            '--no-sandbox',
            '--disable-setuid-sandbox',
        ],
        no_viewport=True,
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        # 模拟真实用户
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    )
    
    # 注入反检测脚本
    await context.add_init_script("""
        // 覆盖 webdriver 检测
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // 覆盖 plugins 检测
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // 覆盖 languages 检测
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en']
        });
        
        // 覆盖 chrome 检测
        window.chrome = {
            runtime: {}
        };
        
        // 覆盖 permissions 检测
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
    """)
    
    return context


async def find_placeholder_and_select(page: Page, placeholder: str) -> bool:
    """【方案B】在编辑器中查找占位符文本并选中它，准备替换为图片。
    
    占位符格式：<<IMG_PLACEHOLDER_0:filename.png>>
    """
    try:
        print(f"   🔍 搜索占位符: {placeholder[:40]}...")
        
        # 1. 定位编辑器区域
        editor_selectors = [
            'div[contenteditable="true"][data-testid="article"]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ]
        
        editor = None
        for selector in editor_selectors:
            try:
                editor = await page.wait_for_selector(selector, timeout=3000)
                if editor:
                    break
            except:
                continue
        
        if not editor:
            print(f"   ⚠️  未找到编辑器区域")
            return False
        
        # 2. 使用 JavaScript 在编辑器内搜索占位符并选中
        # 这比 Playwright 的选择器更精准
        selected = await page.evaluate('''(placeholder) => {
            // 查找编辑器
            const editor = document.querySelector('div[contenteditable="true"]');
            if (!editor) return false;
            
            // 获取编辑器内所有文本节点
            const walker = document.createTreeWalker(
                editor,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let node;
            while (node = walker.nextNode()) {
                const text = node.textContent;
                const index = text.indexOf(placeholder);
                if (index !== -1) {
                    // 找到占位符，创建选区选中它
                    const range = document.createRange();
                    range.setStart(node, index);
                    range.setEnd(node, index + placeholder.length);
                    
                    const selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    // 滚动到可见区域
                    const rect = range.getBoundingClientRect();
                    if (rect.top < 0 || rect.bottom > window.innerHeight) {
                        node.parentElement.scrollIntoView({ block: 'center' });
                    }
                    
                    return true;
                }
            }
            return false;
        }''', placeholder)
        
        if selected:
            print(f"   ✅ 已选中占位符文本")
            await HumanBehaviorSimulator.random_delay(300, 500)
            return True
        else:
            print(f"   ⚠️  未找到占位符: {placeholder}")
            return False
            
    except Exception as e:
        print(f"   ⚠️  占位符搜索失败: {e}")
        return False


async def find_text_position(page: Page, text_snippet: str) -> bool:
    """在【编辑器内部】精确查找文本位置并定位光标（旧方法，作为备用）"""
    try:
        # 1. 先定位编辑器区域（限定搜索范围，避免误匹配页面其他区域）
        editor_selectors = [
            'div[contenteditable="true"][data-testid="article"]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ]
        
        editor = None
        for selector in editor_selectors:
            try:
                editor = await page.wait_for_selector(selector, timeout=3000)
                if editor:
                    print(f"   ✅ 已定位编辑器区域: {selector}")
                    break
            except:
                continue
        
        if not editor:
            print(f"   ⚠️  未找到编辑器区域")
            return False
        
        # 2. 在编辑器内部查找文本（使用前30个字符）
        text_to_find = text_snippet[:30].strip()
        
        # 尝试多种方式在编辑器内查找
        text_element = None
        try:
            # 方法1：直接在编辑器内查找 p 标签
            text_element = await editor.query_selector(f"p:has-text('{text_to_find}')")
        except:
            pass
        
        if not text_element:
            try:
                # 方法2：查找任何包含文本的元素
                text_element = await editor.query_selector(f"text={text_to_find}")
            except:
                pass
        
        if not text_element:
            print(f"   ⚠️  在编辑器中未找到文本: {text_to_find}...")
            return False
        
        # 3. 滚动到目标位置
        await text_element.scroll_into_view_if_needed()
        await HumanBehaviorSimulator.random_delay(300, 600)
        
        # 4. 点击文本末尾
        await text_element.click()
        await HumanBehaviorSimulator.random_delay(200, 400)
        
        # 5. 移动光标到行尾
        await page.keyboard.press('End')
        await HumanBehaviorSimulator.random_delay(200, 400)
        
        # 6. 换行（避免图片与文本混在一起）
        await page.keyboard.press('Enter')
        await HumanBehaviorSimulator.random_delay(300, 500)
        
        # 7. 二次确认焦点在编辑器（防止焦点丢失）
        await editor.click()
        await HumanBehaviorSimulator.random_delay(200, 300)
        
        print(f"   ✅ 光标已定位到插入位置")
        return True
        
    except Exception as e:
        print(f"   ⚠️  定位失败: {e}")
        return False


async def wait_for_image_upload(page: Page, timeout: int = 15) -> bool:
    """等待图片上传完成（检测X的图片CDN）"""
    try:
        print(f"   ⏳ 等待图片上传（最多 {timeout} 秒）...")
        
        # 检查是否出现 X 的图片 CDN 链接
        await page.wait_for_selector(
            'img[src*="pbs.twimg.com"]',
            timeout=timeout * 1000,
            state='visible'
        )
        
        print("   ✅ 图片上传完成（已加载CDN图片）")
        return True
        
    except Exception as e:
        print(f"   ⚠️  上传检测超时: {str(e)[:50]}...")
        print(f"   ℹ️  继续执行（图片可能已上传或需手动检查）")
        return False


async def get_editor_handle(page: Page):
    """获取编辑器节点句柄"""
    editor_selectors = [
        'div[contenteditable="true"][data-testid="article"]',
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"]',
    ]
    for selector in editor_selectors:
        try:
            editor = await page.wait_for_selector(selector, timeout=2000)
            if editor:
                return editor
        except:
            continue
    return None


async def get_editor_image_count(page: Page) -> int:
    """统计编辑器内部图片数量"""
    try:
        editor = await get_editor_handle(page)
        if not editor:
            return 0
        imgs = await editor.query_selector_all("img")
        return len(imgs)
    except:
        return 0


async def wait_for_editor_image_increase(page: Page, before_count: int, timeout: int = 15) -> bool:
    """等待编辑器内图片数量增加（更可靠的插入验证）"""
    try:
        checks = max(1, int(timeout / 0.5))
        for _ in range(checks):
            current = await get_editor_image_count(page)
            if current > before_count:
                print(f"   ✅ 图片节点新增（{before_count} -> {current}）")
                return True
            await asyncio.sleep(0.5)
        print(f"   ⚠️  图片节点未增加（{before_count} -> {current}）")
        return False
    except Exception as e:
        print(f"   ⚠️  图片节点验证失败: {e}")
        return False


async def auto_publish_article(markdown_file: str, publish: bool = False):
    """全自动发布文章"""
    
    print("=" * 80)
    print("🤖 X Article 全自动发布系统")
    print("=" * 80)
    print()
    
    # 检查 Chrome 配置
    if not CHROME_USER_DATA_DIR.exists():
        print(f"❌ 未找到 Chrome 用户数据目录: {CHROME_USER_DATA_DIR}")
        return False
    
    # 解析 Markdown
    print("📄 [1/7] 解析 Markdown 文件...")
    result = parse_markdown_file(markdown_file)
    print(f"✅ 解析成功")
    print(f"   📌 标题: {result['title']}")
    print(f"   🖼️  封面图: {result['cover_image'] or '无'}")
    print(f"   🖼️  内容图片: {len(result['content_images'])} 张")
    print()
    
    async with async_playwright() as p:
        print("🌐 [2/7] 启动隐身浏览器...")
        print("   ⚠️  请确保已关闭所有 Chrome 窗口")
        print()
        
        context = None
        page = None # Initialize page to None
        try:
            context = await setup_stealth_browser(p)
            print("✅ 浏览器已启动（反检测模式）")
            
            page = await context.new_page() if not context.pages else context.pages[0]
            
            # 导航到 X Articles
            print()
            print("🔗 [3/7] 打开 X Articles 编辑器...")
            try:
                await page.goto("https://x.com/compose/articles", timeout=60000, wait_until="domcontentloaded")
                await HumanBehaviorSimulator.random_delay(2000, 4000)
                print("✅ 页面已加载")
            except Exception as e:
                print(f"⚠️  导航超时: {e}")
            
            # 检查登录状态
            current_url = page.url
            if "login" in current_url.lower() or "flow/login" in current_url.lower():
                print("⚠️  检测到未登录状态！")
                print("👉 请在弹出的浏览器中手动完成登录")
                print("   (登录成功并跳转到 Articles 页面后，回到这里按 Enter 继续)")
                await asyncio.get_event_loop().run_in_executor(None, input)
                
                # 二次检查
                if "login" in page.url.lower():
                    print("❌ 依然未登录，退出")
                    return False
            
            print("✅ 已登录")
            
            # 检查是否需要点击 "Write" 按钮
            try:
                write_selectors = [
                    # 用户提供的精确选择器
                    'a[data-testid="empty_state_button_text"]',
                    # 其他备选
                    'a[href="/compose/articles/new"]',
                    'div[role="button"][aria-label="Write"]',
                    'span:has-text("Write")',
                    'span:has-text("撰写")',
                ]
                
                for selector in write_selectors:
                    try:
                        write_btn = await page.wait_for_selector(selector, timeout=3000)
                        if write_btn:
                            print("   👈 点击 'Write' 按钮...")
                            await write_btn.click()
                            await HumanBehaviorSimulator.random_delay(2000, 4000)
                            break
                    except:
                        continue
            except Exception as e:
                pass  # 如果没找到，可能直接进入了编辑器
                
            # 页面预热
            await HumanBehaviorSimulator.warmup_page(page)
            print()
            
            # 输入标题
            print("✍️  [4/7] 输入标题...")
            try:
                # 查找标题输入框（多种可能的选择器）
                title_selectors = [
                    'textarea[placeholder="Add a title"]',  # 英文界面精确匹配
                    'textarea[name="Article Title"]',       # 通过 name 属性匹配
                    'input[placeholder*="标题"]',
                    'div[contenteditable="true"]',
                    'textarea[placeholder*="标题"]',
                ]
                
                title_input = None
                for selector in title_selectors:
                    try:
                        title_input = await page.wait_for_selector(selector, timeout=3000)
                        if title_input:
                            break
                    except:
                        continue
                
                if title_input:
                    # 必须先点击激活文本框
                    await title_input.click()
                    await HumanBehaviorSimulator.random_delay(500, 1000)
                    await page.fill(selector, result['title']) # 使用 fill 可能更稳定，type 可能太慢
                    print(f"✅ 标题已输入: {result['title']}")
                else:
                    print("⚠️  未找到标题输入框，请手动输入")
            except Exception as e:
                print(f"⚠️  标题输入失败: {e}")
                # 尝试备用方案：直接键盘输入（如果焦点已在标题栏）
                try:
                     await page.keyboard.type(result['title'])
                except:
                     pass
            
            await HumanBehaviorSimulator.random_delay(1000, 2000)
            print()
            
            # 粘贴文章内容
            print("📝 [5/7] 粘贴文章内容...")
            try:
                # 复制 HTML 到剪贴板
                copy_html_to_clipboard(result['html'])
                await HumanBehaviorSimulator.random_delay(500, 1000)
                
                # 查找内容编辑区域
                content_selectors = [
                    'div[contenteditable="true"][data-testid="article"]', # 可能的 data-testid
                    'div[contenteditable="true"][role="textbox"]',
                    'div[contenteditable="true"]',
                    'div.public-DraftEditor-content',
                ]
                
                content_area = None
                for selector in content_selectors:
                    try:
                        content_area = await page.wait_for_selector(selector, timeout=3000)
                        if content_area:
                            break
                    except:
                        continue
                
                if content_area:
                    await content_area.click()
                    await HumanBehaviorSimulator.random_delay(500, 1000)
                    
                    # 粘贴内容
                    await page.keyboard.press('Control+V')
                    await HumanBehaviorSimulator.random_delay(2000, 3000)
                    print(f"✅ 内容已粘贴 ({len(result['html'])} 字符)")
                else:
                    print("⚠️  未找到内容编辑区域")
            except Exception as e:
                print(f"⚠️  内容粘贴失败: {e}")
            
            print()
            
            # ===== 步骤6：先插入内容图片（方案B：占位符精准定位）=====
            if result['content_images']:
                print(f"🖼️  [6/7] 插入内容图片 ({len(result['content_images'])} 张)...")
                
                for idx, img in enumerate(result['content_images'], 1):
                    if not img['exists']:
                        continue
                    
                    print(f"\n   图片 {idx}/{len(result['content_images'])}: {img['path']}")
                    
                    # 获取占位符（方案B核心）
                    placeholder = img.get('placeholder', '')
                    
                    if placeholder:
                        print(f"   📍 使用占位符定位: {placeholder}")
                    else:
                        print(f"   📍 降级使用文本定位: {img.get('after_text', '')[:40]}...")
                    
                    try:
                        # 方案B：优先使用占位符定位
                        found = False
                        used_placeholder = False
                        if placeholder:
                            found = await find_placeholder_and_select(page, placeholder)
                            if found:
                                used_placeholder = True
                        
                        # 降级：如果没有占位符或占位符未找到，使用旧方法
                        if not found and img.get('after_text'):
                            print(f"   🔄 降级使用文本定位...")
                            found = await find_text_position(page, img.get('after_text', ''))
                        
                        if found:
                            # 记录编辑器内图片数量（用于插入验证）
                            before_count = await get_editor_image_count(page)
                            print(f"   🔎 插入前图片数量: {before_count}")

                            # 如果使用占位符定位，先删除选中的占位符文本
                            if used_placeholder:
                                print(f"   🗑️  删除占位符文本...")
                                await page.keyboard.press('Delete')
                                await HumanBehaviorSimulator.random_delay(300, 500)

                            # 复制图片到剪贴板
                            copy_image_to_clipboard(img['path'], quality=85)
                            await HumanBehaviorSimulator.random_delay(500, 1000)
                            
                            # 粘贴图片
                            print(f"   📋 执行粘贴...")
                            await page.keyboard.press('Control+V')
                            await HumanBehaviorSimulator.random_delay(1000, 1500)

                            # 等待编辑器内图片节点增加（关键验证）
                            inserted = await wait_for_editor_image_increase(page, before_count, timeout=15)

                            # 若未插入，自动重试一次（避免偶发焦点丢失）
                            if not inserted:
                                print(f"   🔁 第一次插入未检测到图片，准备重试...")
                                editor = await get_editor_handle(page)
                                if editor:
                                    await editor.click()
                                    await HumanBehaviorSimulator.random_delay(200, 400)
                                await page.keyboard.press('Control+V')
                                await HumanBehaviorSimulator.random_delay(1000, 1500)
                                inserted = await wait_for_editor_image_increase(page, before_count, timeout=15)

                            # 等待图片上传完成（CDN 检测，辅助验证）
                            upload_success = await wait_for_image_upload(page, timeout=15)

                            if inserted and upload_success:
                                print(f"   ✅ 图片 {idx} 已成功插入并上传")
                            elif inserted:
                                print(f"   ⚠️  图片 {idx} 已插入，但上传状态未知")
                            else:
                                print(f"   ❌ 图片 {idx} 插入失败，请手动检查")
                        else:
                            print(f"   ⚠️  未找到插入位置（占位符和文本均未匹配），跳过")
                    
                    except Exception as e:
                        print(f"   ⚠️  插入失败: {e}")
                    
                    # 随机延迟（模拟人类操作）
                    await HumanBehaviorSimulator.random_delay(1000, 2000)
                
                print()
            
            # ===== 步骤7：最后插入封面图 =====
            if result['cover_image'] and result['cover_exists']:
                print("🖼️  [7/7] 插入封面图...")
                cover_uploaded = False
                
                try:
                    # 方法1（优先）：直接使用 file input 上传（最稳定）
                    try:
                        file_input = await page.wait_for_selector('input[type="file"]', timeout=3000)
                        if file_input:
                            await file_input.set_input_files(result['cover_image'])
                            print(f"✅ 封面图已上传 (File Input): {result['cover_image']}")
                            cover_uploaded = True
                    except Exception as e:
                        print(f"   ℹ️  File Input 方式不可用: {e}")
                    
                    # 方法2（降级）：点击上传按钮后粘贴
                    if not cover_uploaded:
                        # 复制封面图到剪贴板
                        copy_image_to_clipboard(result['cover_image'], quality=85)
                        await HumanBehaviorSimulator.random_delay(500, 1000)
                        
                        # 查找封面图上传区域/按钮
                        cover_selectors = [
                            'span:has-text("Upload")',
                            'div:has-text("Upload")',
                            'button[aria-label*="封面"]',
                            'button[aria-label*="Cover"]',
                            'div[data-testid*="cover"]',
                            'text="Add cover image"',
                            'text="添加封面图片"'
                        ]
                        
                        cover_button = None
                        matched_selector = None
                        for selector in cover_selectors:
                            try:
                                cover_button = await page.wait_for_selector(selector, timeout=2000)
                                if cover_button:
                                    matched_selector = selector
                                    break
                            except:
                                continue
                        
                        if cover_button and matched_selector:
                            await HumanBehaviorSimulator.human_click(page, matched_selector)
                            await HumanBehaviorSimulator.random_delay(500, 1000)
                            
                            # 尝试粘贴
                            await page.keyboard.press('Control+V')
                            await HumanBehaviorSimulator.random_delay(2000, 3000)
                            print(f"✅ 封面图已粘贴: {result['cover_image']}")
                            cover_uploaded = True
                        else:
                            print("⚠️  未找到封面图上传按钮，请手动上传")

                except Exception as e:
                    print(f"⚠️  封面图插入尝试失败: {e}")

                # 无论通过哪种方式上传，都尝试处理 "Apply" 弹窗
                try:
                     print("   ⏳ 等待图片编辑器弹窗...")
                     await HumanBehaviorSimulator.random_delay(2000, 3000)
                     
                     # Apply 按钮选择器列表
                     apply_selectors = [
                         'button[data-testid="applyButton"]',
                         'span:has-text("Apply")',
                         'div[role="button"]:has-text("Apply")',
                         'button:has-text("Apply")',
                     ]
                     
                     found_apply = False
                     for selector in apply_selectors:
                         try:
                             # 使用非常短的超时，快速轮询
                             apply_btn = await page.wait_for_selector(selector, state='visible', timeout=2000)
                             if apply_btn:
                                 print(f"   👈 点击 'Apply' 确认封面 (使用: {selector})...")
                                 await apply_btn.click()
                                 found_apply = True
                                 break
                         except:
                             continue
                     
                     if found_apply:
                         await HumanBehaviorSimulator.random_delay(1000, 2000)
                         print("   ✅ 封面已应用")
                     else:
                         # 也许已经自动应用了，或者是上面的操作没触发弹窗
                         pass
                         
                except Exception as e:
                     # 这部分是非关键路径，不应该阻塞流程
                     print(f"   ℹ️  跳过 Apply 确认 (可能不需要): {e}")
                
                print()
            
            # 完成
            print("=" * 80)
            print("✅ 自动化流程完成！")
            print("=" * 80)
            print()
            print("📋 请在浏览器中：")
            print("   1. 检查内容是否正确")
            print("   2. 预览文章")
            
            if publish:
                print("   🚀 [8/+] 自动点击发布...")
                try:
                    # 1. 点击右上角的 "Publish" 按钮
                    publish_selectors = [
                        'button[data-testid="tweetButtonInline"]',
                        'div[role="button"]:has-text("Publish")',
                        'div[role="button"]:has-text("发布")',
                        'button:has-text("Publish")',
                        'span:has-text("Publish")',
                    ]
                    
                    publish_btn = None
                    for selector in publish_selectors:
                        try:
                            publish_btn = await page.wait_for_selector(selector, timeout=2000)
                            if publish_btn:
                                print(f"      找到发布按钮: {selector}")
                                break
                        except:
                            continue
                    
                    if publish_btn:
                        await HumanBehaviorSimulator.human_click(page, selector)
                        print("      ⏳ 等待确认弹窗 (2-3秒)...")
                        await HumanBehaviorSimulator.random_delay(2000, 3500)
                        
                        # 2. 处理可能的确认弹窗 (Confirm / Post / Publish)
                        # 用户反馈：点击 publish 后会有弹窗，需要再次点击 Publish
                        confirm_selectors = [
                            'button[data-testid="confirmationSheetConfirm"]', # 标准确认按钮 ID
                            'div[role="dialog"] button:has-text("Publish")', # 弹窗内的 Publish 按钮
                            'div[role="dialog"] div[role="button"]:has-text("Publish")',
                            'div[data-testid="sheetDialog"] div[role="button"]:has-text("Publish")',
                            # 兜底文本匹配
                            'div[role="button"]:has-text("Post")',
                            'div[role="button"]:has-text("Confirm")',
                            'div[role="button"]:has-text("Publish")',  # 直接找 Publish 按钮
                        ]
                        
                        found_confirm = False
                        for selector in confirm_selectors:
                            try:
                                # 只查找可见的元素
                                confirm_btn = await page.wait_for_selector(selector, state='visible', timeout=2000)
                                if confirm_btn:
                                    print(f"      点击确认发布按钮: {selector}...")
                                    await HumanBehaviorSimulator.human_click(page, selector)
                                    found_confirm = True
                                    break
                            except:
                                continue
                        
                        if found_confirm:
                            print("      ✅ 最终发布点击完成")
                            # 再等一下，确保请求发送
                            await HumanBehaviorSimulator.random_delay(2000, 3000)
                        else:
                            print("      ℹ️  未检测到确认弹窗，可能已直接发布或需人工确认")
                            
                        print("   ✅ 发布流程执行完毕")
                    else:
                        print("   ⚠️  未找到主发布按钮，请手动点击")
                        
                except Exception as e:
                    print(f"   ⚠️  自动发布失败: {e}")
                    print("   👉 请手动点击发布")
            else:
                print("   3. 手动点击「保存草稿」或「发布」 (未开启 --publish)")
            
            if publish:
                print("⏳ 发布成功，5秒后自动关闭浏览器...")
                await asyncio.sleep(5)
            else:
                print("按 Enter 关闭浏览器...")
                await asyncio.get_event_loop().run_in_executor(None, input)
            
        except Exception as e:
            print(f"❌ 运行错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if context:
                print("🧹 正在释放浏览器资源...")
                await context.close()
                print("✅ 资源已完全释放")
    
    print("✅ 完成")
    return True


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print("""
用法: python auto_publish.py <markdown_file> [--publish]

参数:
    markdown_file    Markdown 文件路径
    --publish        自动发布（默认保存为草稿）

示例:
    python auto_publish.py article.md
    python auto_publish.py article.md --publish

前提:
    taskkill /F /IM chrome.exe
    1. 已在 Chrome 中登录 X 账号
    2. 运行前需关闭所有 Chrome 窗口
    3. 需要 X Premium Plus 订阅
""")
        sys.exit(0)
    
    markdown_file = sys.argv[1]
    publish = '--publish' in sys.argv
    
    if not os.path.exists(markdown_file):
        print(f"❌ 文件不存在: {markdown_file}")
        sys.exit(1)
    
    try:
        asyncio.run(auto_publish_article(markdown_file, publish))
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
