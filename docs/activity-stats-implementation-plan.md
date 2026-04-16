# 活动统计功能实现方案

**目标**: 在粉丝统计采集中增加单一活动指标 `activity_24h`，表示“采集执行时刻往前 24 小时内，本人出现在 `/with_replies` 时间线中的内容总数（含原帖与回复）”。

**更新日期**: 2026-04-16

---

## 核心需求

1. **统计口径统一**: 与雷达日报一致，按过去 24 小时滑动窗口统计。
2. **字段语义准确**: 只保留 `activity_24h`，不再区分 `posts`、`replies`、`articles`。
3. **历史数据兼容**: 将 `followers.json` 中旧字段迁移为新结构。
4. **输出简单稳定**: CLI 与 JSON 输出统一展示 `activity_24h`。

---

## 数据流

```text
用户触发采集
  ↓
fetch_follower_stats.py
  ↓
采集粉丝数 / 关注数
  ↓
打开 /<user>/with_replies
  ↓
滚动抓取 (status_id, datetime)
  ↓
按 status_id 去重
  ↓
过滤过去 24 小时
  ↓
输出 activity_24h
  ↓
写入 xinfo/log/followers.json
```

---

## 数据存储格式

### 当前格式

```json
{
  "username": "jackaiwison",
  "records": [
    {
      "date": "2026-04-16",
      "time": "10:39:54",
      "followers": 88,
      "following": 511,
      "activity_24h": 3
    }
  ]
}
```

### 字段说明

- `followers`: 当前粉丝数
- `following`: 当前关注数
- `activity_24h`: 过去 24 小时内的活动总数（含原帖与回复）

---

## 后端实现

### 1. `fetch_activity_stats()`

在 [`fetch_follower_stats.py`](../fetch_follower_stats.py) 中：

- 只访问 `https://x.com/<username>/with_replies`
- 解析每个推文块中的：
  - `status_id`
  - `time[datetime]`
- 使用 `status_id` 去重
- 将 `datetime` 转为 UTC 后与 `now_utc - 24h` 比较
- 最终返回：

```python
{
    "activity_24h": 3,
    "activity_ok": True,
}
```

### 2. 历史数据迁移

保存前统一迁移旧记录：

- 若已有 `activity_24h`，直接保留
- 若仅有 `posts/replies/articles`，则：

```text
activity_24h = posts + replies + articles
```

- 然后删除旧字段
- 若旧记录完全没有活动字段，则补 `activity_24h: 0`

### 3. 失败保护

若本次活动采集失败：

- 不覆盖当日已有的 `activity_24h`
- 仅更新粉丝 / 关注数

---

## CLI 输出

### JSON 输出

```json
{
  "ok": true,
  "username": "jackaiwison",
  "followers": 88,
  "following": 511,
  "activity_24h": 3,
  "activity_ok": true,
  "date": "2026-04-16",
  "time": "10:39:54"
}
```

### 终端输出

```text
📊 @jackaiwison 数据统计
  👥 Followers: 88
  👤 Following: 511
  📝 Activity(24h): 3
  ✅ 近 24 小时活动采集: 成功
```

---

## 设计取舍

### 为什么不再区分 Posts / Replies / Articles

1. `/with_replies` 已经天然包含原帖和回复。
2. `article` 识别链路未真正接入主流程，维护成本高且结果不可靠。
3. `posts/replies` 的区分依赖较脆弱的 DOM 线索，复杂度高。
4. 当前业务目标只是回答：**“过去 24 小时我活跃了多少次？”**

### 为什么使用过去 24 小时

1. 与雷达日报口径一致。
2. 避免本地日 / UTC 日边界混乱。
3. 不依赖本地时区切换，适合全球内容采集场景。

---

## 验证建议

1. 运行 `python3 -m py_compile fetch_follower_stats.py`
2. 运行一次真实采集，确认输出只包含 `activity_24h`
3. 检查 `xinfo/log/followers.json` 已无 `posts/replies/articles`
4. 抽样核对某个账号过去 24 小时内在 `/with_replies` 页面可见的内容数

---

## 边界说明

- `activity_24h` 统计的是 **过去 24 小时的总活动量**，不是自然日统计。
- 该值来自 X 的虚拟列表页面，极端情况下深层内容可能因为未加载完全而少计。
- 当前版本不再回答“其中多少是原帖、多少是回复、多少是长文”，若未来有稳定需求再单独细分。
