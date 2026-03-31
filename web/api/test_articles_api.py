#!/usr/bin/env python3
"""
Article CRUD API 集成测试

测试覆盖：
- 创建文章（有效和无效标题）
- 获取文章列表和详情
- 更新文章内容
- 删除文章
- 错误处理（404, 400）
"""

import asyncio
import json
import shutil
import time
from pathlib import Path
from typing import Optional

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


# ---------------------------------------------------------------------------
# 测试：创建文章
# ---------------------------------------------------------------------------

def test_create_article_with_valid_title():
    """测试创建文章 - 有效标题"""
    response = client.post("/api/articles", json={
        "title": "如何使用 AI 提升开发效率"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert "article_id" in data
    assert data["article_id"].startswith("art_")
    assert data["title"] == "如何使用 AI 提升开发效率"
    assert "created_at" in data
    
    # 验证文件已创建
    article_id = data["article_id"]
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    assert json_path.exists()
    
    # 验证 JSON 内容
    article_data = json.loads(json_path.read_text("utf-8"))
    assert article_data["id"] == article_id
    assert article_data["title"] == "如何使用 AI 提升开发效率"
    assert article_data["status"] == "draft"
    assert article_data["step"] == "title"
    assert article_data["created_at"] is not None
    assert article_data["updated_at"] is not None


def test_create_article_with_empty_title():
    """测试创建文章 - 空标题（应失败）"""
    response = client.post("/api/articles", json={
        "title": ""
    })
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "标题不能为空" in data["detail"]


def test_create_article_with_whitespace_title():
    """测试创建文章 - 仅空格标题（应失败）"""
    response = client.post("/api/articles", json={
        "title": "   "
    })
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "标题不能为空" in data["detail"]


def test_create_article_trims_whitespace():
    """测试创建文章 - 自动去除首尾空格"""
    response = client.post("/api/articles", json={
        "title": "  测试标题  "
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试标题"


def test_create_multiple_articles_unique_ids():
    """测试创建多篇文章 - ID 唯一性"""
    titles = ["文章1", "文章2", "文章3"]
    article_ids = []
    
    for title in titles:
        response = client.post("/api/articles", json={"title": title})
        assert response.status_code == 200
        data = response.json()
        article_ids.append(data["article_id"])
        
        # 确保 ID 唯一
        time.sleep(0.01)  # 避免时间戳冲突
    
    # 验证所有 ID 唯一
    assert len(article_ids) == len(set(article_ids))


# ---------------------------------------------------------------------------
# 测试：获取文章列表
# ---------------------------------------------------------------------------

def test_get_articles_empty_list():
    """测试获取文章列表 - 空列表"""
    response = client.get("/api/articles")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["articles"] == []
    assert data["total"] == 0


def test_get_articles_list():
    """测试获取文章列表 - 多篇文章"""
    # 创建 3 篇文章
    titles = ["文章1", "文章2", "文章3"]
    for title in titles:
        client.post("/api/articles", json={"title": title})
        time.sleep(0.01)
    
    # 获取列表
    response = client.get("/api/articles")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert len(data["articles"]) == 3
    assert data["total"] == 3
    
    # 验证列表项包含必要字段
    for article in data["articles"]:
        assert "id" in article
        assert "title" in article
        assert "status" in article
        assert "step" in article
        assert "created_at" in article
        assert "updated_at" in article
        # 列表不应包含 content 字段
        assert "content" not in article


def test_get_articles_sorted_by_updated_at():
    """测试获取文章列表 - 按 updated_at 倒序排列"""
    # 创建 3 篇文章
    article_ids = []
    for i in range(3):
        response = client.post("/api/articles", json={"title": f"文章{i}"})
        article_ids.append(response.json()["article_id"])
        time.sleep(0.02)
    
    # 更新第一篇文章（使其 updated_at 最新）
    client.put(f"/api/articles/{article_ids[0]}", json={"content": "更新内容"})
    
    # 获取列表
    response = client.get("/api/articles")
    data = response.json()
    
    # 第一篇文章应该排在最前面
    assert data["articles"][0]["id"] == article_ids[0]


# ---------------------------------------------------------------------------
# 测试：获取文章详情
# ---------------------------------------------------------------------------

def test_get_article_detail():
    """测试获取文章详情 - 成功"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 获取详情
    response = client.get(f"/api/articles/{article_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert "article" in data
    
    article = data["article"]
    assert article["id"] == article_id
    assert article["title"] == "测试文章"
    assert article["status"] == "draft"
    assert article["step"] == "title"
    assert "content" in article  # 详情应包含 content 字段


def test_get_article_not_found():
    """测试获取文章详情 - 文章不存在（404）"""
    response = client.get("/api/articles/art_nonexistent")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "文章不存在" in data["detail"]


def test_get_article_with_content():
    """测试获取文章详情 - 包含 Markdown 内容"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 更新内容
    content = "# 测试文章\n\n这是测试内容。"
    client.put(f"/api/articles/{article_id}", json={"content": content})
    
    # 获取详情
    response = client.get(f"/api/articles/{article_id}")
    data = response.json()
    
    assert data["article"]["content"] == content


# ---------------------------------------------------------------------------
# 测试：更新文章内容
# ---------------------------------------------------------------------------

def test_update_article_content():
    """测试更新文章内容 - 成功"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 更新内容
    new_content = "# 更新后的内容\n\n这是新内容。"
    response = client.put(f"/api/articles/{article_id}", json={
        "content": new_content
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["article_id"] == article_id
    assert "updated_at" in data
    
    # 验证内容已更新
    get_response = client.get(f"/api/articles/{article_id}")
    article = get_response.json()["article"]
    assert article["content"] == new_content


def test_update_article_updates_timestamp():
    """测试更新文章 - updated_at 时间戳更新"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 获取初始时间戳
    get_response = client.get(f"/api/articles/{article_id}")
    original_updated_at = get_response.json()["article"]["updated_at"]
    
    # 等待一小段时间
    time.sleep(0.1)
    
    # 更新内容
    client.put(f"/api/articles/{article_id}", json={
        "content": "新内容"
    })
    
    # 验证时间戳已更新
    get_response = client.get(f"/api/articles/{article_id}")
    new_updated_at = get_response.json()["article"]["updated_at"]
    
    assert new_updated_at > original_updated_at


def test_update_article_not_found():
    """测试更新文章 - 文章不存在（404）"""
    response = client.put("/api/articles/art_nonexistent", json={
        "content": "新内容"
    })
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "文章不存在" in data["detail"]


def test_update_article_with_empty_content():
    """测试更新文章 - 空内容（应允许）"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 更新为空内容
    response = client.put(f"/api/articles/{article_id}", json={
        "content": ""
    })
    
    assert response.status_code == 200
    
    # 验证内容已更新为空
    get_response = client.get(f"/api/articles/{article_id}")
    assert get_response.json()["article"]["content"] == ""


def test_update_article_preserves_metadata():
    """测试更新文章 - 保留元数据"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 获取原始元数据
    get_response = client.get(f"/api/articles/{article_id}")
    original_article = get_response.json()["article"]
    
    # 更新内容
    client.put(f"/api/articles/{article_id}", json={
        "content": "新内容"
    })
    
    # 验证元数据未改变（除了 updated_at）
    get_response = client.get(f"/api/articles/{article_id}")
    updated_article = get_response.json()["article"]
    
    assert updated_article["id"] == original_article["id"]
    assert updated_article["title"] == original_article["title"]
    assert updated_article["status"] == original_article["status"]
    assert updated_article["step"] == original_article["step"]
    assert updated_article["created_at"] == original_article["created_at"]


# ---------------------------------------------------------------------------
# 测试：删除文章
# ---------------------------------------------------------------------------

def test_delete_article():
    """测试删除文章 - 成功"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 添加内容
    client.put(f"/api/articles/{article_id}", json={
        "content": "测试内容"
    })
    
    # 验证文件存在
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    assert json_path.exists()
    assert md_path.exists()
    
    # 删除文章
    response = client.delete(f"/api/articles/{article_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["article_id"] == article_id
    assert "已删除" in data["message"]
    
    # 验证文件已删除
    assert not json_path.exists()
    assert not md_path.exists()


def test_delete_article_not_found():
    """测试删除文章 - 文章不存在（404）"""
    response = client.delete("/api/articles/art_nonexistent")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "文章不存在" in data["detail"]


def test_delete_article_removes_from_list():
    """测试删除文章 - 从列表中移除"""
    # 创建 3 篇文章
    article_ids = []
    for i in range(3):
        response = client.post("/api/articles", json={"title": f"文章{i}"})
        article_ids.append(response.json()["article_id"])
    
    # 删除第二篇
    client.delete(f"/api/articles/{article_ids[1]}")
    
    # 验证列表只剩 2 篇
    response = client.get("/api/articles")
    data = response.json()
    
    assert len(data["articles"]) == 2
    assert data["total"] == 2
    
    # 验证被删除的文章不在列表中
    remaining_ids = [a["id"] for a in data["articles"]]
    assert article_ids[1] not in remaining_ids
    assert article_ids[0] in remaining_ids
    assert article_ids[2] in remaining_ids


def test_delete_article_cannot_get_after_deletion():
    """测试删除文章 - 删除后无法获取"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 删除文章
    client.delete(f"/api/articles/{article_id}")
    
    # 尝试获取详情（应返回 404）
    response = client.get(f"/api/articles/{article_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 测试：错误处理
# ---------------------------------------------------------------------------

def test_invalid_article_id_format():
    """测试无效的文章 ID 格式"""
    # 获取详情
    response = client.get("/api/articles/invalid_id")
    assert response.status_code == 404
    
    # 更新
    response = client.put("/api/articles/invalid_id", json={"content": "test"})
    assert response.status_code == 404
    
    # 删除
    response = client.delete("/api/articles/invalid_id")
    assert response.status_code == 404


def test_missing_required_fields():
    """测试缺少必需字段"""
    # 创建文章时缺少 title
    response = client.post("/api/articles", json={})
    assert response.status_code == 422  # FastAPI 验证错误
    
    # 更新文章时缺少 content
    create_response = client.post("/api/articles", json={"title": "测试"})
    article_id = create_response.json()["article_id"]
    
    response = client.put(f"/api/articles/{article_id}", json={})
    assert response.status_code == 422


def test_concurrent_operations():
    """测试并发操作 - 原子性写入"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "测试文章"
    })
    article_id = create_response.json()["article_id"]
    
    # 模拟并发更新（快速连续更新）
    contents = ["内容1", "内容2", "内容3"]
    for content in contents:
        client.put(f"/api/articles/{article_id}", json={"content": content})
    
    # 验证最终内容是最后一次更新的内容
    response = client.get(f"/api/articles/{article_id}")
    final_content = response.json()["article"]["content"]
    assert final_content == "内容3"
    
    # 验证 JSON 文件完整性（没有损坏）
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    article_data = json.loads(json_path.read_text("utf-8"))
    assert "id" in article_data
    assert "title" in article_data


# ---------------------------------------------------------------------------
# 测试：数据持久化
# ---------------------------------------------------------------------------

def test_article_persistence():
    """测试文章数据持久化"""
    # 创建文章
    create_response = client.post("/api/articles", json={
        "title": "持久化测试"
    })
    article_id = create_response.json()["article_id"]
    
    # 更新内容
    content = "# 持久化测试\n\n这是测试内容。"
    client.put(f"/api/articles/{article_id}", json={"content": content})
    
    # 验证 JSON 文件
    json_path = TEST_ARTICLES_DIR / f"{article_id}.json"
    assert json_path.exists()
    article_data = json.loads(json_path.read_text("utf-8"))
    assert article_data["id"] == article_id
    assert article_data["title"] == "持久化测试"
    
    # 验证 Markdown 文件
    md_path = TEST_ARTICLES_DIR / f"{article_id}.md"
    assert md_path.exists()
    md_content = md_path.read_text("utf-8")
    assert md_content == content


def test_article_round_trip():
    """测试文章数据往返一致性"""
    # 创建文章
    original_title = "往返测试"
    create_response = client.post("/api/articles", json={
        "title": original_title
    })
    article_id = create_response.json()["article_id"]
    
    # 更新内容
    original_content = "# 往返测试\n\n这是测试内容。"
    client.put(f"/api/articles/{article_id}", json={
        "content": original_content
    })
    
    # 读取文章
    response = client.get(f"/api/articles/{article_id}")
    article = response.json()["article"]
    
    # 验证数据一致性
    assert article["title"] == original_title
    assert article["content"] == original_content


# ---------------------------------------------------------------------------
# 运行测试
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
