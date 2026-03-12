#!/usr/bin/env python3
"""
X Article 全自动发布系统 (macOS 专用版)
使用 undetected-chromedriver 实现反检测技术
支持安全登录和完整发布功能
"""

import os
import sys
import time
import random
import argparse
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 添加脚本路径
script_dir = Path(__file__).parent / "pasreMarkDown/skills/x-article-publisher/scripts"
sys.path.insert(0, str(script_dir))

from parse_markdown import parse_markdown_file
from copy_to_clipboard import copy_html_to_clipboard, copy_image_to_clipboard

# 配置
PROFILE_DIR = os.environ.get("XPOST_PROFILE_DIR")
if PROFILE_DIR:
    USER_DATA_DIR = Path(PROFILE_DIR)
else:
    USER_DATA_DIR = Path.cwd() / "chrome_data_mirror"
ARTICLES_URL = "https://x.com/compose/articles"


class HumanBehaviorSimulator:
    """模拟人类行为，避免机器人检测"""
    
    @staticmethod
    def random_delay(min_ms: int = 500, max_ms: int = 2000):
        """随机延迟"""
        delay = random.uniform(min_ms, max_ms) / 1000
        time.sleep(delay)
    
    @staticmethod
    def human_type(driver, element, text, delay_range=(50, 150)):
        """模拟人类打字速度"""
        try:
            element.click()
            HumanBehaviorSimulator.random_delay(300, 800)
            
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(*delay_range) / 1000)
                # 偶尔停顿（模拟思考）
                if random.random() < 0.1:
                    time.sleep(random.uniform(0.3, 1.0))
        except Exception as e:
            print(f"⚠️  打字模拟失败: {e}")
            # 降级方案：直接输入
            element.send_keys(text)
    
    @staticmethod
    def scroll_smoothly(driver, distance: int = 300):
        """平滑滚动"""
        try:
            steps = random.randint(5, 10)
            step_distance = distance / steps
            
            for _ in range(steps):
                driver.execute_script(f"window.scrollBy(0, {step_distance})")
                time.sleep(random.uniform(0.05, 0.15))
        except:
            pass
    
    @staticmethod
    def warmup_page(driver):
        """页面预热 - 模拟真实用户行为"""
        print("   🔥 页面预热中...")
        
        # 随机滚动
        HumanBehaviorSimulator.scroll_smoothly(driver, random.randint(100, 300))
        HumanBehaviorSimulator.random_delay(500, 1500)
        
        # 随机移动鼠标
        try:
            action = ActionChains(driver)
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                action.move_by_offset(x - 400, y - 300).perform()
                action.reset_actions()
                HumanBehaviorSimulator.random_delay(200, 600)
        except:
            pass
        
        print("   ✅ 预热完成")


def create_driver():
    """创建 undetected Chrome 驱动"""
    print("🌐 启动反检测浏览器...")
    print("   ⚠️  请确保已关闭所有 Chrome 窗口")
    
    # 确保用户数据目录存在
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 指定 Chrome 版本以匹配系统安装的 Chrome
    version_main_env = os.environ.get("XPOST_CHROME_VERSION_MAIN")
    try:
        version_main = int(version_main_env) if version_main_env else 145
    except ValueError:
        version_main = 145

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")  # macOS 必需

    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=version_main
    )
    print("✅ 浏览器已启动（反检测模式）")
    return driver


def check_login_status(driver):
    """检查是否已登录"""
    try:
        # 检查 URL 是否包含 login
        if "login" in driver.current_url.lower() or "flow/login" in driver.current_url.lower():
            return False
        
        # 检查是否存在登录按钮
        login_indicators = [
            'a[href="/login"]',
            'a[href*="flow/login"]',
        ]
        
        for selector in login_indicators:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    print(f"   ℹ️  发现登录按钮: {selector}")
                    return False
            except NoSuchElementException:
                continue
        
        return True
    except Exception:
        return True  # 如果无法确定，假设已登录


def wait_for_login(driver, timeout=300):
    """等待用户手动登录"""
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
        if check_login_status(driver):
            print("✅ 登录成功！")
            return True
        time.sleep(3)
    
    print("❌ 登录超时")
    return False


