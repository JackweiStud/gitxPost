#!/usr/bin/env python3
"""
gitxPost Web API — FastAPI 中间层
封装 xpost CLI 命令，为 Vue 前端提供 RESTful 接口。
"""

import asyncio
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # gitxPost root
XINFO_LOG = BASE_DIR / "xinfo" / "log"
XINFO_DAY = XINFO_LOG / "day"
XINFO_WEEK = XINFO_LOG / "week"
RESULT_JSON = BASE_DIR / "xinfo" / "RESULT.json"
INTERESTS_JSON = XINFO_LOG / "interests.json"
ACTIONS_JSON = XINFO_LOG / "actions.json"
X_IDEAS_SCAN_PY = BASE_DIR / "xinfo" / "x_ideas_scan.py"
ACCOUNTS_JSON = BASE_DIR / "xinfo" / "accounts.json"
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"
XPOST_PY = BASE_DIR / "xpost.py"
BEST_TIME_ANALYZER_PY = BASE_DIR / "analyze_best_time_v2.py"
BEST_TIME_ANALYSIS_JSON = XINFO_LOG / "best_time_analysis_v2.json"
GENERATE_REPLIES_PY = BASE_DIR / "skills" / "x-reply-assistV2" / "scripts" / "generate_replies.py"
DAILY_OPPORTUNITIES_JS = BASE_DIR / "scripts" / "daily_opportunities.js"
PUBLISH_QUEUE_JSON = XINFO_LOG / "publish_queue.json"
UPLOAD_DIR = XINFO_LOG / "uploads"
ARTICLES_DIR = XINFO_LOG / "articles"

# 确保上传目录存在
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 确保文章目录存在
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="gitxPost API", version="0.1.0")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_running_tasks: dict[str, dict] = {}

# 网页按钮 / 流水线扫描：RSS 探测失败则本轮 CDP，最多 100 账号
_RADAR_SCAN_CLI = ("radar-scan", "--source", "auto", "--limit", "100")
_RADAR_SCAN_TIMEOUT_S = 2700  # 45 min；100 个 CDP 账号约 15–40 分钟
_SCHEDULER_RUN_NOW_TIMEOUT_S = 5400  # 90 min：扫描 + 日报 + 机会 + 粉丝统计

# 同一时间只跑一个 xpost 子进程（本地工具：避免多任务抢 Chrome / 状态混乱）
_xpost_run_lock = asyncio.Lock()
_active_xpost_proc: Optional[asyncio.subprocess.Process] = None
_xpost_proc_lock = asyncio.Lock()

# 队列处理器后台任务
_queue_processor_task: Optional[asyncio.Task] = None
_queue_processor_running = False

# WebSocket 连接管理
_ws_connections: set[WebSocket] = set()


# ---------------------------------------------------------------------------
# WebSocket Manager
# ---------------------------------------------------------------------------

