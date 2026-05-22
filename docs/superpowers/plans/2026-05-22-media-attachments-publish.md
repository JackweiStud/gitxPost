# Media Attachments for `/publish` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/publish` accept image and video attachments through one unified media attachment flow, from browser upload through API persistence to Post publishing.

**Architecture:** Replace the current image-only upload path with a generic media attachment path. The backend will expose one upload endpoint that accepts image/video files, persist them under `xinfo/log/uploads`, and serve them back through the FastAPI app. The publish API and CLI will carry a typed attachment list so the UI can pass mixed media without special-casing images versus videos.

**Tech Stack:** Vue 3, FastAPI, Pydantic, Python CLI, Playwright/patchright automation, pytest.

---

### Task 1: Write failing backend tests for unified media uploads and publish payloads

**Files:**
- Create: `web/api/test_publish_media_upload.py`
- Modify: `web/api/test_article_image_upload.py:1-260`

- [ ] **Step 1: Write the failing test**

```python
import io
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server import app, UPLOAD_DIR, ARTICLES_DIR

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_uploads():
    original_upload_dir = UPLOAD_DIR
    original_articles_dir = ARTICLES_DIR
    yield
    if original_upload_dir.exists():
        shutil.rmtree(original_upload_dir, ignore_errors=True)
    if original_articles_dir.exists():
        shutil.rmtree(original_articles_dir, ignore_errors=True)


def test_upload_media_accepts_image_and_video():
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    mp4_data = (
        b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41isom'
        b'\x00\x00\x00\x08free\x00\x00\x00\x08mdat'
    )

    image_resp = client.post(
        "/api/upload/media",
        files={"file": ("a.png", io.BytesIO(png_data), "image/png")},
    )
    video_resp = client.post(
        "/api/upload/media",
        files={"file": ("b.mp4", io.BytesIO(mp4_data), "video/mp4")},
    )

    assert image_resp.status_code == 200
    assert video_resp.status_code == 200
    assert image_resp.json()["kind"] == "image"
    assert video_resp.json()["kind"] == "video"
    assert image_resp.json()["url"].startswith("/uploads/")
    assert video_resp.json()["url"].startswith("/uploads/")


def test_upload_media_rejects_non_media():
    resp = client.post(
        "/api/upload/media",
        files={"file": ("a.txt", io.BytesIO(b"nope"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "只支持图片或视频" in resp.json()["detail"]


def test_publish_post_accepts_media_attachments(monkeypatch):
    async def fake_run_xpost(*args, **kwargs):
        return {"ok": True, "published": True}

    monkeypatch.setattr("server._run_xpost", fake_run_xpost)

    resp = client.post(
        "/api/publish/post",
        json={
            "text": "hello",
            "attachments": [
                {"kind": "image", "path": "/tmp/a.png"},
                {"kind": "video", "path": "/tmp/b.mp4"},
            ],
            "publish": True,
            "scheduled_at": None,
        },
    )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/jackwl/Code/gitcode/gitxPost && python -m pytest web/api/test_publish_media_upload.py -v`

Expected: fail with missing `/api/upload/media`, missing `attachments` field, and/or missing attachment propagation.

- [ ] **Step 3: Confirm the failure is the right one**

Expected failure should show the current code only understands `/api/upload/image` and `images`, not mixed media attachments.

### Task 2: Implement backend media attachment plumbing and static upload serving

**Files:**
- Modify: `web/api/server.py`
- Modify: `xpost.py`
- Modify: `auto_publish_post.py`

- [ ] **Step 1: Add the minimal backend implementation**

```python
import uuid

from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


class MediaAttachment(BaseModel):
    kind: str
    path: str
    filename: Optional[str] = None
    url: Optional[str] = None


class PublishPostRequest(BaseModel):
    text: str
    attachments: list[MediaAttachment] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    publish: bool = True
    scheduled_at: Optional[str] = None


@app.post("/api/upload/media")
async def upload_media(file: UploadFile = File(...)):
    if not file.content_type:
        raise HTTPException(400, detail="只支持图片或视频文件")
    if not (
        file.content_type.startswith("image/")
        or file.content_type.startswith("video/")
    ):
        raise HTTPException(400, detail="只支持图片或视频文件")
    ext = Path(file.filename).suffix if file.filename else ""
    filename = f"{uuid.uuid4().hex}{ext or '.bin'}"
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(await file.read())
    return {
        "ok": True,
        "kind": "video" if file.content_type.startswith("video/") else "image",
        "path": str(filepath),
        "filename": filename,
        "url": f"/uploads/{filename}",
    }


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
```