def click_write_button(driver):
    """检查并点击 Write 按钮（如果需要）"""
    write_selectors = [
        'a[data-testid="empty_state_button_text"]',
        'a[href="/compose/articles/new"]',
        'div[role="button"][aria-label="Write"]',
    ]
    
    for selector in write_selectors:
        try:
            write_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            print("   👈 点击 'Write' 按钮...")
            write_btn.click()
            HumanBehaviorSimulator.random_delay(2000, 4000)
            return True
        except:
            continue
    return False


def input_title(driver, title):
    """输入文章标题"""
    print(f"✍️  [4/7] 输入标题...")
    
    title_selectors = [
        'textarea[placeholder="Add a title"]',
        'textarea[name="Article Title"]',
        'input[placeholder*="标题"]',
        'textarea[placeholder*="标题"]',
        'div[contenteditable="true"]',
    ]
    
    for selector in title_selectors:
        try:
            title_input = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            title_input.click()
            HumanBehaviorSimulator.random_delay(500, 1000)
            title_input.clear()
            title_input.send_keys(title)
            print(f"✅ 标题已输入: {title}")
            return True
        except:
            continue
    
    print("⚠️  未找到标题输入框，请手动输入")
    # 尝试备用方案：直接键盘输入
    try:
        ActionChains(driver).send_keys(title).perform()
    except:
        pass
    return False


def paste_content(driver, html_content):
    """粘贴文章内容（HTML格式）"""
    print("📝 [5/7] 粘贴文章内容...")
    
    try:
        # 复制 HTML 到剪贴板
        copy_html_to_clipboard(html_content)
        HumanBehaviorSimulator.random_delay(500, 1000)
        
        # 查找内容编辑区域
        content_selectors = [
            'div[contenteditable="true"][data-testid="article"]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
            'div.public-DraftEditor-content',
        ]
        
        for selector in content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                # 通常第二个 contenteditable 是内容区域（第一个是标题）
                content_area = elements[1] if len(elements) > 1 else (elements[0] if elements else None)
                
                if content_area:
                    content_area.click()
                    HumanBehaviorSimulator.random_delay(500, 1000)
                    
                    # 粘贴内容 (Command+V)
                    ActionChains(driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                    
                    HumanBehaviorSimulator.random_delay(2000, 3000)
                    print(f"✅ 内容已粘贴 ({len(html_content)} 字符)")
                    return True
            except:
                continue
        
        print("⚠️  未找到内容编辑区域")
        return False
        
    except Exception as e:
        print(f"⚠️  内容粘贴失败: {e}")
        return False


def get_editor_image_count(driver):
    """统计编辑器内部图片数量"""
    try:
        editor_selectors = [
            'div[contenteditable="true"][data-testid="article"]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ]
        
        for selector in editor_selectors:
            try:
                editors = driver.find_elements(By.CSS_SELECTOR, selector)
                if len(editors) > 1:
                    editor = editors[1]  # 内容编辑器
                elif editors:
                    editor = editors[0]
                else:
                    continue
                    
                imgs = editor.find_elements(By.TAG_NAME, "img")
                return len(imgs)
            except:
                continue
        return 0
    except:
        return 0


def find_placeholder_and_select(driver, placeholder):
    """在编辑器中查找占位符文本并选中它"""
    try:
        print(f"   🔍 搜索占位符: {placeholder[:40]}...")
        
        # 使用 JavaScript 在编辑器内搜索并选中占位符
        selected = driver.execute_script('''
            const placeholder = arguments[0];
            const editors = document.querySelectorAll('div[contenteditable="true"]');
            const editor = editors.length > 1 ? editors[1] : editors[0];
            if (!editor) return false;
            
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
                    const range = document.createRange();
                    range.setStart(node, index);
                    range.setEnd(node, index + placeholder.length);
                    
                    const selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    
                    node.parentElement.scrollIntoView({ block: 'center' });
                    return true;
                }
            }
            return false;
        ''', placeholder)
        
        if selected:
            print(f"   ✅ 已选中占位符文本")
            HumanBehaviorSimulator.random_delay(300, 500)
            return True
        else:
            print(f"   ⚠️  未找到占位符: {placeholder}")
            return False
            
    except Exception as e:
        print(f"   ⚠️  占位符搜索失败: {e}")
        return False


def wait_for_image_upload(driver, timeout=15):
    """等待图片上传完成"""
    try:
        print(f"   ⏳ 等待图片上传（最多 {timeout} 秒）...")
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'img[src*="pbs.twimg.com"]'))
        )
        print("   ✅ 图片上传完成")
        return True
    except:
        print("   ⚠️  上传检测超时（继续执行）")
        return False


