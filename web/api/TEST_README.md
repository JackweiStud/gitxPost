# Article CRUD API 集成测试

## 概述

本测试套件为 X Article 创作工作站的 CRUD API 提供全面的集成测试覆盖。

## 测试覆盖

### 1. 创建文章 (POST /api/articles)
- ✅ 有效标题创建文章
- ✅ 空标题验证（400 错误）
- ✅ 仅空格标题验证（400 错误）
- ✅ 自动去除首尾空格
- ✅ 多篇文章 ID 唯一性

### 2. 获取文章列表 (GET /api/articles)
- ✅ 空列表返回
- ✅ 多篇文章列表
- ✅ 按 updated_at 倒序排列
- ✅ 列表不包含 content 字段

### 3. 获取文章详情 (GET /api/articles/{id})
- ✅ 成功获取详情
- ✅ 文章不存在返回 404
- ✅ 详情包含 content 字段
- ✅ 包含 Markdown 内容

### 4. 更新文章内容 (PUT /api/articles/{id})
- ✅ 成功更新内容
- ✅ updated_at 时间戳更新
- ✅ 文章不存在返回 404
- ✅ 允许空内容
- ✅ 保留元数据

### 5. 删除文章 (DELETE /api/articles/{id})
- ✅ 成功删除文章
- ✅ 文章不存在返回 404
- ✅ 从列表中移除
- ✅ 删除后无法获取
- ✅ 删除 JSON 和 Markdown 文件

### 6. 错误处理
- ✅ 无效文章 ID 格式（404）
- ✅ 缺少必需字段（422）
- ✅ 并发操作原子性

### 7. 数据持久化
- ✅ 文章数据持久化
- ✅ 数据往返一致性

## 安装依赖

```bash
cd web/api
pip install -r requirements.txt
```

## 运行测试

### 运行所有测试
```bash
cd web/api
python test_articles_api.py
```

或使用 pytest 命令：
```bash
cd web/api
pytest test_articles_api.py -v
```

### 运行特定测试
```bash
# 运行创建文章相关测试
pytest test_articles_api.py -k "test_create" -v

# 运行错误处理测试
pytest test_articles_api.py -k "test_error" -v

# 运行删除文章测试
pytest test_articles_api.py -k "test_delete" -v
```

### 查看详细输出
```bash
pytest test_articles_api.py -v --tb=short
```

### 查看测试覆盖率
```bash
pip install pytest-cov
pytest test_articles_api.py --cov=server --cov-report=html
```

## 测试数据

测试使用独立的测试目录 `web/api/test_data/articles/`，不会影响生产数据。每个测试前后会自动清理测试数据。

## 测试结果示例

```
test_articles_api.py::test_create_article_with_valid_title PASSED           [  4%]
test_articles_api.py::test_create_article_with_empty_title PASSED           [  8%]
test_articles_api.py::test_create_article_with_whitespace_title PASSED      [ 12%]
test_articles_api.py::test_create_article_trims_whitespace PASSED           [ 16%]
test_articles_api.py::test_create_multiple_articles_unique_ids PASSED       [ 20%]
test_articles_api.py::test_get_articles_empty_list PASSED                   [ 24%]
test_articles_api.py::test_get_articles_list PASSED                         [ 28%]
test_articles_api.py::test_get_articles_sorted_by_updated_at PASSED         [ 32%]
test_articles_api.py::test_get_article_detail PASSED                        [ 36%]
test_articles_api.py::test_get_article_not_found PASSED                     [ 40%]
test_articles_api.py::test_get_article_with_content PASSED                  [ 44%]
test_articles_api.py::test_update_article_content PASSED                    [ 48%]
test_articles_api.py::test_update_article_updates_timestamp PASSED          [ 52%]
test_articles_api.py::test_update_article_not_found PASSED                  [ 56%]
test_articles_api.py::test_update_article_with_empty_content PASSED         [ 60%]
test_articles_api.py::test_update_article_preserves_metadata PASSED         [ 64%]
test_articles_api.py::test_delete_article PASSED                            [ 68%]
test_articles_api.py::test_delete_article_not_found PASSED                  [ 72%]
test_articles_api.py::test_delete_article_removes_from_list PASSED          [ 76%]
test_articles_api.py::test_delete_article_cannot_get_after_deletion PASSED  [ 80%]
test_articles_api.py::test_invalid_article_id_format PASSED                 [ 84%]
test_articles_api.py::test_missing_required_fields PASSED                   [ 88%]
test_articles_api.py::test_concurrent_operations PASSED                     [ 92%]
test_articles_api.py::test_article_persistence PASSED                       [ 96%]
test_articles_api.py::test_article_round_trip PASSED                        [100%]

========================= 25 passed in 2.34s =========================
```

## 故障排查

### 导入错误
如果遇到 `ModuleNotFoundError: No module named 'server'`，确保在 `web/api/` 目录下运行测试。

### 权限错误
如果遇到文件权限错误，确保测试目录 `web/api/test_data/` 有写权限。

### 端口冲突
测试使用 TestClient，不需要启动实际的服务器，因此不会有端口冲突。

## 持续集成

可以将测试集成到 CI/CD 流程中：

```yaml
# .github/workflows/test.yml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd web/api
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd web/api
          pytest test_articles_api.py -v
```

## 下一步

- [ ] 添加工作流 API 测试（outline, generate, publish）
- [ ] 添加 WebSocket 事件测试
- [ ] 添加性能测试
- [ ] 添加并发压力测试
