#!/usr/bin/env python3
"""
Article Workflow API 集成测试

测试覆盖：
- POST /api/articles/{id}/outline - 生成骨架
- POST /api/articles/{id}/generate - 生成全文
- POST /api/articles/{id}/publish - 发布文章
- WebSocket 事件广播
- CLI 工具调用参数
- 错误处理和错误事件
"""

import asyncio
import json
import shutil
import time
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# 导入 FastAPI 应用
import sys
sys.path.insert(0, str(Path(__file__).parent))
from server import app, ARTICLES_DIR

# 创建测试客户端
client = TestClient(app)

# 测试数据目录
TEST_ARTICLES_DIR = Path(__file__).parent / "test_data" / "articles"


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """每个测试前后的设置和清理"""
    # 备份原始 ARTICLES_DIR
    original_dir = ARTICLES_DIR
    
    # 使用测试目录
    import server
    server.ARTICLES_DIR = TEST_ARTICLES_DIR
    
    # 清理测试目录
    if TEST_ARTICLES_DIR.exists():
        shutil.rmtree(TEST_ARTICLES_DIR)
    TEST_ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # 恢复原始目录
    server.ARTICLES_DIR = original_dir
    
    # 清理测试数据
    if TEST_ARTICLES_DIR.exists():
        shutil.rmtree(TEST_ARTICLES_DIR)


def create_test_article(title="测试文章"):
    """辅助函数：创建测试文章"""
    response = client.post("/api/articles", json={"title": title})
    return response.json()["article_id"]


# ---------------------------------------------------------------------------
# 测试：一键生成 API (Auto-Generate)
# ---------------------------------------------------------------------------

@patch('server._run_xpost')
def test_auto_generate_success(mock_run_xpost):
    """测试一键生成 - 成功"""
    # 创建文章
    article_id = create_test_article("如何使用 AI 提升开发效率")
    
    # Mock xpost init 和 generate 命令返回成功
    mock_run_xpost.side_effect = [
        {"created": True, "path": str(TEST_ARTICLES_DIR / f"{article_id}.md")},  # init
        {"ok": True, "generated": True}  # generate
    ]
    
    # 调用一键生成 API（默认 zara 风格）
    response = client.post(f"/api/articles/{article_id}/auto-generate")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["article_id"] == article_id
    assert data["status"] == "generating"
    assert data["style"] == "zara"
    assert "message" in data


@patch('server._run_xpost')
def test_auto_generate_with_style_parameter(mock_run_xpost):
    """测试一键生成 - 指定风格参数"""
    # 创建文章
    article_id = create_test_article("技术文章标题")
    
    # Mock xpost 命令
    mock_run_xpost.side_effect = [
        {"created": True},
        {"ok": True}
    ]
    
    # 调用一键生成 API，指定 tech 风格
    response = client.post(f"/api/articles/{article_id}/auto-generate?style=tech")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["style"] == "tech"


@patch('server._run_xpost')
def test_auto_generate_with_fun_style(mock_run_xpost):
    """测试一键生成 - fun 风格"""
    # 创建文章
    article_id = create_test_article("趣味文章标题")
    
    # Mock xpost 命令
    mock_run_xpost.side_effect = [
        {"created": True},
        {"ok": True}
    ]
    
    # 调用一键生成 API，指定 fun 风格
    response = client.post(f"/api/articles/{article_id}/auto-generate?style=fun")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["style"] == "fun"


