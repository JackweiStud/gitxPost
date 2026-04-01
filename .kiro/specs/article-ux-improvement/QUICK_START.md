# 快速开始 - 修复界面显示问题

## 🎯 目标
让新的文章工作站界面正确显示（风格选择器、浮动面板、一键生成按钮）

## ⚡ 快速执行步骤

### 步骤 1：重启前后端服务器
```bash
# 停止当前服务器（如果在运行）
# 按 Ctrl+C

# 清理前端缓存
rm -rf web/ui/node_modules/.vite

# 使用统一启动脚本
bash web/start.sh

# 等待看到：
# =========================================
#   gitxPost Web UI
# =========================================
#   后端 API:  http://127.0.0.1:8900
#   前端 UI:   http://127.0.0.1:5900
#   按 Ctrl+C 停止所有服务
# =========================================
```

### 步骤 2：访问并验证
1. 打开浏览器：`http://127.0.0.1:5900/articles`
2. 点击任意文章进入编辑页
3. **硬刷新**：Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows)

### 步骤 3：检查新界面
应该看到：
- ✅ 顶部有风格选择器下拉菜单（Zara 风格 ▼）
- ✅ 右下角有浮动操作面板（白色卡片）
- ✅ 有"一键生成"按钮

如果还是看到旧界面：
- ❌ 只有"Zara 风格"文本（不是下拉菜单）
- ❌ 有"骨架"和"生成中"按钮

说明缓存还没清除，继续下一步。

### 步骤 4：如果还不行，完全重建
```bash
# 停止服务器（Ctrl+C）

# 删除所有缓存
rm -rf web/ui/node_modules/.vite
rm -rf web/ui/dist
rm -rf web/ui/.vite

# 重新安装依赖
cd web/ui && npm install

# 返回根目录，重新启动
cd ../..
bash web/start.sh
```

## 🔍 验证命令

在浏览器 Console (F12) 中输入：
```javascript
// 检查新组件是否存在
document.querySelector('.compact-header')
document.querySelector('.floating-panel')
document.querySelector('.style-selector')

// 如果都返回 DOM 元素（不是 null），说明新界面已加载
```

## 📁 关键文件位置

**已实现的组件**：
- `web/ui/src/components/CompactHeader.vue` - 紧凑头部
- `web/ui/src/components/FloatingActionPanel.vue` - 浮动面板
- `web/ui/src/components/ProgressIndicator.vue` - 进度指示器
- `web/ui/src/composables/useWorkflowOrchestrator.js` - 工作流编排
- `web/ui/src/views/ArticleEditorPage.vue` - 主页面（已重构）

**后端 API**：
- `web/api/server.py` 第 1930 行：auto-generate 端点
- `web/api/server.py` 第 1976 行：图片上传端点
- `web/api/server.py` 第 1754 行：取消生成端点

## 📖 详细文档

- 完整交接文档：`.kiro/specs/article-ux-improvement/HANDOVER.md`
- 界面预览：`.kiro/specs/article-ux-improvement/UI_PREVIEW.md`
- 测试指南：`.kiro/specs/article-ux-improvement/TESTING_GUIDE.md`

## ⚠️ 常见问题

**Q: 重启后还是看到旧界面？**
A: 硬刷新浏览器（Cmd+Shift+R），或者用无痕模式测试

**Q: Console 有错误？**
A: 检查后端服务器是否在运行（http://127.0.0.1:8900/api/status）

**Q: 组件找不到？**
A: 检查文件是否存在：`ls web/ui/src/components/CompactHeader.vue`

---

**核心问题**：代码已全部实现，只是前端服务器需要重启以重新编译。