class WebSocketManager:
    """WebSocket 连接管理器 - 处理连接生命周期和消息广播"""
    
    def __init__(self, name: str):
        """初始化管理器
        
        Args:
            name: 管理器名称，用于日志标识
        """
        self.name = name
        self.connections: set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """接受并注册新连接
        
        Args:
            websocket: WebSocket 连接对象
        """
        await websocket.accept()
        self.connections.add(websocket)
        print(f"🔌 [{self.name}] WebSocket 连接建立，当前连接数: {len(self.connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开并清理连接
        
        Args:
            websocket: WebSocket 连接对象
        """
        self.connections.discard(websocket)
        print(f"🔌 [{self.name}] WebSocket 连接断开，当前连接数: {len(self.connections)}")
    
    async def broadcast(self, message: dict):
        """广播消息到所有连接
        
        Args:
            message: 要广播的消息字典
        """
        if not self.connections:
            return
        
        disconnected = set()
        
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"⚠️  [{self.name}] 向 WebSocket 发送消息失败: {e}")
                disconnected.add(ws)
        
        # 清理断开的连接
        self.connections.difference_update(disconnected)
        
        if disconnected:
            print(f"🧹 [{self.name}] 清理了 {len(disconnected)} 个断开的连接")
    
    async def close_all(self):
        """关闭所有连接（应用关闭时调用）"""
        print(f"🧹 [{self.name}] 关闭 {len(self.connections)} 个 WebSocket 连接")
        
        for ws in list(self.connections):
            try:
                await ws.close()
            except Exception:
                pass
        
        self.connections.clear()


# 创建管理器实例
_queue_ws_manager = WebSocketManager("Queue")
_article_ws_manager = WebSocketManager("Article")


def _python_bin() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return "python3"


def _extract_last_json(text: str):
    """从混合了日志文本的 stdout 中提取最后一个完整 JSON 对象。"""
    # 从末尾向前找最后一个 '}'，再向前找匹配的 '{'
    end = text.rfind("}")
    if end < 0:
        return None
    depth = 0
    for i in range(end, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[i: end + 1])
                except Exception:
                    return None
    return None


async def _run_xpost(*args: str, timeout: int = 600) -> dict:
    global _active_xpost_proc
    async with _xpost_run_lock:
        cmd = [_python_bin(), str(XPOST_PY), *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
        )
        async with _xpost_proc_lock:
            _active_xpost_proc = proc
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await asyncio.wait_for(proc.wait(), timeout=15)
            except asyncio.TimeoutError:
                pass
            raise HTTPException(504, detail="命令执行超时")
        finally:
            async with _xpost_proc_lock:
                if _active_xpost_proc is proc:
                    _active_xpost_proc = None

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        # xpost CLI 的 stdout 可能混合进度日志和 JSON 输出，
        # 尝试直接解析，失败则从末尾向前查找最后一个 JSON 对象
        try:
            return json.loads(out)
        except Exception:
            pass

        last_json = _extract_last_json(out)
        if last_json is not None:
            return last_json

        return {"ok": False, "stdout": out, "stderr": err, "returncode": proc.returncode}


def _classify_upload_kind(content_type: Optional[str]) -> Optional[str]:
    if not content_type:
        return None
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    return None


async def _store_media_upload(file: UploadFile, *, allow_video: bool) -> dict:
    kind = _classify_upload_kind(file.content_type)
    detail = "只支持图片文件" if not allow_video else "只支持图片或视频文件"
    if kind is None:
        raise HTTPException(400, detail=detail)
    if kind == "video" and not allow_video:
        raise HTTPException(400, detail=detail)

    ext = Path(file.filename).suffix if file.filename else ""
    if not ext:
        ext = ".mp4" if kind == "video" else ".jpg"

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename

    try:
        filepath.write_bytes(await file.read())
    except Exception as exc:
        raise HTTPException(500, detail=f"文件保存失败: {str(exc)}")

    return {
        "ok": True,
        "kind": kind,
        "path": str(filepath),
        "filename": filename,
        "url": f"/uploads/{filename}",
    }


async def _run_daily_opportunities(timeout: int = 600) -> dict:
    """生成日报后的借势机会文件。失败不应吞掉日报本身结果。"""
    proc = await asyncio.create_subprocess_exec(
        "node",
        str(DAILY_OPPORTUNITIES_JS),
        "--json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(BASE_DIR),
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": "opportunities generation timeout"}

    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()
    try:
        return json.loads(out)
    except Exception:
        parsed = _extract_last_json(out)
        if parsed is not None:
            return parsed
        return {"ok": False, "stdout": out, "stderr": err, "returncode": proc.returncode}


async def _run_best_time_analyzer(timeout: int = 120) -> dict:
    proc = await asyncio.create_subprocess_exec(
        _python_bin(),
        str(BEST_TIME_ANALYZER_PY),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(BASE_DIR),
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await asyncio.wait_for(proc.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass
        raise HTTPException(504, detail="最佳发帖时间估计执行超时")

    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()
    payload = _read_json(BEST_TIME_ANALYSIS_JSON)
    return {
        "ok": proc.returncode == 0 and bool(payload),
        "analysis": payload,
        "stdout_tail": out[-3000:] if out else "",
        "stderr_tail": err[-1200:] if err else "",
        "returncode": proc.returncode,
    }


async def _kill_active_xpost() -> dict:
    """终止当前由 _run_xpost 启动的子进程（用于用户中断「一键日报」等长任务）。"""
    async with _xpost_proc_lock:
        proc = _active_xpost_proc
    if proc is None:
        return {"ok": True, "cancelled": False, "message": "当前没有正在执行的 xpost 任务"}
    if proc.returncode is not None:
        return {"ok": True, "cancelled": False, "message": "任务已结束"}
    try:
        proc.kill()
        await asyncio.wait_for(proc.wait(), timeout=15)
    except (ProcessLookupError, OSError):
        pass
    except asyncio.TimeoutError:
        pass
    return {"ok": True, "cancelled": True, "message": "已发送终止信号"}


def _read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return default


def _read_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return path.read_text("utf-8")


def _parse_radar_post_time(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        from email.utils import parsedate_to_datetime

        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def _normalize_radar_post_url(url: str) -> str:
    return re.sub(r"#.*$", "", url or "").strip()


def _classify_radar_text_language(text: str) -> str:
    """Classify a post's content language using visible script evidence only."""
    cleaned = re.sub(r"https?://\S+|x\.com/\S+|[@#]\w+", " ", text or "")
    cjk = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
    latin = len(re.findall(r"[A-Za-z]", cleaned))
    japanese = len(re.findall(r"[\u3040-\u30ff]", cleaned))
    korean = len(re.findall(r"[\uac00-\ud7af]", cleaned))
    total = cjk + latin + japanese + korean

    if total < 8:
        return "unknown"
    if cjk >= 6 or (cjk >= 3 and cjk / max(1, total) >= 0.18):
        return "zh"
    if latin >= 12 and cjk <= 2 and japanese + korean == 0:
        return "en"
    return "other"


def _load_account_language_profile() -> tuple[dict[str, dict], dict]:
    """Build account language labels from the latest 3 deduped radar post samples."""
    posts_by_account: dict[str, dict[str, dict]] = {}
    latest_scan_time = ""
    latest_snapshot = ""

    for result_path in sorted(XINFO_DAY.glob("*_result.json")):
        data = _read_json(result_path, {})
        if not isinstance(data, dict):
            continue
        summary = data.get("summary") or {}
        scan_time = summary.get("scan_time") or ""
        if scan_time and scan_time > latest_scan_time:
            latest_scan_time = scan_time
            latest_snapshot = str(result_path)

        for item in summary.get("new_ideas_preview") or []:
            account = (item.get("account") or "").strip()
            url = _normalize_radar_post_url(item.get("link") or "")
            if not account or not url:
                continue

            text = f"{item.get('title') or ''} {item.get('summary') or ''}"
            post = {
                "time": _parse_radar_post_time(item.get("time") or ""),
                "language": _classify_radar_text_language(text),
            }
            bucket = posts_by_account.setdefault(account.lower(), {})
            old = bucket.get(url)
            if old is None or post["time"] >= old["time"]:
                bucket[url] = post

    profile: dict[str, dict] = {}
    for account_key, deduped_posts in posts_by_account.items():
        latest_posts = sorted(deduped_posts.values(), key=lambda row: row["time"], reverse=True)[:3]
        counts = {"en": 0, "zh": 0, "other": 0, "unknown": 0}
        for post in latest_posts:
            lang = post.get("language") or "unknown"
            counts[lang if lang in counts else "other"] += 1

        if len(latest_posts) >= 3 and counts["en"] >= 2:
            language = "en"
            label = "EN"
        elif len(latest_posts) >= 3 and counts["zh"] >= 2:
            language = "zh"
            label = "CN"
        elif len(latest_posts) >= 3 and counts["other"] >= 2:
            language = "other"
            label = "--"
        else:
            language = "unknown"
            label = "--"

        profile[account_key] = {
            "language": language,
            "language_label": label,
            "language_sample_count": len(latest_posts),
            "language_post_counts": counts,
        }

    meta = {
        "latest_scan_time": latest_scan_time,
        "latest_snapshot": latest_snapshot,
        "update_mode": "computed_on_accounts_request",
        "update_note": "打开或刷新账号页时读取本地最新雷达扫描快照计算；不触发新扫描。",
        "rule": "latest_3_deduped_posts_majority",
    }
    return profile, meta


def _build_language_summary(active: list[dict], language_meta: dict) -> dict:
    total = len(active)
    english_count = sum(1 for acc in active if acc.get("language") == "en")
    chinese_count = sum(1 for acc in active if acc.get("language") == "zh")
    other_count = sum(1 for acc in active if acc.get("language") == "other")
    unknown_count = total - english_count - chinese_count - other_count
    classified_total = english_count + chinese_count + other_count

    def pct(count: int) -> float:
        return round(count / total * 100, 1) if total else 0.0

    return {
        "active_total": total,
        "classified_total": classified_total,
        "english_count": english_count,
        "chinese_count": chinese_count,
        "other_count": other_count,
        "unknown_count": unknown_count,
        "english_percent": pct(english_count),
        "chinese_percent": pct(chinese_count),
        "other_percent": pct(other_count),
        "unknown_percent": pct(unknown_count),
        **language_meta,
    }


def _attach_language_to_report_tweets(report: dict) -> dict:
    language_profile, _ = _load_account_language_profile()
    account_languages = {
        handle: {
            "language": row.get("language", "unknown"),
            "language_label": row.get("language_label", "--"),
            "language_sample_count": row.get("language_sample_count", 0),
            "language_post_counts": row.get(
                "language_post_counts",
                {"en": 0, "zh": 0, "other": 0, "unknown": 0},
            ),
        }
        for handle, row in language_profile.items()
    }

    for tweet in report.get("tweets", []):
        language = account_languages.get((tweet.get("author") or "").lower(), {})
        tweet["language"] = language.get("language", "unknown")
        tweet["language_label"] = language.get("language_label", "--")
        tweet["language_sample_count"] = language.get("language_sample_count", 0)
        tweet["language_post_counts"] = language.get(
            "language_post_counts",
            {"en": 0, "zh": 0, "other": 0, "unknown": 0},
        )

    report["account_languages"] = account_languages
    return report


def _list_daily_reports() -> list[dict]:
    if not XINFO_DAY.exists():
        return []
    reports = []
    for f in sorted(XINFO_DAY.glob("*.md"), reverse=True):
        name = f.stem
        reports.append({
            "date": name,
            "path": str(f),
            "size": f.stat().st_size,
        })
    return reports


def _list_weekly_reports() -> list[dict]:
    """列出所有周报文件"""
    if not XINFO_WEEK.exists():
        return []
    reports = []
    for f in sorted(XINFO_WEEK.glob("*.md"), reverse=True):
        reports.append({
            "date": f.stem,
            "path": str(f),
            "size": f.stat().st_size,
        })
    return reports


def _extract_markdown_from_report_body(body_text: str) -> str:
    """从日报 body 中提取 markdown 内容。

    日报文件格式为 frontmatter + JSON body，但 JSON 中 markdown 值内含有
    未转义的引号导致 json.loads 失败。这里用多种策略兜底提取。
    """
    # 策略 1: 标准 JSON 解析
    try:
        data = json.loads(body_text)
        md = data.get("markdown", "")
        if md:
            return md.replace("\\n", "\n") if ("\\n" in md and "\n" not in md) else md
    except Exception:
        pass

    # 策略 2: 定位 "markdown" 字段值的起止位置
    # 找到 "markdown": " 或 "markdown":" 后的内容，直到 ","actions" 或文件末尾
    for marker_start in ['"markdown": "', '"markdown":"']:
        idx = body_text.find(marker_start)
        if idx < 0:
            continue
        content_start = idx + len(marker_start)

        # 找结束位置：","actions" 或 JSON 结尾
        end_markers = ['","actions"', '"\n}', '"}']
        end_idx = len(body_text)
        for em in end_markers:
            pos = body_text.find(em, content_start)
            if pos > 0:
                end_idx = min(end_idx, pos)

        raw = body_text[content_start:end_idx]
        # 将 JSON 转义的 \n 转为真正换行
        raw = raw.replace("\\n", "\n")
        if raw.strip():
            return raw

    # 策略 3: 整个 body 当作纯 markdown（兜底）
    return body_text


def _parse_daily_report(md_text: str) -> dict:
    """从日报 Markdown 中提取结构化数据：frontmatter + JSON body + 推文链接列表"""
    frontmatter = {}
    body_text = md_text

    if md_text.startswith("---"):
        end = md_text.find("\n---", 3)
        if end != -1:
            fm_block = md_text[3:end].strip()
            for line in fm_block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip()] = v.strip().strip('"')
            body_text = md_text[end + 4:].strip()

    markdown_content = _extract_markdown_from_report_body(body_text)

    tweet_links = []
    link_pattern = re.compile(r'\[原文↗\]\((https://x\.com/[^)]+)\)')
    for match in link_pattern.finditer(markdown_content):
        url = match.group(1).split("#")[0]
        tweet_links.append(url)

    tweets = []
    seen_urls = set()
    for line in markdown_content.split("\n"):
        line = line.strip()
        if not line.startswith("•"):
            continue
        m = re.match(
            r'•\s*(.+?)(?:：|:)\s*(.+?)(?:—|–)\s*@(\w+)\s*·\s*\[原文↗\]\((https://x\.com/[^)]+)\)',
            line,
        )
        if m:
            url = m.group(4).split("#")[0]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            tweets.append({
                "title": m.group(1).strip(),
                "summary": m.group(2).strip(),
                "author": m.group(3).strip(),
                "url": url,
            })

    return {
        "frontmatter": frontmatter,
        "markdown": markdown_content,
        "tweet_links": list(dict.fromkeys(tweet_links)),
        "tweets": tweets,
    }