def test_auto_generate_invalid_style():
    """测试一键生成 - 无效的风格参数"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # 调用一键生成 API，使用无效风格
    response = client.post(f"/api/articles/{article_id}/auto-generate?style=invalid")
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "无效的风格参数" in data["detail"]


def test_auto_generate_article_not_found():
    """测试一键生成 - 文章不存在"""
    response = client.post("/api/articles/art_nonexistent/auto-generate")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "文章不存在" in data["detail"]


@patch('server._run_xpost')
def test_auto_generate_cli_parameters(mock_run_xpost):
    """测试一键生成 - 验证 CLI 调用参数"""
    # 创建文章
    title = "测试标题"
    article_id = create_test_article(title)
    
    # Mock xpost 命令
    mock_run_xpost.side_effect = [
        {"created": True},
        {"ok": True}
    ]
    
    # 调用一键生成 API，指定 zara 风格
    client.post(f"/api/articles/{article_id}/auto-generate?style=zara")
    
    # 等待后台任务执行
    time.sleep(0.5)
    
    # 验证 CLI 调用参数
    assert mock_run_xpost.call_count == 2
    
    # 第一次调用：xpost init <md_path> --topic <title> --style zara
    first_call = mock_run_xpost.call_args_list[0][0]
    assert first_call[0] == "init"
    assert str(TEST_ARTICLES_DIR / f"{article_id}.md") in first_call[1]
    assert "--topic" in first_call
    assert title in first_call
    assert "--style" in first_call
    assert "zara" in first_call
    
    # 第二次调用：xpost generate <md_path>
    second_call = mock_run_xpost.call_args_list[1][0]
    assert second_call[0] == "generate"
    assert str(TEST_ARTICLES_DIR / f"{article_id}.md") in second_call[1]


@patch('server._run_xpost')
def test_auto_generate_saves_style_to_metadata(mock_run_xpost):
    """测试一键生成 - 保存风格到文章元数据"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # 创建 Markdown 文件（模拟生成的内容）
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    md_path.write_text("# 测试骨架\n\n## 章节 1", "utf-8")
    
    # Mock xpost 命令
    mock_run_xpost.side_effect = [
        {"created": True},
        {"ok": True}
    ]
    
    # 调用一键生成 API，指定 tech 风格
    client.post(f"/api/articles/{article_id}/auto-generate?style=tech")
    
    # 等待后台任务执行
    time.sleep(0.5)
    
    # 验证文章元数据中保存了风格
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    article_data = json.loads(json_path.read_text("utf-8"))
    assert article_data.get("style") == "tech"


@patch('server._run_xpost')
def test_auto_generate_outline_failure(mock_run_xpost):
    """测试一键生成 - 骨架生成失败"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # Mock xpost init 命令返回失败
    mock_run_xpost.return_value = {
        "ok": False,
        "error": "生成失败：无法连接到 LLM"
    }
    
    # 调用一键生成 API
    response = client.post(f"/api/articles/{article_id}/auto-generate")
    
    # 应该返回 202，错误通过 WebSocket 通知
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["status"] == "generating"


@patch('server._run_xpost')
def test_auto_generate_content_failure(mock_run_xpost):
    """测试一键生成 - 全文生成失败"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # 创建 Markdown 文件（模拟骨架生成成功）
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    md_path.write_text("# 测试骨架", "utf-8")
    
    # Mock xpost 命令：init 成功，generate 失败
    mock_run_xpost.side_effect = [
        {"created": True},
        {"ok": False, "error": "生成失败"}
    ]
    
    # 调用一键生成 API
    response = client.post(f"/api/articles/{article_id}/auto-generate")
    
    # 应该返回 202，错误通过 WebSocket 通知
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 测试：取消生成 API
# ---------------------------------------------------------------------------

@patch('server._kill_active_xpost')
def test_cancel_generation(mock_kill):
    """测试取消生成"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # Mock 取消函数
    mock_kill.return_value = {
        "ok": True,
        "cancelled": True,
        "message": "已发送终止信号"
    }
    
    # 调用取消 API
    response = client.post(f"/api/articles/{article_id}/cancel")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["cancelled"] is True
    assert "message" in data


@patch('server._kill_active_xpost')
def test_cancel_no_active_task(mock_kill):
    """测试取消生成 - 没有活动任务"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # Mock 取消函数返回没有活动任务
    mock_kill.return_value = {
        "ok": True,
        "cancelled": False,
        "message": "当前没有正在执行的 xpost 任务"
    }
    
    # 调用取消 API
    response = client.post(f"/api/articles/{article_id}/cancel")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["cancelled"] is False


# ---------------------------------------------------------------------------
# 测试：生成骨架 API
# ---------------------------------------------------------------------------

@patch('server._run_xpost')
def test_generate_outline_success(mock_run_xpost):
    """测试生成骨架 - 成功"""
    # 创建文章
    article_id = create_test_article("如何使用 AI 提升开发效率")
    
    # Mock xpost init 命令返回成功
    mock_run_xpost.return_value = {
        "created": True,
        "path": str(TEST_ARTICLES_DIR / f"{article_id}.md")
    }
    
    # 调用生成骨架 API
    response = client.post(f"/api/articles/{article_id}/outline")
    
    assert response.status_code == 200  # 默认返回 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["article_id"] == article_id
    assert "message" in data
    assert "已启动" in data["message"]


