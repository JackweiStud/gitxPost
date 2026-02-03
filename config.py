# X Article 自动发布配置文件

## 反机器人检测配置

### 时间延迟配置（毫秒）
DELAYS = {
    # 基础延迟
    "min_action_delay": 500,      # 最小操作延迟
    "max_action_delay": 2000,     # 最大操作延迟
    
    # 打字速度
    "min_typing_delay": 50,       # 最小打字延迟（每个字符）
    "max_typing_delay": 150,      # 最大打字延迟
    
    # 页面加载
    "page_load_wait": 3000,       # 页面加载等待
    "after_paste_wait": 2000,     # 粘贴后等待
    
    # 图片操作
    "image_upload_wait": 2000,    # 图片上传等待
    "between_images": 1500,       # 图片之间的间隔
}

### 人类行为模拟
HUMAN_BEHAVIOR = {
    # 思考停顿概率（0-1）
    "thinking_pause_probability": 0.1,
    "thinking_pause_duration": (300, 1000),  # 毫秒
    
    # 鼠标移动
    "mouse_move_steps": (5, 10),  # 移动步数范围
    
    # 滚动行为
    "scroll_distance": (100, 300),  # 滚动距离范围
    "scroll_steps": (5, 10),        # 滚动步数
    
    # 预热行为
    "warmup_mouse_moves": (2, 4),   # 预热时鼠标移动次数
    "warmup_scroll": True,          # 是否预热滚动
}

### 浏览器配置
BROWSER_CONFIG = {
    "headless": False,              # 是否无头模式
    "slow_mo": 50,                  # 全局减速（毫秒）
    "locale": "zh-CN",
    "timezone": "Asia/Shanghai",
    
    # User Agent
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

### 重试配置
RETRY_CONFIG = {
    "max_retries": 3,               # 最大重试次数
    "retry_delay": (2000, 5000),    # 重试延迟范围
    "timeout": 10000,               # 元素查找超时（毫秒）
}

### 选择器配置（X Article 编辑器）
SELECTORS = {
    # 标题输入框
    "title": [
        'input[placeholder*="标题"]',
        'input[placeholder*="Title"]',
        'div[contenteditable="true"]',
        'textarea[placeholder*="标题"]',
    ],
    
    # 内容编辑区域
    "content": [
        'div[contenteditable="true"][data-testid*="article"]',
        'div[contenteditable="true"]:not([placeholder*="标题"])',
        'div.public-DraftEditor-content',
    ],
    
    # 封面图按钮
    "cover": [
        'button[aria-label*="封面"]',
        'button[aria-label*="Cover"]',
        'div[data-testid*="cover"]',
    ],
    
    # 发布按钮
    "publish": [
        'button[data-testid*="publish"]',
        'button:has-text("发布")',
        'button:has-text("Publish")',
    ],
}

### 图片质量配置
IMAGE_CONFIG = {
    "cover_quality": 85,            # 封面图质量（1-100）
    "content_quality": 85,          # 内容图片质量
    "max_width": 2000,              # 最大宽度（像素）
    "max_height": 2000,             # 最大高度
}