def _extract_weekly_account_actions(markdown: str) -> dict:
    """从周报 Markdown 中提取推荐关注和建议移除的账号列表"""
    recommended_adds = []
    suggested_removes = []

    lines = markdown.split("\n")
    current_section = None      # "recommend" | "remove" | "keep" | None
    in_table = False            # 是否在表格内
    
    for line in lines:
        stripped = line.strip()
        
        # 检测章节标题
        if "二度人脉推荐" in stripped:
            current_section = "recommend"
            in_table = False
            continue
        if "账号调整建议" in stripped:
            current_section = "adjust"
            in_table = False
            continue
        # 检测子章节（在 adjust 内）
        if current_section == "adjust" or current_section in ("keep", "remove"):
            if "建议移除" in stripped or ("❌" in stripped and "建议" in stripped):
                current_section = "remove"
                in_table = False
                continue
            if "建议保留" in stripped or ("✅" in stripped and "建议" in stripped):
                current_section = "keep"
                in_table = False
                continue
        # 遇到下一个 H2 标题，重置
        if stripped.startswith("## ") or stripped.startswith("# "):
            if current_section not in ("adjust", "keep", "remove"):
                current_section = None
            if stripped.startswith("## ") and "二度" not in stripped and "账号" not in stripped:
                current_section = None
            in_table = False
            continue
        
        # 检测表格（Markdown 表格以 | 开头）
        if stripped.startswith("|"):
            # 推荐关注区域的表格
            if current_section == "recommend":
                # 跳过表头和分隔行
                if "账号" in stripped or "---" in stripped:
                    in_table = True
                    continue
                # 解析表格行
                if in_table:
                    parts = [p.strip() for p in stripped.split("|")]
                    if len(parts) >= 4:  # | 账号 | 被推荐次数 | 推荐来源 | ...
                        account_cell = parts[1] if len(parts) > 1 else ""
                        source_cell = parts[3] if len(parts) > 3 else ""
                        suggestion_cell = parts[-2] if len(parts) > 4 else ""  # 倒数第二列通常是"建议"
                        
                        # 提取账号
                        match = re.search(r'@(\w+)', account_cell)
                        if match:
                            handle = match.group(1)
                            # context 使用推荐来源
                            context = source_cell.strip()
                            # description 使用建议列
                            description = suggestion_cell.strip()
                            recommended_adds.append({
                                "handle": handle,
                                "context": context,
                                "description": description,
                            })
                continue
            
            # 建议移除区域的表格
            elif current_section == "remove":
                # 跳过表头和分隔行
                if "账号" in stripped or "---" in stripped or "推荐" in stripped:
                    in_table = True
                    continue
                # 解析表格行
                if in_table:
                    parts = [p.strip() for p in stripped.split("|")]
                    if len(parts) >= 3:  # | 账号 | 原创率 | 推文数 | 理由
                        account_cell = parts[1] if len(parts) > 1 else ""
                        rate_cell = parts[2] if len(parts) > 2 else ""
                        reason_cell = parts[-2] if len(parts) > 3 else ""  # 理由列
                        
                        # 提取账号
                        match = re.search(r'@(\w+)', account_cell)
                        if match:
                            handle = match.group(1)
                            # context 使用原创率 + 理由
                            context = f"{rate_cell} 原创率，{reason_cell}".strip("，")
                            suggested_removes.append({
                                "handle": handle,
                                "context": context,
                            })
                continue
        
        # 提取 @username（列表格式，兼容旧格式）
        if current_section == "recommend" and not in_table:
            # 格式: - @username（context）- description
            # 或:   - @username（context）
            matches = re.findall(r'@(\w+)', stripped)
            if matches and stripped.startswith("-"):
                handle = matches[0]  # 第一个是主账号
                # 提取括号内 context
                ctx = re.search(r'[（(](.+?)[）)]', stripped)
                context = ctx.group(1) if ctx else ""
                # 提取 - 后的描述
                desc = re.search(r'[）)]\s*[-—–]\s*(.+)', stripped)
                description = desc.group(1).strip() if desc else ""
                recommended_adds.append({
                    "handle": handle,
                    "context": context,
                    "description": description,
                })
        
        elif current_section == "remove" and not in_table:
            # 格式 A (列表): - @username（context）
            if stripped.startswith("-"):
                matches = re.findall(r'@(\w+)', stripped)
                for handle in matches:
                    ctx = re.search(
                        rf'@{handle}\s*[（(](.+?)[）)]', stripped
                    )
                    context = ctx.group(1) if ctx else ""
                    suggested_removes.append({
                        "handle": handle,
                        "context": context,
                    })
            # 格式 B (逗号分隔): - @a、@b、@c（原创率 xx%）
            elif "、" in stripped and "@" in stripped:
                # 提取所有 @username
                handles = re.findall(r'@(\w+)', stripped)
                # 整行括号说明作为共享 context
                ctx = re.search(r'[（(](.+?)[）)]', stripped)
                context = ctx.group(1) if ctx else ""
                for handle in handles:
                    suggested_removes.append({
                        "handle": handle,
                        "context": context,
                    })

    return {
        "recommended_adds": recommended_adds,
        "suggested_removes": suggested_removes,
    }


def _parse_weekly_report(md_text: str) -> dict:
    """解析周报：frontmatter + markdown body
    
    周报文件格式为 frontmatter + JSON body（与日报类似），需要提取 JSON 中的 markdown 字段
    """
    frontmatter = {}
    body_text = md_text
    
    # 提取 frontmatter
    if md_text.startswith("---"):
        end = md_text.find("\n---", 3)
        if end != -1:
            fm_block = md_text[3:end].strip()
            for line in fm_block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip()] = v.strip().strip('"')
            body_text = md_text[end + 4:].strip()
    
    # 提取 markdown 内容（周报也使用 JSON 包裹格式）
    markdown_content = _extract_markdown_from_report_body(body_text)
    
    # 提取账号操作建议
    account_actions = _extract_weekly_account_actions(markdown_content)
    
    return {
        "frontmatter": frontmatter,
        "markdown": markdown_content,
        **account_actions,  # recommended_adds, suggested_removes
    }


# ---------------------------------------------------------------------------
# Routes: Status
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def get_status():
    result_data = _read_json(RESULT_JSON)
    scan_summary = result_data.get("summary", {}) if result_data else {}
    reports = _list_daily_reports()
    latest_report = reports[0] if reports else None

    return {
        "ok": True,
        "scan": {
            "last_scan_time": scan_summary.get("scan_time"),
            "total_accounts": scan_summary.get("account_stats", {}).get("total", 0),
            "successful_accounts": scan_summary.get("account_stats", {}).get("success", 0),
            "new_tweets": scan_summary.get("new_tweets_count", 0),
            "new_originals": scan_summary.get("new_originals_count", 0),
            "status": scan_summary.get("status", "unknown"),
        },
        "latest_report": latest_report,
        "report_count": len(reports),
        "running_tasks": {k: v.get("status") for k, v in _running_tasks.items()},
    }


# ---------------------------------------------------------------------------
# Routes: Radar
# ---------------------------------------------------------------------------

@app.post("/api/radar/cancel")
async def radar_cancel():
    """中断当前正在执行的 xpost 子进程（一键日报 / 扫描 / 分析 / 日报生成 / 回帖等）。"""
    return await _kill_active_xpost()


@app.post("/api/radar/scan")
async def radar_scan():
    task_id = f"scan_{datetime.now().strftime('%H%M%S')}"
    _running_tasks[task_id] = {"status": "running", "command": "radar-scan", "started": datetime.now().isoformat()}

    try:
        result = await _run_xpost(*_RADAR_SCAN_CLI, timeout=_RADAR_SCAN_TIMEOUT_S)
        _running_tasks[task_id]["status"] = "done"
        _running_tasks[task_id]["result"] = result
        return result
    except Exception as e:
        _running_tasks[task_id]["status"] = "error"
        _running_tasks[task_id]["error"] = str(e)
        raise


@app.post("/api/radar/analyze")
async def radar_analyze(days: int = 7):
    return await _run_xpost("radar-analyze", "--days", str(days))


@app.get("/api/radar/best-time")
async def get_best_time_analysis():
    analysis = _read_json(BEST_TIME_ANALYSIS_JSON)
    return {"ok": bool(analysis), "analysis": analysis}


@app.post("/api/radar/best-time")
async def run_best_time_analysis():
    return await _run_best_time_analyzer()


@app.post("/api/radar/daily")
async def radar_daily():
    result = await _run_xpost("radar-daily", timeout=300)
    if result.get("ok"):
        result["opportunities"] = await _run_daily_opportunities(timeout=600)
    return result


@app.get("/api/radar/reports")
async def list_reports():
    return {"ok": True, "reports": _list_daily_reports()}


@app.get("/api/radar/report/{date}")
async def get_report(date: str):
    md_path = XINFO_DAY / f"{date}.md"
    raw = _read_text(md_path)
    if raw is None:
        raise HTTPException(404, detail=f"日报不存在: {date}")
    parsed = _parse_daily_report(raw)
    parsed = _attach_language_to_report_tweets(parsed)
    return {"ok": True, "date": date, **parsed}


@app.get("/api/radar/weekly-reports")
async def list_weekly_reports():
    """列出所有周报文件"""
    return {"ok": True, "reports": _list_weekly_reports()}


@app.get("/api/radar/weekly-report/{date}")
async def get_weekly_report(date: str):
    """获取指定日期的周报详情"""
    md_path = XINFO_WEEK / f"{date}.md"
    raw = _read_text(md_path)
    if raw is None:
        raise HTTPException(404, detail=f"周报不存在: {date}")
    parsed = _parse_weekly_report(raw)
    return {"ok": True, "date": date, **parsed}


@app.post("/api/radar/weekly")
async def radar_weekly():
    """触发周报生成"""
    return await _run_xpost("radar-weekly", timeout=300)


@app.get("/api/radar/result")
async def get_scan_result(limit: int = 50, offset: int = 0):
    data = _read_json(RESULT_JSON)
    if not data:
        raise HTTPException(404, detail="扫描结果不存在")

    preview = data.get("summary", {}).get("new_ideas_preview", [])
    total = len(preview)
    sliced = preview[offset: offset + limit]

    return {
        "ok": True,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": sliced,
        "summary": {
            "scan_time": data.get("summary", {}).get("scan_time"),
            "total_accounts": data.get("summary", {}).get("account_stats", {}).get("total"),
            "new_tweets": data.get("summary", {}).get("new_tweets_count"),
            "new_originals": data.get("summary", {}).get("new_originals_count"),
        },
    }


@app.get("/api/radar/interests")
async def get_interests():
    data = _read_json(INTERESTS_JSON, {})
    return {"ok": True, **data}


class UpdateInterestsRequest(BaseModel):
    focus: list[str] = []
    recent_context: list[str] = []
    ignore: list[str] = []
    preferred_formats: list[str] = []


@app.put("/api/radar/interests")
async def update_interests(req: UpdateInterestsRequest):
    """更新兴趣画像"""
    # 读取现有数据保留 _comment 等元字段
    existing = _read_json(INTERESTS_JSON, {})
    
    # 更新四个核心字段
    existing["focus"] = [s.strip() for s in req.focus if s.strip()]
    existing["recent_context"] = [s.strip() for s in req.recent_context if s.strip()]
    existing["ignore"] = [s.strip() for s in req.ignore if s.strip()]
    existing["preferred_formats"] = [s.strip() for s in req.preferred_formats if s.strip()]
    existing["_updated"] = datetime.now().strftime("%Y-%m-%d")
    
    # 写回文件
    INTERESTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    INTERESTS_JSON.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    return {
        "ok": True,
        "updated_at": existing["_updated"],
        "counts": {
            "focus": len(existing["focus"]),
            "recent_context": len(existing["recent_context"]),
            "ignore": len(existing["ignore"]),
            "preferred_formats": len(existing["preferred_formats"]),
        }
    }