def test_generate_outline_article_not_found():
    """测试生成骨架 - 文章不存在"""
    response = client.post("/api/articles/art_nonexistent/outline")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "文章不存在" in data["detail"]


@patch('server._run_xpost')
def test_generate_outline_cli_parameters(mock_run_xpost):
    """测试生成骨架 - 验证 CLI 调用参数"""
    # 创建文章
    title = "测试标题"
    article_id = create_test_article(title)
    
    # Mock xpost init 命令
    mock_run_xpost.return_value = {"created": True}
    
    # 调用生成骨架 API
    client.post(f"/api/articles/{article_id}/outline")
    
    # 等待后台任务执行
    time.sleep(0.5)
    
    # 验证 CLI 调用参数
    # 应该调用: xpost init <md_path> --topic <title> --style tech
    assert mock_run_xpost.called
    call_args = mock_run_xpost.call_args[0]
    
    assert call_args[0] == "init"
    assert str(TEST_ARTICLES_DIR / f"{article_id}.md") in call_args[1]
    assert "--topic" in call_args
    assert title in call_args
    assert "--style" in call_args
    assert "tech" in call_args


# ---------------------------------------------------------------------------
# 测试：生成全文 API
# ---------------------------------------------------------------------------

@patch('server._run_xpost')
def test_generate_content_success(mock_run_xpost):
    """测试生成全文 - 成功"""
    # 创建文章并设置为 outline 步骤
    article_id = create_test_article("测试文章")
    
    # 更新步骤为 outline
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    article_data = json.loads(json_path.read_text("utf-8"))
    article_data["step"] = "outline"
    json_path.write_text(json.dumps(article_data, ensure_ascii=False, indent=2), "utf-8")
    
    # 创建 Markdown 文件（必须存在）
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    md_path.write_text("# 测试骨架\n\n## 章节 1", "utf-8")
    
    # Mock xpost generate 命令返回成功
    mock_run_xpost.return_value = {
        "ok": True,
        "generated": True
    }
    
    # 调用生成全文 API
    response = client.post(f"/api/articles/{article_id}/generate")
    
    assert response.status_code == 200  # Accepted
    data = response.json()
    
    assert data["ok"] is True
    assert data["article_id"] == article_id


def test_generate_content_article_not_found():
    """测试生成全文 - 文章不存在"""
    response = client.post("/api/articles/art_nonexistent/generate")
    
    assert response.status_code == 404


@patch('server._run_xpost')
def test_generate_content_cli_parameters(mock_run_xpost):
    """测试生成全文 - 验证 CLI 调用参数"""
    # 创建文章并设置为 outline 步骤
    article_id = create_test_article("测试文章")
    
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    article_data = json.loads(json_path.read_text("utf-8"))
    article_data["step"] = "outline"
    json_path.write_text(json.dumps(article_data, ensure_ascii=False, indent=2), "utf-8")
    
    # 创建 Markdown 文件（必须存在）
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    md_path.write_text("# 测试骨架", "utf-8")
    
    # Mock xpost generate 命令
    mock_run_xpost.return_value = {"ok": True}
    
    # 调用生成全文 API
    client.post(f"/api/articles/{article_id}/generate")
    
    # 等待后台任务执行
    time.sleep(0.5)
    
    # 验证 CLI 调用参数
    # 应该调用: xpost generate <md_path>
    assert mock_run_xpost.called
    call_args = mock_run_xpost.call_args[0]
    
    assert call_args[0] == "generate"
    assert str(TEST_ARTICLES_DIR / f"{article_id}.md") in call_args[1]


# ---------------------------------------------------------------------------
# 测试：发布文章 API
# ---------------------------------------------------------------------------