- [ ] **Step 2: Teach publish execution to pass mixed attachments through to `xpost post`**

```python
attachment_paths = [item.path for item in req.attachments] if req.attachments else []
media_paths = attachment_paths or req.images
result = await _run_xpost(
    "post",
    req.text,
    *(["--media"] + media_paths if media_paths else []),
    *(["--publish"] if req.publish else []),
    "--observe-ms",
    "900",
    timeout=120,
)
```

- [ ] **Step 3: Expand CLI parsing and browser automation to accept `--media`**

```python
p_post.add_argument("--media", nargs="+", help="Media paths (images and videos)")
p_post.add_argument("--images", nargs="+", help=argparse.SUPPRESS)


def validate_media(media: Optional[List[str]]) -> bool:
    if not media:
        return True
    if len(media) > MAX_IMAGES:
        raise ValueError(f"媒体数量超过 {MAX_IMAGES} 张/个限制（当前：{len(media)}）")
    for media_path in media:
        if not Path(media_path).exists():
            raise FileNotFoundError(f"媒体文件不存在: {media_path}")
    return True


def upload_post_media(page: Page, media: List[str], step_pause_ms: int = STEP_PAUSE_MS) -> bool:
    if not media:
        return True

    print(f"   🎞️  上传 {len(media)} 个媒体附件...")

    matched_selector = None
    for selector in SELECTORS["file_input"]:
        try:
            if page.query_selector(selector):
                matched_selector = selector
                break
        except Exception:
            continue

    if matched_selector is None:
        _save_debug_artifacts(page)
        raise RuntimeError("未找到媒体上传 input")

    handle = page.query_selector(matched_selector)
    if handle is None:
        _save_debug_artifacts(page)
        raise RuntimeError(f"未找到媒体上传控件句柄: {matched_selector}")

    abs_media = [str(Path(media_path).expanduser().resolve()) for media_path in media]
    handle.set_input_files(abs_media, timeout=10000)
    page.wait_for_timeout(2500)
    _activate_chrome_window()

    attached = page.eval_on_selector(
        matched_selector,
        "(el) => (el.files && el.files.length) || 0",
    ) or 0

    preview_count = page.evaluate(
        """
        () => {
          const selectors = [
            'button[data-testid="removeMedia"]',
            'button[aria-label*="Remove media"]',
            'div[data-testid="attachments"] *',
            'img[src^="blob:"]',
            'video[src^="blob:"]'
          ];
          return Math.max(0, ...selectors.map((selector) => document.querySelectorAll(selector).length));
        }
        """
    )

    detected = max(attached, preview_count)
    if detected < len(media):
        _save_debug_artifacts(page)
        raise RuntimeError(f"媒体上传不完整：期望 {len(media)} 个，实际检测 {detected} 个")

    print(f"   ✅ 媒体上传成功 (检测到 {detected} 个)")
    _pause_for_observation("媒体已插入", step_pause_ms)
    return True
```

- [ ] **Step 4: Run the backend test again and verify it passes**

Run: `cd /Users/jackwl/Code/gitcode/gitxPost && python -m pytest web/api/test_publish_media_upload.py -v`

Expected: all tests in the new media upload file pass, and existing image upload tests still pass.

### Task 3: Update the `/publish` UI to treat attachments as mixed media

**Files:**
- Modify: `web/ui/src/views/PublishPage.vue`
- Modify: `web/ui/src/api/xpost.js`
- Modify: `web/ui/src/components/PublishQueue.vue`

- [ ] **Step 1: Replace the image-only upload UI with a mixed media picker**

```vue
<input
  ref="fileInput"
  type="file"
  multiple
  accept="image/*,video/*"
  @change="handleFileSelect"
  style="display: none"
/>
```