# ---------------------------------------------------------------------------
# Routes: Reply
# ---------------------------------------------------------------------------

class ReplyExtractRequest(BaseModel):
    url: str


class GenerateRepliesRequest(BaseModel):
    tweet_text: str
    handle: str


class SendReplyRequest(BaseModel):
    url: str
    text: str
    publish: bool = False


@app.post("/api/reply/extract")
async def reply_extract(req: ReplyExtractRequest):
    return await _run_xpost("reply-extract", req.url, timeout=120)


@app.post("/api/reply/generate")
async def generate_replies(req: GenerateRepliesRequest):
    cmd = [_python_bin(), str(GENERATE_REPLIES_PY), req.tweet_text[:2000], req.handle]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(BASE_DIR),
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(504, detail="回复生成超时")

    out = stdout.decode("utf-8", errors="replace").strip()
    
    # 先尝试直接解析，失败则使用 _extract_last_json 兜底
    try:
        return json.loads(out)
    except Exception:
        result = _extract_last_json(out)
        if result:
            return result
        raise HTTPException(500, detail=f"回复生成失败: {out}")


@app.post("/api/reply/send")
async def send_reply(req: SendReplyRequest):
    args = ["reply", req.url, req.text]
    if req.publish:
        args.append("--publish")
    args.extend(["--observe-ms", "900"])
    return await _run_xpost(*args, timeout=120)


# ---------------------------------------------------------------------------
# Routes: Accounts
# ---------------------------------------------------------------------------

def _parse_accounts_stdout(stdout: str) -> dict:
    """解析 manage_accounts.py list 的文本输出为结构化数据"""
    active = []
    removed = []
    current_section = None
    
    for line in stdout.splitlines():
        line = line.strip()
        if "活跃账号" in line:
            current_section = "active"
            continue
        if "已注释" in line or "已移除" in line:
            current_section = "removed"
            continue
        
        # 匹配 "  1. @username" 或 "      @username"
        m = re.match(r'^\s*(?:\d+\.\s*)?@(\w+)', line)
        if m:
            handle = m.group(1)
            if current_section == "active":
                active.append({"handle": handle, "status": "active"})
            elif current_section == "removed":
                removed.append({"handle": handle, "status": "removed"})
    
    return {"active": active, "removed": removed}


def _read_accounts_from_file() -> dict:
    """直接从 accounts.json 读取账号列表（不依赖 xpost 子进程）"""
    active = []
    removed = []
    language_profile, language_meta = _load_account_language_profile()

    if not ACCOUNTS_JSON.exists():
        return {"active": active, "removed": removed, "language_summary": _build_language_summary(active, language_meta)}

    try:
        data = json.loads(ACCOUNTS_JSON.read_text("utf-8"))
        accounts = data.get("accounts", [])

        for acc in accounts:
            handle = acc.get("handle")
            status = acc.get("status")

            if not handle:
                continue

            language = language_profile.get(handle.lower(), {})
            row = {
                "handle": handle,
                "status": status,
                "note": acc.get("note", ""),
                "language": language.get("language", "unknown"),
                "language_label": language.get("language_label", "--"),
                "language_sample_count": language.get("language_sample_count", 0),
                "language_post_counts": language.get(
                    "language_post_counts",
                    {"en": 0, "zh": 0, "other": 0, "unknown": 0},
                ),
            }

            if status == "active":
                active.append(row)
            elif status == "removed":
                removed.append(row)

        return {
            "active": active,
            "removed": removed,
            "language_summary": _build_language_summary(active, language_meta),
        }

    except Exception as e:
        print(f"读取账号文件失败: {e}")
        return {"active": active, "removed": removed, "language_summary": _build_language_summary(active, language_meta)}



@app.get("/api/accounts")
async def list_accounts():
    """旧端点，保持兼容"""
    return await _run_xpost("radar-accounts", "list")


@app.get("/api/radar/accounts")
async def list_radar_accounts():
    """列出所有监控账号（结构化）- 直接读取文件，不阻塞"""
    parsed = _read_accounts_from_file()
    return {
        "ok": True,
        "accounts": parsed["active"] + parsed["removed"],
        "active_count": len(parsed["active"]),
        "removed_count": len(parsed["removed"]),
        "language_summary": parsed["language_summary"],
    }


class AddAccountRequest(BaseModel):
    handle: str
    note: str = ""


@app.post("/api/radar/accounts")
async def add_radar_account(req: AddAccountRequest):
    """添加监控账号"""
    handle = req.handle.lstrip("@").strip()
    if not handle:
        raise HTTPException(400, detail="handle 不能为空")
    if not req.note.strip():
        raise HTTPException(400, detail="note 不能为空")
    return await _run_xpost("radar-accounts", "add", handle, req.note)


@app.delete("/api/radar/accounts/{handle}")
async def remove_radar_account(handle: str):
    """移除监控账号（软删除）"""
    handle = handle.lstrip("@").strip()
    if not handle:
        raise HTTPException(400, detail="handle 不能为空")
    return await _run_xpost("radar-accounts", "remove", handle)


@app.put("/api/radar/accounts/{handle}/restore")
async def restore_radar_account(handle: str):
    """恢复已移除账号"""
    handle = handle.lstrip("@").strip()
    if not handle:
        raise HTTPException(400, detail="handle 不能为空")
    return await _run_xpost("radar-accounts", "restore", handle)


@app.post("/api/radar/following-sync")
async def sync_following_with_radar():
    """同步 @jackaiwison Following，并生成 Radar 差异报表。"""
    return await _run_xpost(
        "following-sync",
        "jackaiwison",
        "--timeout",
        "45",
        "--idle-rounds",
        "20",
        timeout=900,
    )


# ---------------------------------------------------------------------------
# Routes: Pipeline (简易版)
# ---------------------------------------------------------------------------

class PipelineRunRequest(BaseModel):
    steps: list[str]  # ["scan", "analyze", "daily"]


# ---------------------------------------------------------------------------
# Routes: Followers
# ---------------------------------------------------------------------------

FOLLOWERS_JSON = XINFO_LOG / "followers.json"


@app.get("/api/followers")
async def get_followers():
    """读取粉丝历史数据"""
    data = _read_json(FOLLOWERS_JSON)
    if data is None:
        return {"ok": True, "username": "", "records": []}
    return {"ok": True, **data}


@app.post("/api/followers/fetch")
async def fetch_followers(username: str = "jackaiwison"):
    """触发浏览器采集粉丝数"""
    return await _run_xpost("follower-stats", username, timeout=120)


# ---------------------------------------------------------------------------
# Routes: Publish Queue
# ---------------------------------------------------------------------------

def _read_publish_queue():
    """读取发布队列"""
    if not PUBLISH_QUEUE_JSON.exists():
        return {"queue": []}
    try:
        return json.loads(PUBLISH_QUEUE_JSON.read_text("utf-8"))
    except Exception:
        return {"queue": []}


def _write_publish_queue(data):
    """写入发布队列"""
    PUBLISH_QUEUE_JSON.parent.mkdir(parents=True, exist_ok=True)
    PUBLISH_QUEUE_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


async def _broadcast_queue_update(event_type: str, task_id: str = None, task: dict = None):
    """广播队列更新到所有 WebSocket 连接"""
    message = {
        "type": event_type,  # "task_added", "task_updated", "task_completed", "task_failed"
        "task_id": task_id,
        "task": task,
        "timestamp": datetime.now().isoformat()
    }
    
    await _queue_ws_manager.broadcast(message)


def _generate_queue_id():
    """生成队列任务 ID"""
    import time
    return f"pq_{int(time.time() * 1000)}"


# ---------------------------------------------------------------------------
# Helpers: Articles
# ---------------------------------------------------------------------------

def _generate_article_id():
    """生成文章 ID - 格式: art_<timestamp_ms>_<suffix>"""
    import time
    import uuid
    return f"art_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


def _article_root(article_id: str) -> Path:
    return ARTICLES_DIR / article_id


def _article_images_dir(article_id: str) -> Path:
    return _article_root(article_id) / "images"


def _article_json_path(article_id: str) -> Path:
    return _article_root(article_id) / "article.json"


def _article_md_path(article_id: str) -> Path:
    return _article_root(article_id) / "article.md"


def _legacy_article_json_path(article_id: str) -> Path:
    return ARTICLES_DIR / f"{article_id}.json"


def _legacy_article_md_path(article_id: str) -> Path:
    return ARTICLES_DIR / f"{article_id}.md"


def _legacy_article_backup_paths(article_id: str) -> list[Path]:
    return sorted(ARTICLES_DIR.glob(f"{article_id}.skeleton.*.md"))


def _extract_markdown_image_paths(markdown: str) -> list[str]:
    return re.findall(r"!\[[^\]]*\]\(([^)]+)\)", markdown or "")


def _ensure_article_storage(article_id: str) -> Path:
    root = _article_root(article_id)
    root.mkdir(parents=True, exist_ok=True)
    _article_images_dir(article_id).mkdir(parents=True, exist_ok=True)
    return root


