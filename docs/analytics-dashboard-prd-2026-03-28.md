# Analytics 数据看板 — PRD

日期：2026-03-28  
状态：待实现  
优先级：P1

---

## 1. 背景与价值

gitxPost 已积累三层数据：
- `xinfo/log/trends/*.json`：按周聚合的关键词频率
- `xinfo/log/runtime/*_radar-daily.jsonl`：每日雷达扫描结果
- `xinfo/log/week/*.md`：周报 Markdown

但当前 Web UI（Dashboard）只有 4 个静态数字卡片，**没有任何图表**，无法从数据中发现趋势和信号。

**核心价值**：
- 选题决策：看哪个关键词在上涨，下周发什么内容
- 账号策略：发现新兴话题，判断是否扩充监控账号
- 异常发现：数量级突变一眼识别（Week 12 agent 从 102→2164）
- 产品差异化：数据可视化是 gitxPost 对外展示的核心竞争力

---

## 2. 功能范围（MVP）

### 2.1 关键词趋势折线图

**数据源**：`xinfo/log/trends/YYYY-WW.json`

**展示内容**：
- X 轴：周次（如 Week-10、Week-11、Week-12）
- Y 轴：关键词出现频次
- 多条折线：用户可选择展示哪些关键词（默认展示 Top 5）
- 支持点击图例显示/隐藏单条线

**交互**：
- 默认展示全部已有周次数据
- Hover 显示具体数值
- 支持按关键词搜索过滤

**示例数据对比**（已验证）：
```
关键词   Week-10  Week-11  Week-12
agent      102      111     2164   ← 20x 爆发
codex       92       63     1184   ← 13x 爆发
龙虾       126       59     1173   ← 持续高热
skills      --      122      680   ← 回落
gemini      --       --      794   ← 新进榜
```

### 2.2 每日新增推文趋势

**数据源**：`xinfo/log/runtime/*_radar-daily.jsonl`

**展示内容**：
- 柱状图：每日新增推文数量
- X 轴：日期（最近 14 天）
- Y 轴：推文数量
- 颜色区分：原创帖 vs 转发/回复

### 2.3 账号活跃度统计

**数据源**：`xinfo/RESULT.json` 或 `/api/radar/result`

**展示内容**：
- 各监控账号的发帖频率
- 原创率排行（Top 10）

---

## 3. 技术方案

### 3.1 后端 API（`web/api/server.py`）

需新增两个接口：

```python
# 返回所有周的关键词趋势数据，合并为时间序列
GET /api/analytics/keyword-trends
# 响应示例：
{
  "weeks": ["2026-10", "2026-11", "2026-12"],
  "series": {
    "agent": [102, 111, 2164],
    "codex": [92, 63, 1184],
    "龙虾": [126, 59, 1173]
  }
}

# 返回最近 N 天的每日新增推文数
GET /api/analytics/daily-stats?days=14
# 响应示例：
{
  "dates": ["2026-03-15", "2026-03-16", ...],
  "new_tweets": [42, 38, 55, ...],
  "new_originals": [12, 8, 15, ...]
}
```

**实现要点**：
- 读取 `xinfo/log/trends/` 目录下所有 `YYYY-WW.json`，按 week 字段排序合并
- 读取 `xinfo/log/runtime/` 目录下 `*_radar-daily.jsonl`，按日期聚合
- 两个接口都是只读，无副作用

### 3.2 前端（`web/ui/src/`）

**新增文件**：
- `web/ui/src/views/AnalyticsPage.vue` — 主页面
- `web/ui/src/components/KeywordTrendChart.vue` — 折线图组件
- `web/ui/src/components/DailyBarChart.vue` — 柱状图组件

**图表库选择**（二选一）：
- 推荐：[Chart.js](https://www.chartjs.org/) — 轻量，Vue 可用 `vue-chartjs` wrapper
- 备选：纯 SVG 手写 — 零依赖，但开发成本高

**路由注册**（`web/ui/src/router.js`）：
```js
{ path: '/analytics', component: AnalyticsPage, name: 'analytics' }
```

**导航栏**（`web/ui/src/App.vue` 或 sidebar）：
新增「数据分析」导航入口。

---

## 4. 验收标准

- [ ] `/analytics` 页面可正常访问，不报错
- [ ] 关键词趋势折线图正确展示已有 3 周数据
- [ ] agent 关键词 Week-10/11/12 数值显示为 102/111/2164
- [ ] 可点击图例隐藏/显示单条折线
- [ ] 每日推文柱状图展示最近 14 天（或有数据的天数）
- [ ] 移动端（375px）可正常查看，图表不溢出
- [ ] 无已有功能回归（Dashboard、RadarDaily 正常）

---

## 5. 不在范围内（本期不做）

- 实时数据推送（WebSocket）
- 账号维度的单独趋势分析
- 导出 CSV/图片功能
- 时间范围自定义筛选器

---

## 6. 数据文件位置参考

```
xinfo/
├── log/
│   ├── trends/
│   │   ├── 2026-10.json   # Week 10 关键词频率
│   │   ├── 2026-11.json   # Week 11 关键词频率
│   │   └── 2026-12.json   # Week 12 关键词频率
│   ├── runtime/
│   │   ├── 2026-03-19_radar-daily.jsonl
│   │   ├── 2026-03-20_radar-daily.jsonl
│   │   └── ...            # 每日扫描结果
│   └── week/
│       ├── 2026-03-24.md
│       └── 2026-03-25.md
└── RESULT.json            # 最新扫描完整结果
```

---

## 7. 工作量估算

| 模块 | 估算 |
|------|------|
| 后端两个 API | 2-3 小时 |
| 前端 AnalyticsPage + 折线图 | 3-4 小时 |
| 前端柱状图 | 1-2 小时 |
| 联调 + 验收 | 1 小时 |
| **合计** | **约 7-10 小时** |