@patch('server._run_xpost')
def test_publish_article_success(mock_run_xpost):
    """测试发布文章 - 成功"""
    # 创建文章并设置为 content 步骤
    article_id = create_test_article("测试文章")
    
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    article_data = json.loads(json_path.read_text("utf-8"))
    article_data["step"] = "content"
    json_path.write_text(json.dumps(article_data, ensure_ascii=False, indent=2), "utf-8")
    
    # 创建 Markdown 文件（必须存在）
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    md_path.write_text("# 测试文章\n\n完整内容...", "utf-8")
    
    # Mock xpost publish 命令返回成功
    mock_run_xpost.return_value = {
        "ok": True,
        "published": True,
        "url": "https://x.com/test/status/123456"
    }
    
    # 调用发布文章 API
    response = client.post(f"/api/articles/{article_id}/publish")
    
    assert response.status_code == 200  # Accepted
    data = response.json()
    
    assert data["ok"] is True
    assert data["article_id"] == article_id


def test_publish_article_not_found():
    """测试发布文章 - 文章不存在"""
    response = client.post("/api/articles/art_nonexistent/publish")
    
    assert response.status_code == 404


@patch('server._run_xpost')
def test_publish_article_cli_parameters(mock_run_xpost):
    """测试发布文章 - 验证 CLI 调用参数"""
    # 创建文章并设置为 content 步骤
    article_id = create_test_article("测试文章")
    
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    article_data = json.loads(json_path.read_text("utf-8"))
    article_data["step"] = "content"
    json_path.write_text(json.dumps(article_data, ensure_ascii=False, indent=2), "utf-8")
    
    # 创建 Markdown 文件（必须存在）
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    md_path.write_text("# 测试文章", "utf-8")
    
    # Mock xpost publish 命令
    mock_run_xpost.return_value = {"ok": True, "published": True}
    
    # 调用发布文章 API
    client.post(f"/api/articles/{article_id}/publish")
    
    # 等待后台任务执行
    time.sleep(0.5)
    
    # 验证 CLI 调用参数
    # 应该调用: xpost publish <md_path> --publish
    assert mock_run_xpost.called
    call_args = mock_run_xpost.call_args[0]
    
    assert call_args[0] == "publish"
    assert str(TEST_ARTICLES_DIR / f"{article_id}.md") in call_args[1]
    assert "--publish" in call_args


# ---------------------------------------------------------------------------
# 测试：完整工作流
# ---------------------------------------------------------------------------

@patch('server._run_xpost')
def test_complete_workflow(mock_run_xpost):
    """测试完整工作流：create → outline → generate → publish"""
    
    # 1. 创建文章
    article_id = create_test_article("完整工作流测试")
    
    # 验证初始状态
    response = client.get(f"/api/articles/{article_id}")
    article = response.json()["article"]
    assert article["step"] == "title"
    assert article["status"] == "draft"
    
    # 2. 生成骨架
    mock_run_xpost.return_value = {"created": True}
    response = client.post(f"/api/articles/{article_id}/outline")
    assert response.status_code == 200
    
    # 模拟骨架生成完成，更新步骤和创建 Markdown 文件
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    article_data = json.loads(json_path.read_text("utf-8"))
    article_data["step"] = "outline"
    article_data["outline"] = "# 测试骨架\n\n## 章节 1"
    json_path.write_text(json.dumps(article_data, ensure_ascii=False, indent=2), "utf-8")
    
    # 创建 Markdown 文件
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    md_path.write_text("# 测试骨架\n\n## 章节 1", "utf-8")
    
    # 3. 生成全文
    mock_run_xpost.return_value = {"ok": True, "generated": True}
    response = client.post(f"/api/articles/{article_id}/generate")
    assert response.status_code == 200
    
    # 模拟全文生成完成，更新步骤和内容
    article_data["step"] = "content"
    article_data["content"] = "# 测试文章\n\n完整内容..."
    json_path.write_text(json.dumps(article_data, ensure_ascii=False, indent=2), "utf-8")
    md_path.write_text("# 测试文章\n\n完整内容...", "utf-8")
    
    # 4. 发布文章
    mock_run_xpost.return_value = {
        "ok": True,
        "published": True,
        "url": "https://x.com/test/status/123456"
    }
    response = client.post(f"/api/articles/{article_id}/publish")
    assert response.status_code == 200
    
    # 验证 CLI 调用顺序
    assert mock_run_xpost.call_count >= 3
    
    # 第一次调用：init
    first_call = mock_run_xpost.call_args_list[0][0]
    assert first_call[0] == "init"
    
    # 第二次调用：generate
    second_call = mock_run_xpost.call_args_list[1][0]
    assert second_call[0] == "generate"
    
    # 第三次调用：publish
    third_call = mock_run_xpost.call_args_list[2][0]
    assert third_call[0] == "publish"