def _migrate_legacy_article_storage(article_id: str):
    """将旧的根目录文章文件迁移到每篇文章独立目录。"""
    root = _ensure_article_storage(article_id)
    legacy_json = _legacy_article_json_path(article_id)
    legacy_md = _legacy_article_md_path(article_id)
    new_json = _article_json_path(article_id)
    new_md = _article_md_path(article_id)

    if legacy_json.exists():
        if not new_json.exists():
            shutil.move(str(legacy_json), str(new_json))
        else:
            legacy_json.unlink()

    if legacy_md.exists():
        if not new_md.exists():
            shutil.move(str(legacy_md), str(new_md))
        else:
            legacy_md.unlink()

    for legacy_backup in _legacy_article_backup_paths(article_id):
        target = root / legacy_backup.name
        if not target.exists():
            shutil.move(str(legacy_backup), str(target))
        else:
            legacy_backup.unlink()

    markdown_source = None
    if new_md.exists():
        markdown_source = new_md.read_text("utf-8")
    elif legacy_md.exists():
        markdown_source = legacy_md.read_text("utf-8")

    if not markdown_source:
        return

    shared_images_dir = ARTICLES_DIR / "images"
    if not shared_images_dir.exists():
        return

    for rel_path in _extract_markdown_image_paths(markdown_source):
        normalized = rel_path.strip().lstrip("./")
        if not normalized.startswith("images/"):
            continue

        relative_name = normalized[len("images/") :]
        if not relative_name:
            continue

        src = shared_images_dir / relative_name
        dst = root / normalized
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _migrate_existing_articles_storage():
    article_ids: set[str] = set()
    for json_file in ARTICLES_DIR.glob("*.json"):
        article_ids.add(json_file.stem)
    for md_file in ARTICLES_DIR.glob("*.md"):
        if ".skeleton." in md_file.name:
            article_ids.add(md_file.name.split(".skeleton.", 1)[0])
        else:
            article_ids.add(md_file.stem)

    for article_id in sorted(article_ids):
        _migrate_legacy_article_storage(article_id)


def _read_article(article_id: str) -> Optional[dict]:
    """读取文章 JSON 元数据"""
    _migrate_legacy_article_storage(article_id)

    json_path = _article_json_path(article_id)
    if not json_path.exists():
        json_path = _legacy_article_json_path(article_id)
    if not json_path.exists():
        return None
    try:
        data = json.loads(json_path.read_text("utf-8"))
        data["md_path"] = str(_article_md_path(article_id))
        return data
    except Exception as e:
        print(f"⚠️  读取文章元数据失败 {article_id}: {e}")
        return None


def _write_article(article_id: str, data: dict):
    """原子性写入文章 JSON 元数据"""
    from datetime import timezone
    
    _ensure_article_storage(article_id)
    data["md_path"] = str(_article_md_path(article_id))
    json_path = _article_json_path(article_id)
    temp_path = json_path.with_suffix(".json.tmp")
    
    try:
        # 确保目录存在
        _ensure_article_storage(article_id)
        
        # 写入临时文件
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        # 原子性重命名
        temp_path.rename(json_path)
    except Exception as e:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"写入文章元数据失败 {article_id}: {e}")


def _read_article_content(article_id: str) -> Optional[str]:
    """读取文章 Markdown 内容"""
    _migrate_legacy_article_storage(article_id)

    md_path = _article_md_path(article_id)
    if not md_path.exists():
        md_path = _legacy_article_md_path(article_id)
    if not md_path.exists():
        return None
    try:
        return md_path.read_text("utf-8")
    except Exception as e:
        print(f"⚠️  读取文章内容失败 {article_id}: {e}")
        return None


def _write_article_content(article_id: str, content: str):
    """原子性写入文章 Markdown 内容"""
    _ensure_article_storage(article_id)
    md_path = _article_md_path(article_id)
    temp_path = md_path.with_suffix(".md.tmp")
    
    try:
        # 确保目录存在
        ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        
        # 写入临时文件
        temp_path.write_text(content, encoding="utf-8")
        
        # 原子性重命名
        temp_path.rename(md_path)
    except Exception as e:
        # 清理临时文件
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"写入文章内容失败 {article_id}: {e}")