def insert_content_images(driver, content_images):
    """插入内容图片"""
    if not content_images:
        return
    
    print(f"🖼️  [6/7] 插入内容图片 ({len(content_images)} 张)...")
    
    for idx, img in enumerate(content_images, 1):
        if not img.get('exists', False):
            continue
        
        print(f"\n   图片 {idx}/{len(content_images)}: {img['path']}")
        
        placeholder = img.get('placeholder', '')
        
        try:
            # 使用占位符定位
            found = False
            used_placeholder = False
            
            if placeholder:
                print(f"   📍 使用占位符定位: {placeholder}")
                found = find_placeholder_and_select(driver, placeholder)
                if found:
                    used_placeholder = True
            
            if found:
                before_count = get_editor_image_count(driver)
                print(f"   🔎 插入前图片数量: {before_count}")
                
                # 如果使用占位符定位，先删除选中的占位符文本
                if used_placeholder:
                    print(f"   🗑️  删除占位符文本...")
                    ActionChains(driver).send_keys(Keys.DELETE).perform()
                    HumanBehaviorSimulator.random_delay(300, 500)
                
                # 复制图片到剪贴板
                copy_image_to_clipboard(img['path'], quality=85)
                HumanBehaviorSimulator.random_delay(500, 1000)
                
                # 粘贴图片 (Command+V)
                print(f"   📋 执行粘贴...")
                ActionChains(driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                
                HumanBehaviorSimulator.random_delay(1000, 1500)
                
                # 等待图片上传
                wait_for_image_upload(driver, timeout=15)
                
                after_count = get_editor_image_count(driver)
                if after_count > before_count:
                    print(f"   ✅ 图片 {idx} 已成功插入")
                else:
                    print(f"   ⚠️  图片 {idx} 插入可能失败，请检查")
            else:
                print(f"   ⚠️  未找到插入位置，跳过")
        
        except Exception as e:
            print(f"   ⚠️  插入失败: {e}")
        
        HumanBehaviorSimulator.random_delay(1000, 2000)
    
    print()


def insert_cover_image(driver, cover_image, cover_exists):
    """插入封面图"""
    if not cover_image or not cover_exists:
        return
    
    print("🖼️  [7/7] 插入封面图...")
    cover_uploaded = False
    
    try:
        # 方法1：使用 file input 上传
        try:
            file_input = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
            file_input.send_keys(str(cover_image))
            print(f"✅ 封面图已上传 (File Input): {cover_image}")
            cover_uploaded = True
        except Exception as e:
            print(f"   ℹ️  File Input 方式不可用: {e}")
        
        # 方法2：点击上传按钮后粘贴
        if not cover_uploaded:
            copy_image_to_clipboard(cover_image, quality=85)
            HumanBehaviorSimulator.random_delay(500, 1000)
            
            cover_selectors = [
                'div[data-testid*="cover"]',
                'button[aria-label*="Cover"]',
                'button[aria-label*="封面"]',
            ]
            
            for selector in cover_selectors:
                try:
                    cover_btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    cover_btn.click()
                    HumanBehaviorSimulator.random_delay(500, 1000)
                    
                    # 粘贴 (Command+V)
                    ActionChains(driver).key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND).perform()
                    
                    HumanBehaviorSimulator.random_delay(2000, 3000)
                    print(f"✅ 封面图已粘贴: {cover_image}")
                    cover_uploaded = True
                    break
                except:
                    continue
        
        # 处理 Apply 弹窗
        if cover_uploaded:
            try:
                print("   ⏳ 等待图片编辑器弹窗...")
                HumanBehaviorSimulator.random_delay(2000, 3000)
                
                apply_selectors = [
                    'button[data-testid="applyButton"]',
                    'button:contains("Apply")',
                ]
                
                for selector in apply_selectors:
                    try:
                        apply_btn = WebDriverWait(driver, 2).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        print(f"   👈 点击 'Apply' 确认封面...")
                        apply_btn.click()
                        HumanBehaviorSimulator.random_delay(1000, 2000)
                        print("   ✅ 封面已应用")
                        break
                    except:
                        continue
            except:
                pass
        
        if not cover_uploaded:
            print("⚠️  未找到封面图上传按钮，请手动上传")
    
    except Exception as e:
        print(f"⚠️  封面图插入失败: {e}")
    
    print()