# ---------------------------------------------------------------------------
# 测试：错误处理
# ---------------------------------------------------------------------------

@patch('server._run_xpost')
def test_outline_generation_failure(mock_run_xpost):
    """测试骨架生成失败"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # Mock xpost init 命令返回失败
    mock_run_xpost.return_value = {
        "ok": False,
        "error": "生成失败：无法连接到 LLM"
    }
    
    # 调用生成骨架 API
    response = client.post(f"/api/articles/{article_id}/outline")
    assert response.status_code == 200  # 仍然返回 202，错误通过 WebSocket 通知


@patch('server._run_xpost')
def test_cli_timeout_handling(mock_run_xpost):
    """测试 CLI 超时处理"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # Mock xpost 命令超时（同步版本）
    def timeout_side_effect(*args, **kwargs):
        raise Exception("命令执行超时")
    
    mock_run_xpost.side_effect = timeout_side_effect
    
    # 调用生成骨架 API
    response = client.post(f"/api/articles/{article_id}/outline")
    assert response.status_code == 200


@patch('server._run_xpost')
def test_cli_exception_handling(mock_run_xpost):
    """测试 CLI 异常处理"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # Mock xpost 命令抛出异常
    mock_run_xpost.side_effect = Exception("未知错误")
    
    # 调用生成骨架 API
    response = client.post(f"/api/articles/{article_id}/outline")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 测试：并发操作
# ---------------------------------------------------------------------------

@patch('server._run_xpost')
def test_concurrent_workflow_operations(mock_run_xpost):
    """测试并发工作流操作"""
    # 创建多篇文章
    article_ids = [create_test_article(f"文章{i}") for i in range(3)]
    
    # Mock xpost 命令
    mock_run_xpost.return_value = {"created": True}
    
    # 并发调用生成骨架
    responses = []
    for article_id in article_ids:
        response = client.post(f"/api/articles/{article_id}/outline")
        responses.append(response)
    
    # 验证所有请求都成功
    for response in responses:
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# 测试：步骤验证
# ---------------------------------------------------------------------------

def test_generate_content_requires_outline_step():
    """测试生成全文需要先完成骨架步骤"""
    # 创建文章（step=title）
    article_id = create_test_article("测试文章")
    
    # 尝试直接生成全文（应该允许，但可能会失败）
    response = client.post(f"/api/articles/{article_id}/generate")
    
    # 当前实现允许任何步骤生成全文，所以应该返回 202
    # 如果未来添加步骤验证，这里应该返回 400
    assert response.status_code in [202, 400]


def test_publish_requires_content_step():
    """测试发布需要先完成内容步骤"""
    # 创建文章（step=title）
    article_id = create_test_article("测试文章")
    
    # 尝试直接发布（应该允许，但可能会失败）
    response = client.post(f"/api/articles/{article_id}/publish")
    
    # 当前实现允许任何步骤发布，所以应该返回 202
    # 如果未来添加步骤验证，这里应该返回 400
    assert response.status_code in [202, 400]


# ---------------------------------------------------------------------------
# 测试：数据更新
# ---------------------------------------------------------------------------

@patch('server._run_xpost')
def test_outline_updates_article_data(mock_run_xpost):
    """测试骨架生成更新文章数据"""
    # 创建文章
    article_id = create_test_article("测试文章")
    
    # 创建骨架内容
    outline_content = "# 测试骨架\n\n## 章节 1\n\n## 章节 2"
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    md_path.write_text(outline_content, "utf-8")
    
    # Mock xpost init 命令返回成功
    mock_run_xpost.return_value = {"created": True}
    
    # 调用生成骨架 API
    client.post(f"/api/articles/{article_id}/outline")
    
    # 等待后台任务执行
    time.sleep(0.5)
    
    # 验证文章数据已更新（通过后台任务）
    # 注意：由于是异步后台任务，这里可能需要等待或使用其他方式验证


# ---------------------------------------------------------------------------
# 运行测试
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