```js
const attachments = ref([])

function addAttachments(files) {
  const mediaFiles = files.filter(f =>
    f.type.startsWith('image/') || f.type.startsWith('video/')
  )
  if (attachments.value.length + mediaFiles.length > 4) {
    appStore.notify('最多上传 4 个媒体附件', 'error')
    return
  }
  mediaFiles.forEach(file => {
    const reader = new FileReader()
    reader.onload = (e) => {
      attachments.value.push({
        file,
        preview: e.target.result,
        name: file.name,
        kind: file.type.startsWith('video/') ? 'video' : 'image',
      })
    }
    reader.readAsDataURL(file)
  })
}
```

- [ ] **Step 2: Change publish submission to upload attachments via the new API**

```js
const attachmentPayload = []
for (const item of attachments.value) {
  const result = await api.uploadMedia(item.file)
  if (result.ok && result.path) {
    attachmentPayload.push({
      kind: result.kind || item.kind,
      path: result.path,
      filename: result.filename,
      url: result.url,
    })
  } else {
    throw new Error('媒体上传失败')
  }
}
```

```js
const payload = {
  text: postText.value,
  attachments: attachmentPayload,
  publish: true,
  scheduled_at: isScheduled.value && scheduledTime.value
    ? new Date(scheduledTime.value).toISOString()
    : null
}
```

- [ ] **Step 3: Update queue previews so mixed media is readable**

```js
function getContentPreview(task) {
  const attachments = task.content?.attachments || []
  if (attachments.length > 0) {
    const kinds = attachments.map(a => a.kind).join(', ')
    return `📎 ${attachments.length} 个附件 (${kinds})`
  }
  if (task.type === 'post') {
    const text = task.content?.text || ''
    return text.length > 50 ? text.substring(0, 50) + '...' : text
  }
  if (task.type === 'article') {
    const mdPath = task.content?.md_path || ''
    const filename = mdPath.split('/').pop() || '文章'
    return `📄 ${filename}`
  }
  return ''
}
```

- [ ] **Step 4: Build the UI and fix any compile errors**

Run: `cd /Users/jackwl/Code/gitcode/gitxPost/web/ui && npm run build`

Expected: Vite build passes with the new attachment state and API call shape.

### Task 4: Verify mixed-media publish end to end and clean up compatibility

**Files:**
- Modify: `web/api/test_article_image_upload.py`
- Modify: `web/api/test_workflow_api.py`
- Modify: `README.md` or the nearest user-facing publish docs if examples mention `--images`

- [ ] **Step 1: Preserve image-only compatibility and add one mixed-media regression test**

```python
import io
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_publish_post_still_accepts_images(monkeypatch):
    async def fake_run_xpost(*args, **kwargs):
        return {"ok": True, "published": True}

    monkeypatch.setattr("server._run_xpost", fake_run_xpost)

    resp = client.post(
        "/api/publish/post",
        json={
            "text": "hello",
            "images": ["/tmp/a.png"],
            "publish": True,
            "scheduled_at": None,
        },
    )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
```

- [ ] **Step 2: Run the full focused test set**

Run:
`cd /Users/jackwl/Code/gitcode/gitxPost && python -m pytest web/api/test_article_image_upload.py web/api/test_publish_media_upload.py web/api/test_workflow_api.py -v`

Expected: upload tests, publish tests, and existing workflow tests all pass.

- [ ] **Step 3: Smoke-check the browser path manually**

Open `/publish`, upload one image and one video, confirm both previews render, submit, and verify the queue row shows the mixed attachment summary instead of a hard-coded image-only preview.

- [ ] **Step 4: Commit the finished change**

```bash
git add web/api/server.py web/api/test_article_image_upload.py web/api/test_publish_media_upload.py web/api/test_workflow_api.py web/ui/src/views/PublishPage.vue web/ui/src/api/xpost.js web/ui/src/components/PublishQueue.vue auto_publish_post.py xpost.py README.md docs/superpowers/plans/2026-05-22-media-attachments-publish.md
git commit -m "feat: support mixed media attachments in publish flow"
```