def click_publish_button(driver):
    """点击发布按钮"""
    print("🚀 [8/+] 自动点击发布...")
    
    publish_selectors = [
        'button[data-testid="tweetButtonInline"]',
        'div[role="button"]:contains("Publish")',
        'button:contains("Publish")',
    ]
    
    for selector in publish_selectors:
        try:
            publish_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            print(f"   找到发布按钮: {selector}")
            publish_btn.click()
            HumanBehaviorSimulator.random_delay(2000, 3000)
            
            # 可能有确认弹窗
            try:
                confirm_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="confirmationSheetConfirm"]'))
                )
                confirm_btn.click()
                print("   ✅ 已确认发布")
            except:
                pass
            
            print("✅ 发布成功！")
            return True
        except:
            continue
    
    print("⚠️  未找到发布按钮，请手动发布")
    return False


def auto_publish_article(markdown_file: str, publish: bool = False):
    """全自动发布文章主流程"""
    
    print("=" * 80)
    print("🤖 X Article 全自动发布系统 (undetected-chromedriver 版)")
    print("=" * 80)
    print()
    
    # 解析 Markdown
    print("📄 [1/7] 解析 Markdown 文件...")
    result = parse_markdown_file(markdown_file)
    print(f"✅ 解析成功")
    print(f"   📌 标题: {result['title']}")
    print(f"   🖼️  封面图: {result['cover_image'] or '无'}")
    print(f"   🖼️  内容图片: {len(result['content_images'])} 张")
    print()
    
    driver = None
    try:
        # 创建浏览器
        print("🌐 [2/7] 启动隐身浏览器...")
        driver = create_driver()
        print()
        
        # 打开 Articles 页面
        print("🔗 [3/7] 打开 X Articles 编辑器...")
        driver.get(ARTICLES_URL)
        HumanBehaviorSimulator.random_delay(2000, 4000)
        print("✅ 页面已加载")
        
        # 检查登录状态
        if not check_login_status(driver):
            if not wait_for_login(driver):
                print("❌ 登录失败，退出")
                return False
        else:
            print("✅ 已登录")
        
        # 点击 Write 按钮（如果需要）
        click_write_button(driver)
        
        # 页面预热
        HumanBehaviorSimulator.warmup_page(driver)
        print()
        
        # 输入标题
        input_title(driver, result['title'])
        HumanBehaviorSimulator.random_delay(1000, 2000)
        print()
        
        # 粘贴内容
        paste_content(driver, result['html'])
        print()
        
        # 插入内容图片
        insert_content_images(driver, result['content_images'])
        
        # 插入封面图
        insert_cover_image(driver, result['cover_image'], result['cover_exists'])
        
        # 完成
        print("=" * 80)
        print("✅ 自动化流程完成！")
        print("=" * 80)
        print()
        print("📋 请在浏览器中：")
        print("   1. 检查内容是否正确")
        print("   2. 预览文章")
        
        if publish:
            click_publish_button(driver)
        else:
            print("   3. 手动点击「保存草稿」或「发布」 (未开启 --publish)")
            print()
            if os.environ.get("XPOST_NO_WAIT") != "1":
                input("按 Enter 键关闭浏览器...")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if driver:
            print("\n🧹 正在释放浏览器资源...")
            try:
                driver.quit()
            except:
                pass
            print("✅ 完成")


def main():
    parser = argparse.ArgumentParser(description='X Article 全自动发布系统')
    parser.add_argument('markdown_file', help='Markdown 文件路径')
    parser.add_argument('--publish', action='store_true', help='直接发布（默认保存草稿）')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.markdown_file):
        print(f"❌ 文件不存在: {args.markdown_file}")
        sys.exit(1)
    
    success = auto_publish_article(args.markdown_file, args.publish)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