def _list_articles() -> list[dict]:
    """列出所有文章，按 updated_at 倒序排列"""
    if not ARTICLES_DIR.exists():
        return []
    
    articles = []
    article_ids: set[str] = set()
    for article_dir in ARTICLES_DIR.iterdir():
        if article_dir.is_dir() and (article_dir / "article.json").exists():
            article_ids.add(article_dir.name)
    for json_file in ARTICLES_DIR.glob("*.json"):
        article_ids.add(json_file.stem)

    for article_id in sorted(article_ids):
        try:
            data = _read_article(article_id)
            if not data:
                continue
            # 只返回基本信息，不包含 content
            articles.append({
                "id": data.get("id"),
                "title": data.get("title"),
                "status": data.get("status"),
                "step": data.get("step"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "published_at": data.get("published_at"),
            })
        except Exception as e:
            print(f"⚠️  读取文章列表时跳过损坏文件 {article_id}: {e}")
            continue
    
    # 按 updated_at 倒序排列
    articles.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    return articles


async def _broadcast_article_update(event_type: str, article_id: str, data: dict = None):
    """广播文章更新到所有 Article WebSocket 连接
    
    Args:
        event_type: 事件类型（article_outline_generating, article_outline_generated, etc.）
        article_id: 文章 ID
        data: 附加数据（如生成的内容）
    """
    from datetime import timezone
    
    message = {
        "type": event_type,
        "article_id": article_id,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await _article_ws_manager.broadcast(message)


async def _process_queue_background():
    """后台队列处理器 - 智能调度"""
    global _queue_processor_running
    _queue_processor_running = True
    
    print("🚀 队列处理器已启动")
    
    while _queue_processor_running:
        try:
            data = _read_publish_queue()
            queue = data.get("queue", [])
            
            # 检查是否有待处理任务
            scheduled_tasks = [t for t in queue if t.get("status") == "scheduled"]
            
            if not scheduled_tasks:
                print("📭 队列为空，处理器自动退出")
                _queue_processor_running = False
                break  # 退出循环，结束处理器
            
            from datetime import timezone
            now = datetime.now(timezone.utc)
            
            # 查找最近要执行的任务
            next_task_time = None
            for task in scheduled_tasks:
                scheduled_at = task.get("scheduled_at")
                if not scheduled_at:
                    continue
                
                try:
                    scheduled_dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
                    if scheduled_dt.tzinfo is None:
                        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
                    
                    if next_task_time is None or scheduled_dt < next_task_time:
                        next_task_time = scheduled_dt
                except Exception:
                    continue
            
            # 执行到期任务
            executed_any = False
            for task in queue:
                if task.get("status") != "scheduled":
                    continue
                
                scheduled_at = task.get("scheduled_at")
                if not scheduled_at:
                    continue
                
                try:
                    scheduled_dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
                    if scheduled_dt.tzinfo is None:
                        scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    task["status"] = "failed"
                    task["error"] = "时间格式错误"
                    _write_publish_queue(data)
                    continue
                
                # 如果还没到时间，跳过
                if scheduled_dt > now:
                    continue
                
                # 根据任务类型执行
                task_type = task.get("type", "post")
                print(f"📤 执行队列任务 {task['id']} (类型: {task_type})")
                task["status"] = "publishing"
                _write_publish_queue(data)
                
                try:
                    if task_type == "post":
                        result = await _execute_post_task(task)
                    elif task_type == "article":
                        result = await _execute_article_task(task)
                    else:
                        raise ValueError(f"未知任务类型: {task_type}")
                    
                    if result.get("ok"):
                        task["status"] = "done"
                        task["executed_at"] = datetime.now(timezone.utc).isoformat()
                        task["result"] = result
                        print(f"✅ 队列任务 {task['id']} 完成")
                        # 广播任务完成
                        await _broadcast_queue_update("task_completed", task["id"], task)
                    else:
                        task["status"] = "failed"
                        task["error"] = result.get("error", "执行失败")
                        print(f"❌ 队列任务 {task['id']} 失败")
                        # 广播任务失败
                        await _broadcast_queue_update("task_failed", task["id"], task)
                    
                    executed_any = True
                    
                except Exception as e:
                    task["status"] = "failed"
                    task["error"] = str(e)
                    print(f"❌ 队列任务 {task['id']} 异常: {e}")
                    # 广播任务失败
                    await _broadcast_queue_update("task_failed", task["id"], task)
                
                _write_publish_queue(data)
            
            if executed_any:
                print(f"✅ 队列处理完成，继续监控")
                continue
            
            # 计算下次检查时间
            if next_task_time:
                wait_seconds = max(1, (next_task_time - now).total_seconds())
                # 最多等待 60 秒，避免长时间不检查
                wait_seconds = min(wait_seconds, 60)
                print(f"⏰ 下个任务在 {next_task_time.strftime('%H:%M:%S')}，等待 {int(wait_seconds)} 秒")
                await asyncio.sleep(wait_seconds)
            else:
                await asyncio.sleep(60)
                
        except Exception as e:
            print(f"⚠️  队列处理器错误: {e}")
            await asyncio.sleep(10)
            continue


def _ensure_queue_processor_running():
    """确保队列处理器正在运行"""
    global _queue_processor_task, _queue_processor_running
    
    if _queue_processor_task is None or _queue_processor_task.done():
        _queue_processor_running = True
        _queue_processor_task = asyncio.create_task(_process_queue_background())
        print("✅ 队列处理器已启动")


async def _execute_post_task(task: dict) -> dict:
    """执行 Post 发布任务"""
    content = task.get("content", {})
    text = content.get("text", "")
    attachments = content.get("attachments", [])
    images = content.get("images", [])
    publish = content.get("publish", True)
    
    if not text:
        return {"ok": False, "error": "缺少文本内容"}
    
    # 调用发布接口
    args = ["post", text]
    media = [
        item.get("path")
        for item in attachments
        if isinstance(item, dict) and item.get("path")
    ]
    if media:
        args.extend(["--media"] + media)
    elif images:
        args.extend(["--images"] + images)
    if publish:
        args.append("--publish")
    args.extend(["--no-wait", "--observe-ms", "900"])
    
    return await _run_xpost(*args, timeout=180)


async def _execute_article_task(task: dict) -> dict:
    """执行 Article 发布任务"""
    content = task.get("content", {})
    md_path = content.get("md_path", "")
    publish = content.get("publish", True)
    
    if not md_path:
        return {"ok": False, "error": "缺少文章路径"}
    
    # 调用文章发布接口
    args = ["article", md_path]
    if publish:
        args.append("--publish")
    args.extend(["--no-wait", "--observe-ms", "900"])
    
    return await _run_xpost(*args, timeout=300)


@app.on_event("startup")
async def startup_event():
    """启动时检查是否有待处理任务"""
    _migrate_existing_articles_storage()

    data = _read_publish_queue()
    queue = data.get("queue", [])
    scheduled_tasks = [t for t in queue if t.get("status") == "scheduled"]
    
    if scheduled_tasks:
        print(f"📋 发现 {len(scheduled_tasks)} 个待处理任务，启动队列处理器")
        _ensure_queue_processor_running()
    else:
        print("📭 队列为空，队列处理器待命")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时停止队列处理器和 WebSocket 连接"""
    global _queue_processor_running, _queue_processor_task
    
    # 停止队列处理器
    _queue_processor_running = False
    if _queue_processor_task:
        _queue_processor_task.cancel()
        try:
            await _queue_processor_task
        except asyncio.CancelledError:
            pass
    print("✅ 后台队列处理器已停止")
    
    # 关闭所有 WebSocket 连接
    await _queue_ws_manager.close_all()
    await _article_ws_manager.close_all()



@app.get("/api/publish/queue")
async def get_publish_queue():
    """获取发布队列"""
    data = _read_publish_queue()
    return {"ok": True, "queue": data.get("queue", [])}


@app.websocket("/ws/queue")
async def websocket_queue(websocket: WebSocket):
    """WebSocket 端点 - 实时推送队列更新"""
    await _queue_ws_manager.connect(websocket)
    
    try:
        # 发送当前队列状态
        data = _read_publish_queue()
        await websocket.send_json({
            "type": "initial",
            "queue": data.get("queue", [])
        })
        
        # 保持连接，等待客户端断开
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"⚠️  [Queue] WebSocket 错误: {e}")
    finally:
        _queue_ws_manager.disconnect(websocket)


@app.websocket("/ws/articles")
async def websocket_articles(websocket: WebSocket):
    """WebSocket 端点 - 实时推送文章更新"""
    await _article_ws_manager.connect(websocket)
    
    try:
        # 发送当前文章列表
        articles = _list_articles()
        await websocket.send_json({
            "type": "initial",
            "articles": articles
        })
        
        # 保持连接，等待客户端断开
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"⚠️  [Article] WebSocket 错误: {e}")
    finally:
        _article_ws_manager.disconnect(websocket)



@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片"""
    return await _store_media_upload(file, allow_video=False)


@app.post("/api/upload/media")
async def upload_media(file: UploadFile = File(...)):
    """上传图片或视频"""
    return await _store_media_upload(file, allow_video=True)


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


@app.post("/api/publish/post")
async def publish_post(req: PublishPostRequest):
    """发布 Post（立即或定时）"""
    if not req.text.strip():
        raise HTTPException(400, detail="文本不能为空")

    media_paths = [item.path for item in req.attachments] if req.attachments else list(req.images)
    if len(media_paths) > 4:
        raise HTTPException(400, detail="最多上传 4 个媒体附件")
    
    # 解析定时时间
    scheduled_at = req.scheduled_at
    from datetime import timezone
    now = datetime.now(timezone.utc)
    
    if scheduled_at:
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            # 确保有时区信息
            if scheduled_dt.tzinfo is None:
                scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
        except Exception:
            raise HTTPException(400, detail="时间格式错误，应为 ISO 8601 格式")
    else:
        scheduled_dt = now
    
    # 判断是立即执行还是加入队列
    is_immediate = scheduled_dt <= now
    
    if is_immediate:
        # 立即执行
        try:
            post_args = [
                "post",
                req.text,
            ]
            if req.attachments:
                post_args += ["--media", *media_paths]
            elif req.images:
                post_args += ["--images", *media_paths]
            if req.publish:
                post_args += ["--publish"]
            post_args += ["--observe-ms", "900"]
            result = await _run_xpost(
                *post_args,
                timeout=120
            )
            
            # 记录到队列（已完成状态）
            queue_data = _read_publish_queue()
            stored_attachments = (
                [item.model_dump() for item in req.attachments]
                if req.attachments
                else [{"kind": "image", "path": path} for path in req.images]
            )
            task = {
                "id": _generate_queue_id(),
                "type": "post",
                "status": "done" if result.get("ok") else "failed",
                "created_at": now.isoformat(),
                "scheduled_at": scheduled_dt.isoformat(),
                "executed_at": datetime.now().isoformat(),
                "content": {
                    "text": req.text,
                    "attachments": stored_attachments,
                    "images": req.images
                },
                "result": result,
                "error": result.get("error") if not result.get("ok") else None
            }
            queue_data["queue"].append(task)
            _write_publish_queue(queue_data)
            
            return {
                "ok": result.get("ok", False),
                "mode": "immediate",
                "task_id": task["id"],
                "result": result
            }
        except Exception as exc:
            raise HTTPException(500, detail=f"发布失败: {str(exc)}")
    else:
        # 加入队列
        queue_data = _read_publish_queue()
        stored_attachments = (
            [item.model_dump() for item in req.attachments]
            if req.attachments
            else [{"kind": "image", "path": path} for path in req.images]
        )
        task = {
            "id": _generate_queue_id(),
            "type": "post",
            "status": "scheduled",
            "created_at": now.isoformat(),
            "scheduled_at": scheduled_dt.isoformat(),
            "executed_at": None,
            "content": {
                "text": req.text,
                "attachments": stored_attachments,
                "images": req.images,
                "publish": req.publish
            },
            "result": None,
            "error": None
        }
        queue_data["queue"].append(task)
        _write_publish_queue(queue_data)
        
        # 广播任务添加
        await _broadcast_queue_update("task_added", task["id"], task)
        
        # 启动队列处理器（如果未运行）
        _ensure_queue_processor_running()
        
        return {
            "ok": True,
            "mode": "scheduled",
            "task_id": task["id"],
            "scheduled_at": scheduled_dt.isoformat()
        }


@app.delete("/api/publish/{task_id}")
async def delete_publish_task(task_id: str):
    """删除发布任务"""
    queue_data = _read_publish_queue()
    queue = queue_data.get("queue", [])
    
    # 查找任务
    task_index = None
    for i, task in enumerate(queue):
        if task["id"] == task_id:
            task_index = i
            break
    
    if task_index is None:
        raise HTTPException(404, detail="任务不存在")
    
    # 删除任务
    deleted_task = queue.pop(task_index)
    _write_publish_queue(queue_data)
    
    return {
        "ok": True,
        "deleted_task_id": task_id,
        "deleted_task": deleted_task
    }


@app.put("/api/publish/{task_id}/cancel")
async def cancel_publish_task(task_id: str):
    """取消排队中的任务"""
    queue_data = _read_publish_queue()
    queue = queue_data.get("queue", [])
    
    # 查找任务
    task = None
    for t in queue:
        if t["id"] == task_id:
            task = t
            break
    
    if task is None:
        raise HTTPException(404, detail="任务不存在")
    
    if task["status"] not in ["scheduled", "running"]:
        raise HTTPException(400, detail="只能取消排队中或执行中的任务")
    
    # 更新状态
    task["status"] = "cancelled"
    task["error"] = "用户取消"
    _write_publish_queue(queue_data)
    
    return {
        "ok": True,
        "task_id": task_id,
        "status": "cancelled"
    }


@app.post("/api/publish/{task_id}/retry")
async def retry_publish_task(task_id: str):
    """重试失败的任务"""
    queue_data = _read_publish_queue()
    queue = queue_data.get("queue", [])
    
    # 查找任务
    task = None
    for t in queue:
        if t["id"] == task_id:
            task = t
            break
    
    if task is None:
        raise HTTPException(404, detail="任务不存在")
    
    if task["status"] != "failed":
        raise HTTPException(400, detail="只能重试失败的任务")
    
    # 重置状态，设置为立即执行
    task["status"] = "scheduled"
    task["scheduled_at"] = datetime.now().isoformat()
    task["executed_at"] = None
    task["result"] = None
    task["error"] = None
    _write_publish_queue(queue_data)
    
    return {
        "ok": True,
        "task_id": task_id,
        "status": "scheduled",
        "message": "任务已重新加入队列"
    }


# ---------------------------------------------------------------------------
# Routes: Articles
# ---------------------------------------------------------------------------

class CreateArticleRequest(BaseModel):
    title: str


class UpdateArticleRequest(BaseModel):
    content: str | None = None
    title: str | None = None
    style: str | None = None


@app.post("/api/articles")
async def create_article(req: CreateArticleRequest):
    """创建新文章"""
    from datetime import timezone
    
    # 验证标题非空
    if not req.title.strip():
        raise HTTPException(400, detail="标题不能为空")
    
    # 生成唯一 article_id
    article_id = _generate_article_id()
    
    # 创建初始 JSON 元数据
    now = datetime.now(timezone.utc).isoformat()
    article_data = {
        "id": article_id,
        "title": req.title.strip(),
        "status": "draft",
        "step": "title",
        "created_at": now,
        "updated_at": now,
        "published_at": None,
        "outline": "",
        "content": "",
        "md_path": str(_article_md_path(article_id)),
        "publish_result": None
    }
    
    # 保存元数据
    try:
        _write_article(article_id, article_data)
    except Exception as e:
        raise HTTPException(500, detail=f"创建文章失败: {str(e)}")
    
    # 广播文章创建事件
    await _broadcast_article_update("article_created", article_id, {
        "id": article_id,
        "title": article_data["title"],
        "status": article_data["status"],
        "step": article_data["step"]
    })
    
    return {
        "ok": True,
        "article_id": article_id,
        "title": article_data["title"],
        "created_at": article_data["created_at"]
    }


@app.get("/api/articles")
async def get_articles():
    """获取文章列表（按 updated_at 倒序）"""
    articles = _list_articles()
    
    return {
        "ok": True,
        "articles": articles,
        "total": len(articles)
    }


@app.get("/api/articles/{article_id}")
async def get_article(article_id: str):
    """获取文章详情（包含完整内容）"""
    # 读取元数据
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")
    
    # 读取 Markdown 内容
    content = _read_article_content(article_id)
    if content is not None:
        article["content"] = content
    
    return {
        "ok": True,
        "article": article
    }


@app.put("/api/articles/{article_id}")
async def update_article(article_id: str, req: UpdateArticleRequest):
    """更新文章内容、标题或风格"""
    from datetime import timezone
    
    # 读取现有文章
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")
    
    # 至少要有一个可更新字段
    if req.content is None and req.title is None and req.style is None:
        raise HTTPException(400, detail="至少需要提供 content、title 或 style 之一")

    # 更新字段和时间戳
    if req.content is not None:
        article["content"] = req.content
    if req.title is not None:
        title = req.title.strip()
        if not title:
            raise HTTPException(400, detail="标题不能为空")
        article["title"] = title
    if req.style is not None:
        if req.style not in ["zara", "tech", "fun"]:
            raise HTTPException(400, detail=f"无效的风格参数: {req.style}，支持的风格: zara, tech, fun")
        article["style"] = req.style
    article["updated_at"] = datetime.now(timezone.utc).isoformat()

    # 保存元数据和内容
    try:
        _write_article(article_id, article)
        if req.content is not None:
            _write_article_content(article_id, req.content)
    except Exception as e:
        raise HTTPException(500, detail=f"更新文章失败: {str(e)}")
    
    # 广播文章更新事件
    await _broadcast_article_update("article_updated", article_id, {
        "updated_at": article["updated_at"]
    })
    
    return {
        "ok": True,
        "article_id": article_id,
        "updated_at": article["updated_at"]
    }


@app.delete("/api/articles/{article_id}")
async def delete_article(article_id: str):
    """删除文章"""
    # 检查文章是否存在
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")
    
    # 删除 JSON 元数据文件
    json_path = _article_json_path(article_id)
    md_path = _article_md_path(article_id)
    legacy_json_path = _legacy_article_json_path(article_id)
    legacy_md_path = _legacy_article_md_path(article_id)
    
    try:
        if _article_root(article_id).exists():
            shutil.rmtree(_article_root(article_id))
        for path in [json_path, md_path, legacy_json_path, legacy_md_path]:
            if path.exists():
                path.unlink()
        for backup in _legacy_article_backup_paths(article_id):
            if backup.exists():
                backup.unlink()
    except Exception as e:
        raise HTTPException(500, detail=f"删除文章失败: {str(e)}")
    
    # 广播文章删除事件
    await _broadcast_article_update("article_deleted", article_id, {})
    
    return {
        "ok": True,
        "article_id": article_id,
        "message": "文章已删除"
    }


@app.post("/api/articles/{article_id}/cancel")
async def cancel_article_generation(article_id: str):
    """取消当前正在进行的生成任务
    
    Returns:
        {
            "ok": true,
            "cancelled": true,
            "message": "已取消生成任务"
        }
    """
    return await _kill_active_xpost()


@app.post("/api/articles/{article_id}/outline")
async def generate_article_outline(article_id: str):
    """生成文章骨架（异步）"""
    from datetime import timezone
    
    # 验证文章存在
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")
    
    # 验证步骤（可选：只在 title 步骤才能生成骨架）
    # if article.get("step") != "title":
    #     raise HTTPException(400, detail=f"当前步骤为 {article['step']}，无法生成骨架")
    
    title = article.get("title", "")
    if not title:
        raise HTTPException(400, detail="文章标题为空，无法生成骨架")
    
    md_path = _article_md_path(article_id)
    
    # 立即返回 202 Accepted
    # 启动后台任务
    asyncio.create_task(_generate_outline_background(article_id, title, str(md_path)))
    
    return {
        "ok": True,
        "article_id": article_id,
        "status": "generating",
        "message": "骨架生成任务已启动"
    }


async def _generate_outline_background(article_id: str, title: str, md_path: str):
    """后台任务：生成文章骨架"""
    from datetime import timezone
    
    try:
        # 广播开始生成
        await _broadcast_article_update("article_outline_generating", article_id, {
            "title": title
        })
        
        # 调用 xpost init 命令（添加 --style 参数，默认使用 tech 风格）
        result = await _run_xpost("init", md_path, "--topic", title, "--style", "tech", timeout=120)
        
        # xpost init 返回的是 {"created": true, ...} 而不是 {"ok": true}
        # 检查是否成功创建
        if result.get("created") or result.get("ok"):
            # 读取生成的内容
            content = _read_article_content(article_id)
            if content is None:
                content = ""
            
            # 更新文章元数据
            article = _read_article(article_id)
            if article:
                article["outline"] = content
                article["content"] = content
                article["step"] = "outline"
                article["updated_at"] = datetime.now(timezone.utc).isoformat()
                _write_article(article_id, article)
            
            # 广播生成成功
            await _broadcast_article_update("article_outline_generated", article_id, {
                "outline": content,
                "step": "outline"
            })
        else:
            # 广播生成失败
            error_msg = result.get("error", "骨架生成失败")
            await _broadcast_article_update("article_error", article_id, {
                "error": error_msg,
                "step": "outline_generation",
                "result": result
            })
    
    except Exception as e:
        # 广播异常错误
        await _broadcast_article_update("article_error", article_id, {
            "error": str(e),
            "step": "outline_generation"
        })


@app.post("/api/articles/{article_id}/generate")
async def generate_article_content(article_id: str):
    """生成文章全文（异步）"""
    from datetime import timezone
    
    # 验证文章存在
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")
    
    # 验证步骤（可选：只在 outline 步骤才能生成全文）
    # if article.get("step") != "outline":
    #     raise HTTPException(400, detail=f"当前步骤为 {article['step']}，无法生成全文")
    
    md_path = _article_md_path(article_id)
    
    # 确保 Markdown 文件存在
    if not md_path.exists():
        raise HTTPException(400, detail="Markdown 文件不存在，请先生成骨架")
    
    # 立即返回 202 Accepted
    # 启动后台任务
    asyncio.create_task(_generate_content_background(article_id, str(md_path)))
    
    return {
        "ok": True,
        "article_id": article_id,
        "status": "generating",
        "message": "全文生成任务已启动"
    }


async def _generate_content_background(article_id: str, md_path: str):
    """后台任务：生成文章全文"""
    from datetime import timezone
    
    try:
        # 广播开始生成
        await _broadcast_article_update("article_content_generating", article_id, {})
        
        # 调用 xpost generate 命令
        result = await _run_xpost("generate", md_path, timeout=300)
        
        if result.get("ok"):
            # 读取生成的内容
            content = _read_article_content(article_id)
            if content is None:
                content = ""
            
            # 更新文章元数据
            article = _read_article(article_id)
            if article:
                article["content"] = content
                article["step"] = "content"
                article["updated_at"] = datetime.now(timezone.utc).isoformat()
                _write_article(article_id, article)
            
            # 广播生成成功
            await _broadcast_article_update("article_content_generated", article_id, {
                "content": content,
                "step": "content"
            })
        else:
            # 广播生成失败
            error_msg = result.get("error", "全文生成失败")
            await _broadcast_article_update("article_error", article_id, {
                "error": error_msg,
                "step": "content_generation"
            })
    
    except Exception as e:
        # 广播异常错误
        await _broadcast_article_update("article_error", article_id, {
            "error": str(e),
            "step": "content_generation"
        })


@app.post("/api/articles/{article_id}/auto-generate")
async def auto_generate_article(article_id: str, style: str = "zara"):
    """一键生成：自动完成 outline → content 流程
    
    Args:
        article_id: 文章 ID
        style: 文章风格 (zara/tech/fun)
    
    Returns:
        {
            "ok": true,
            "article_id": "art_123",
            "status": "generating",
            "message": "自动生成任务已启动"
        }
    """
    from datetime import timezone
    
    # 验证文章存在
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")
    
    # 验证风格参数
    if style not in ["zara", "tech", "fun"]:
        raise HTTPException(400, detail=f"无效的风格参数: {style}，支持的风格: zara, tech, fun")
    
    title = article.get("title", "")
    if not title:
        raise HTTPException(400, detail="文章标题为空，无法生成")
    
    md_path = _article_md_path(article_id)
    
    # 立即返回 202 Accepted
    # 启动后台任务
    asyncio.create_task(_auto_generate_background(article_id, title, str(md_path), style))
    
    return {
        "ok": True,
        "article_id": article_id,
        "status": "generating",
        "message": "自动生成任务已启动",
        "style": style
    }


@app.post("/api/articles/{article_id}/images")
async def upload_article_image(article_id: str, file: UploadFile = File(...)):
    """上传文章图片
    
    Args:
        article_id: 文章 ID
        file: 图片文件
    
    Returns:
        {
            "ok": true,
            "image_url": "/images/articles/art_123/image_456.png",
            "markdown": "![image](/images/articles/art_123/image_456.png)"
        }
    """
    from datetime import timezone
    import time
    
    # 验证文章存在
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")
    
    # 验证文件类型
    allowed_types = ["image/png", "image/jpeg", "image/gif", "image/webp"]
    if not file.content_type or file.content_type not in allowed_types:
        raise HTTPException(400, detail=f"不支持的文件类型: {file.content_type}，仅支持 PNG, JPEG, GIF, WebP")
    
    # 创建图片目录
    images_dir = _article_images_dir(article_id)
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成唯一文件名（使用时间戳）
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    image_id = int(time.time() * 1000)
    filename = f"image_{image_id}{ext}"
    image_path = images_dir / filename
    
    # 保存文件
    try:
        content = await file.read()
        image_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(500, detail=f"图片保存失败: {str(e)}")
    
    # 更新文章元数据
    if "images" not in article:
        article["images"] = []
    article["images"].append(filename)
    article["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    try:
        _write_article(article_id, article)
    except Exception as e:
        # 如果元数据更新失败，删除已上传的图片
        if image_path.exists():
            image_path.unlink()
        raise HTTPException(500, detail=f"更新文章元数据失败: {str(e)}")
    
    # 返回相对 URL 和 Markdown 语法
    image_url = f"/images/articles/{article_id}/{filename}"
    markdown = f"![{filename}]({image_url})"
    
    return {
        "ok": True,
        "image_url": image_url,
        "markdown": markdown,
        "filename": filename
    }


@app.get("/images/articles/{article_id}/{image_path:path}")
async def serve_article_image(article_id: str, image_path: str):
    """提供文章图片静态访问。

    兼容两种来源：
    1. 手动上传：/images/articles/<article_id>/<filename>
    2. 生成内容相对路径：/images/articles/<article_id>/images/<filename>
    """
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")

    normalized_path = image_path.lstrip("/")
    article_root = _article_root(article_id)
    candidates = [
        article_root / normalized_path,
        article_root / "images" / normalized_path,
        ARTICLES_DIR / normalized_path,
        ARTICLES_DIR / "images" / normalized_path,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return FileResponse(candidate)

    raise HTTPException(404, detail=f"图片不存在: {article_id}/{image_path}")


@app.post("/api/articles/{article_id}/publish")
async def publish_article(article_id: str):
    """发布文章（异步）"""
    from datetime import timezone
    
    # 验证文章存在
    article = _read_article(article_id)
    if article is None:
        raise HTTPException(404, detail=f"文章不存在: {article_id}")
    
    # 验证步骤（可选：只在 content 或 preview 步骤才能发布）
    # if article.get("step") not in ["content", "preview"]:
    #     raise HTTPException(400, detail=f"当前步骤为 {article['step']}，无法发布")
    
    md_path = _article_md_path(article_id)
    
    # 确保 Markdown 文件存在
    if not md_path.exists():
        raise HTTPException(400, detail="Markdown 文件不存在，请先生成内容")
    
    # 立即返回 202 Accepted
    # 启动后台任务
    asyncio.create_task(_publish_article_background(article_id, str(md_path)))
    
    return {
        "ok": True,
        "article_id": article_id,
        "status": "publishing",
        "message": "文章发布任务已启动"
    }


async def _auto_generate_background(article_id: str, title: str, md_path: str, style: str = "zara"):
    """后台任务：自动生成 outline + content
    
    Args:
        article_id: 文章 ID
        title: 文章标题
        md_path: Markdown 文件路径
        style: 文章风格 (zara/tech/fun)
    """
    from datetime import timezone
    
    try:
        # Step 1: Generate outline
        await _broadcast_article_update("article_outline_generating", article_id, {
            "step": "outline",
            "progress": 0,
            "style": style
        })
        
        # 调用 xpost init 命令，传入 style 参数
        # 一键生成需要从标题重新构建骨架，即使 Markdown 文件已经被自动保存过也要覆盖
        result = await _run_xpost("init", md_path, "--topic", title, "--style", style, "--force", timeout=120)
        
        # xpost init 返回的是 {"created": true, ...} 而不是 {"ok": true}
        if not (result.get("created") or result.get("ok")):
            raise Exception(f"Outline generation failed: {result.get('error', 'Unknown error')}")
        
        # 读取生成的骨架内容
        content = _read_article_content(article_id)
        if content is None:
            content = ""
        
        # 更新文章元数据 - 保存 style
        article = _read_article(article_id)
        if article:
            article["outline"] = content
            article["content"] = content
            article["step"] = "outline"
            article["style"] = style  # 保存风格到元数据
            article["updated_at"] = datetime.now(timezone.utc).isoformat()
            _write_article(article_id, article)
        
        # 广播骨架生成完成
        await _broadcast_article_update("article_outline_generated", article_id, {
            "outline": content,
            "step": "outline",
            "progress": 50,
            "style": style
        })
        
        # Step 2: Generate content
        await _broadcast_article_update("article_content_generating", article_id, {
            "step": "content",
            "progress": 50
        })
        
        # 调用 xpost generate 命令
        result = await _run_xpost("generate", md_path, timeout=300)
        
        if not result.get("ok"):
            raise Exception(f"Content generation failed: {result.get('error', 'Unknown error')}")
        
        # 读取生成的全文内容
        content = _read_article_content(article_id)
        if content is None:
            content = ""
        
        # 更新文章元数据
        article = _read_article(article_id)
        if article:
            article["content"] = content
            article["step"] = "content"
            article["updated_at"] = datetime.now(timezone.utc).isoformat()
            _write_article(article_id, article)
        
        # 广播全文生成完成
        await _broadcast_article_update("article_images_generating", article_id, {
            "step": "images",
            "progress": 90
        })

        image_result = await _run_xpost("auto-img", md_path, "--style", style, "--topic", title, timeout=300)
        if image_result.get("ok"):
            image_generated_at = datetime.now(timezone.utc).isoformat()
            article = _read_article(article_id)
            if article:
                article["updated_at"] = image_generated_at
                generated_images = []
                for item in image_result.get("generated", []):
                    rel_path = str(item.get("relative_path") or "").strip()
                    if not rel_path:
                        continue
                    filename = Path(rel_path).name
                    if filename:
                        generated_images.append(filename)

                if generated_images:
                    existing_images = article.get("images", [])
                    if not isinstance(existing_images, list):
                        existing_images = []
                    article["images"] = list(dict.fromkeys([*existing_images, *generated_images]))

                _write_article(article_id, article)

            await _broadcast_article_update("article_images_generated", article_id, {
                "step": "images",
                "generated_count": len(image_result.get("generated", [])),
                "warnings": image_result.get("warnings", []),
                "progress": 100,
                "updated_at": image_generated_at,
                "generated": image_result.get("generated", [])
            })
        else:
            await _broadcast_article_update("article_images_error", article_id, {
                "error": image_result.get("error", "自动配图失败"),
                "step": "images",
                "result": image_result
            })

        await _broadcast_article_update("article_content_generated", article_id, {
            "content": content,
            "step": "content",
            "progress": 100
        })
        
    except Exception as e:
        # 广播错误
        await _broadcast_article_update("article_error", article_id, {
            "error": str(e),
            "step": "auto_generation"
        })


async def _publish_article_background(article_id: str, md_path: str):
    """后台任务：发布文章"""
    from datetime import timezone
    
    try:
        # 广播开始发布
        await _broadcast_article_update("article_publishing", article_id, {})
        
        # 调用 xpost publish 命令
        result = await _run_xpost("publish", md_path, "--publish", timeout=300)
        
        if result.get("ok"):
            # 提取文章 URL（如果有）
            article_url = result.get("article_url") or result.get("url")
            
            # 更新文章元数据
            article = _read_article(article_id)
            if article:
                article["status"] = "published"
                article["published_at"] = datetime.now(timezone.utc).isoformat()
                article["updated_at"] = datetime.now(timezone.utc).isoformat()
                article["publish_result"] = result
                _write_article(article_id, article)
            
            # 广播发布成功
            await _broadcast_article_update("article_published", article_id, {
                "status": "published",
                "published_at": article["published_at"],
                "article_url": article_url
            })
        else:
            # 广播发布失败
            error_msg = result.get("error", "文章发布失败")
            await _broadcast_article_update("article_error", article_id, {
                "error": error_msg,
                "step": "publishing"
            })
    
    except Exception as e:
        # 广播异常错误
        await _broadcast_article_update("article_error", article_id, {
            "error": str(e),
            "step": "publishing"
        })


# ---------------------------------------------------------------------------
# Routes: Scheduler
# ---------------------------------------------------------------------------

@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """查询调度器状态"""
    return await _run_xpost("scheduler", "status")


class InstallSchedulerRequest(BaseModel):
    time: str = "09:00"


@app.post("/api/scheduler/install")
async def install_scheduler(req: InstallSchedulerRequest):
    """安装调度器"""
    return await _run_xpost("scheduler", "install", "--time", req.time)


@app.post("/api/scheduler/uninstall")
async def uninstall_scheduler():
    """卸载调度器"""
    return await _run_xpost("scheduler", "uninstall")


@app.post("/api/scheduler/run-now")
async def run_scheduler_now():
    """立即执行一次"""
    return await _run_xpost("scheduler", "run-now", timeout=_SCHEDULER_RUN_NOW_TIMEOUT_S)


@app.get("/api/scheduler/logs")
async def get_scheduler_logs(lines: int = 50):
    """获取最近日志"""
    return await _run_xpost("scheduler", "logs", "--lines", str(lines))


# ---------------------------------------------------------------------------
# Routes: Pipeline
# ---------------------------------------------------------------------------

@app.post("/api/pipeline/run")
async def run_pipeline(req: PipelineRunRequest):
    results = []
    for step in req.steps:
        if step == "scan":
            r = await _run_xpost(*_RADAR_SCAN_CLI, timeout=_RADAR_SCAN_TIMEOUT_S)
        elif step == "analyze":
            r = await _run_xpost("radar-analyze", "--days", "7")
        elif step == "daily":
            r = await _run_xpost("radar-daily", timeout=300)
            if r.get("ok"):
                r["opportunities"] = await _run_daily_opportunities(timeout=600)
        elif step == "weekly":
            r = await _run_xpost("radar-weekly", timeout=300)
        else:
            r = {"ok": False, "error": f"未知步骤: {step}"}

        results.append({"step": step, "result": r})
        if not r.get("ok"):
            break

    return {"ok": all(r["result"].get("ok") for r in results), "steps": results}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8900, reload=True)
