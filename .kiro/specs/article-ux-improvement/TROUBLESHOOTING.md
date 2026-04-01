# 故障排查指南

## 问题：看不到新界面（风格选择器、浮动面板等）

### 原因分析
你看到的可能是**浏览器缓存的旧版本代码**。

### 解决方案

#### 方案 1：硬刷新浏览器（推荐）
1. 在浏览器中按：
   - **Mac**: `Cmd + Shift + R`
   - **Windows/Linux**: `Ctrl + Shift + R`
2. 或者右键点击刷新按钮 → 选择"清空缓存并硬性重新加载"

#### 方案 2：清除浏览器缓存
1. 打开开发者工具（F12）
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

#### 方案 3：无痕模式测试
1. 打开无痕窗口：
   - **Mac**: `Cmd + Shift + N`
   - **Windows/Linux**: `Ctrl + Shift + N`
2. 访问 http://localhost:5901/articles

#### 方案 4：重启前端开发服务器
```bash
# 停止当前服务器（Ctrl+C）
# 然后重新启动
cd web/ui
npm run dev
```

## 验证新界面是否加载

打开浏览器开发者工具（F12），在 Console 中输入：

```javascript
// 检查新组件是否存在
document.querySelector('.compact-header')  // 应该返回 DOM 元素
document.querySelector('.floating-panel')  // 应该返回 DOM 元素
document.querySelector('.style-selector')  // 应该返回 select 元素
```

如果返回 `null`，说明新组件没有加载，需要清除缓存。

## 预期界面特征

### ✅ 新界面应该有：
1. **顶部**：
   - 高度约 60px（很紧凑）
   - 有"← 返回"按钮
   - 标题输入框
   - **风格选择器下拉菜单**（Zara 风格/技术风格/趣味风格）
   - 步骤徽章（标题/骨架/内容）
   - 状态徽章（草稿/已发布）

2. **右下角**：
   - **浮动操作面板**（白色圆角卡片）
   - 保存状态显示
   - "一键生成"或"发布文章"按钮
   - 预览切换按钮（眼睛图标）

3. **编辑器**：
   - 工具栏有"插入图片"按钮
   - 左右分屏（编辑器 + 预览）

### ❌ 旧界面特征：
1. 顶部有大的步骤指示器（占用很多空间）
2. 按钮分散在各处（不是浮动面板）
3. 没有风格选择器
4. 没有"一键生成"按钮（只有"生成骨架"和"生成全文"分开的按钮）

## 如果还是看到旧界面

### 检查文件是否真的更新了

```bash
# 检查 ArticleEditorPage.vue 是否包含新组件
grep -n "CompactHeader" web/ui/src/views/ArticleEditorPage.vue
grep -n "FloatingActionPanel" web/ui/src/views/ArticleEditorPage.vue
grep -n "ProgressIndicator" web/ui/src/views/ArticleEditorPage.vue

# 应该看到这些组件的导入和使用
```

### 检查 Vite 是否检测到文件变化

查看前端开发服务器的终端输出，应该看到：
```
1:30:00 PM [vite] page reload web/ui/src/views/ArticleEditorPage.vue
1:30:00 PM [vite] hmr update /src/views/ArticleEditorPage.vue
```

如果没有看到，说明 Vite 没有检测到文件变化，需要手动重启。

## 当前实现的完整功能列表

### 后端 API（已实现）
- ✅ `POST /api/articles/{id}/auto-generate?style=zara` - 一键生成
- ✅ `POST /api/articles/{id}/images` - 图片上传
- ✅ `POST /api/articles/{id}/cancel` - 取消生成

### 前端组件（已实现）
- ✅ `CompactHeader.vue` - 紧凑头部（含风格选择器）
- ✅ `FloatingActionPanel.vue` - 浮动操作面板
- ✅ `ProgressIndicator.vue` - 进度指示器
- ✅ `useWorkflowOrchestrator.js` - 工作流编排器
- ✅ `MarkdownEditor.vue` - 增强版编辑器（自动保存 + 图片插入）
- ✅ `ArticleEditorPage.vue` - 集成所有新组件

### 用户体验（已实现）
- ✅ 风格选择（zara/tech/fun）
- ✅ 一键生成（自动完成 outline → content）
- ✅ 自动保存（3 秒延迟）
- ✅ 图片插入（拖拽/点击/粘贴）
- ✅ 键盘快捷键（Cmd+S, Cmd+Enter, Cmd+P）
- ✅ 实时进度显示
- ✅ 取消生成

## 下一步

1. **硬刷新浏览器**（Cmd+Shift+R）
2. 如果还是看到旧界面，告诉我你看到的具体内容
3. 我会帮你进一步诊断问题
