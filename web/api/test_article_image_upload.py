#!/usr/bin/env python3
"""
测试文章图片上传 API
"""

import pytest
import json
import io
from pathlib import Path
from fastapi.testclient import TestClient
from server import app, ARTICLES_DIR

client = TestClient(app)


@pytest.fixture
def test_article():
    """创建测试文章"""
    response = client.post("/api/articles", json={"title": "测试文章 - 图片上传"})
    assert response.status_code == 200
    data = response.json()
    article_id = data["article_id"]
    
    yield article_id
    
    # 清理：删除测试文章
    try:
        client.delete(f"/api/articles/{article_id}")
        # 清理图片目录
        images_dir = ARTICLES_DIR / article_id / "images"
        if images_dir.exists():
            for img in images_dir.glob("*"):
                img.unlink()
            images_dir.rmdir()
            (ARTICLES_DIR / article_id).rmdir()
    except Exception:
        pass


def test_upload_image_success(test_article):
    """测试成功上传图片"""
    article_id = test_article
    
    # 创建测试图片（1x1 PNG）
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    files = {
        "file": ("test_image.png", io.BytesIO(png_data), "image/png")
    }
    
    response = client.post(f"/api/articles/{article_id}/images", files=files)
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证响应格式
    assert data["ok"] is True
    assert "image_url" in data
    assert "markdown" in data
    assert "filename" in data
    
    # 验证 URL 格式
    assert data["image_url"].startswith(f"/images/articles/{article_id}/")
    assert data["image_url"].endswith(".png")
    
    # 验证 Markdown 格式
    assert data["markdown"].startswith("![")
    assert data["image_url"] in data["markdown"]
    
    # 验证文件已保存
    images_dir = ARTICLES_DIR / article_id / "images"
    assert images_dir.exists()
    
    filename = data["filename"]
    image_path = images_dir / filename
    assert image_path.exists()
    assert image_path.read_bytes() == png_data
    
    # 验证文章元数据已更新
    article_response = client.get(f"/api/articles/{article_id}")
    article = article_response.json()["article"]
    assert "images" in article
    assert filename in article["images"]

    # 验证图片可通过静态路由访问
    image_response = client.get(data["image_url"])
    assert image_response.status_code == 200
    assert image_response.content == png_data

    nested_response = client.get(f"/images/articles/{article_id}/images/{filename}")
    assert nested_response.status_code == 200
    assert nested_response.content == png_data


def test_upload_multiple_images(test_article):
    """测试上传多张图片"""
    article_id = test_article
    
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    # 上传第一张图片
    files1 = {"file": ("image1.png", io.BytesIO(png_data), "image/png")}
    response1 = client.post(f"/api/articles/{article_id}/images", files=files1)
    assert response1.status_code == 200
    
    # 上传第二张图片
    files2 = {"file": ("image2.png", io.BytesIO(png_data), "image/png")}
    response2 = client.post(f"/api/articles/{article_id}/images", files=files2)
    assert response2.status_code == 200
    
    # 验证两张图片都在元数据中
    article_response = client.get(f"/api/articles/{article_id}")
    article = article_response.json()["article"]
    assert len(article["images"]) == 2


def test_upload_image_invalid_type(test_article):
    """测试上传非图片文件"""
    article_id = test_article
    
    # 尝试上传文本文件
    files = {
        "file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")
    }
    
    response = client.post(f"/api/articles/{article_id}/images", files=files)
    
    assert response.status_code == 400
    assert "不支持的文件类型" in response.json()["detail"]


def test_upload_image_article_not_found():
    """测试上传图片到不存在的文章"""
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    files = {
        "file": ("test.png", io.BytesIO(png_data), "image/png")
    }
    
    response = client.post("/api/articles/nonexistent_id/images", files=files)
    
    assert response.status_code == 404
    assert "文章不存在" in response.json()["detail"]


def test_upload_jpeg_image(test_article):
    """测试上传 JPEG 图片"""
    article_id = test_article
    
    # 最小的有效 JPEG 文件
    jpeg_data = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c'
        b'\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
        b'\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08'
        b'\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14'
        b'\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x7f\x00\xff\xd9'
    )
    
    files = {
        "file": ("test.jpg", io.BytesIO(jpeg_data), "image/jpeg")
    }
    
    response = client.post(f"/api/articles/{article_id}/images", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["image_url"].endswith(".jpg")


def test_upload_webp_image(test_article):
    """测试上传 WebP 图片"""
    article_id = test_article
    
    # 最小的有效 WebP 文件（1x1 像素）
    webp_data = (
        b'RIFF$\x00\x00\x00WEBPVP8 \x18\x00\x00\x000\x01\x00\x9d\x01*'
        b'\x01\x00\x01\x00\x01@\x00\xfe\xf7\x00\x00\x00'
    )
    
    files = {
        "file": ("test.webp", io.BytesIO(webp_data), "image/webp")
    }
    
    response = client.post(f"/api/articles/{article_id}/images", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["image_url"].endswith(".webp")


def test_upload_gif_image(test_article):
    """测试上传 GIF 图片"""
    article_id = test_article
    
    # 最小的有效 GIF 文件（1x1 像素）
    gif_data = (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00'
        b'!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00'
        b'\x00\x02\x02D\x01\x00;'
    )
    
    files = {
        "file": ("test.gif", io.BytesIO(gif_data), "image/gif")
    }
    
    response = client.post(f"/api/articles/{article_id}/images", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["image_url"].endswith(".gif")


def test_unique_filenames(test_article):
    """测试文件名唯一性（使用时间戳）"""
    article_id = test_article
    
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    # 快速上传两张图片
    files1 = {"file": ("test.png", io.BytesIO(png_data), "image/png")}
    response1 = client.post(f"/api/articles/{article_id}/images", files=files1)
    
    files2 = {"file": ("test.png", io.BytesIO(png_data), "image/png")}
    response2 = client.post(f"/api/articles/{article_id}/images", files=files2)
    
    # 验证文件名不同
    filename1 = response1.json()["filename"]
    filename2 = response2.json()["filename"]
    assert filename1 != filename2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
