#!/usr/bin/env python3
"""
gitxPost Web API — FastAPI 中间层
封装 xpost CLI 命令，为 Vue 前端提供 RESTful 接口。
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
GENERATE_REPLIES_PY = BASE_DIR / "skills" / "x-reply-assistV2" / "scripts" / "generate_replies.py"
PUBLISH_QUEUE_JSON = XINFO_LOG / "publish_queue.json"
UPLOAD_DIR = XINFO_LOG / "uploads"

# 确保上传目录存在
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="gitxPost API", version="0.1.0")

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

# 同一时间只跑一个 xpost 子进程（本地工具：避免多任务抢 Chrome / 状态混乱）
_xpost_run_lock = asyncio.Lock()
_active_xpost_proc: Optional[asyncio.subprocess.Process] = None
_xpost_proc_lock = asyncio.Lock()

# 队列处理器后台任务
_queue_processor_task: Optional[asyncio.Task] = None
_queue_processor_running = False

# WebSocket 连接管理
_ws_connections: set[WebSocket] = set()


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
        result = await _run_xpost("radar-scan", timeout=900)
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


@app.post("/api/radar/daily")
async def radar_daily():
    return await _run_xpost("radar-daily", timeout=300)


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

    if not ACCOUNTS_JSON.exists():
        return {"active": active, "removed": removed}

    try:
        data = json.loads(ACCOUNTS_JSON.read_text("utf-8"))
        accounts = data.get("accounts", [])

        for acc in accounts:
            handle = acc.get("handle")
            status = acc.get("status")

            if not handle:
                continue

            if status == "active":
                active.append({"handle": handle, "status": "active"})
            elif status == "removed":
                removed.append({"handle": handle, "status": "removed"})

        return {"active": active, "removed": removed}

    except Exception as e:
        print(f"读取账号文件失败: {e}")
        return {"active": active, "removed": removed}



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
    if not _ws_connections:
        return
    
    message = {
        "type": event_type,  # "task_added", "task_updated", "task_completed", "task_failed"
        "task_id": task_id,
        "task": task,
        "timestamp": datetime.now().isoformat()
    }
    
    # 广播到所有连接
    disconnected = set()
    for ws in _ws_connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)
    
    # 清理断开的连接
    _ws_connections.difference_update(disconnected)


def _generate_queue_id():
    """生成队列任务 ID"""
    import time
    return f"pq_{int(time.time() * 1000)}"


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
                print("📭 队列为空，处理器进入休眠（60秒后再检查）")
                await asyncio.sleep(60)
                continue
            
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
    images = content.get("images", [])
    publish = content.get("publish", True)
    
    if not text:
        return {"ok": False, "error": "缺少文本内容"}
    
    # 调用发布接口
    args = ["post", text]
    if images:
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
    """关闭时停止队列处理器"""
    global _queue_processor_running, _queue_processor_task
    _queue_processor_running = False
    if _queue_processor_task:
        _queue_processor_task.cancel()
        try:
            await _queue_processor_task
        except asyncio.CancelledError:
            pass
    print("✅ 后台队列处理器已停止")


@app.get("/api/publish/queue")
async def get_publish_queue():
    """获取发布队列"""
    data = _read_publish_queue()
    return {"ok": True, "queue": data.get("queue", [])}


@app.websocket("/ws/queue")
async def websocket_queue(websocket: WebSocket):
    """WebSocket 端点 - 实时推送队列更新"""
    await websocket.accept()
    _ws_connections.add(websocket)
    print(f"🔌 WebSocket 连接建立，当前连接数: {len(_ws_connections)}")
    
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
        print(f"⚠️  WebSocket 错误: {e}")
    finally:
        _ws_connections.discard(websocket)
        print(f"🔌 WebSocket 连接断开，当前连接数: {len(_ws_connections)}")


@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片"""
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, detail="只支持图片文件")
    
    # 生成唯一文件名
    import uuid
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    
    # 保存文件
    try:
        content = await file.read()
        filepath.write_bytes(content)
    except Exception as e:
        raise HTTPException(500, detail=f"文件保存失败: {str(e)}")
    
    return {
        "ok": True,
        "path": str(filepath),
        "filename": filename,
        "url": f"/uploads/{filename}"
    }


class PublishPostRequest(BaseModel):
    text: str
    images: list[str] = []
    publish: bool = True
    scheduled_at: Optional[str] = None


@app.post("/api/publish/post")
async def publish_post(req: PublishPostRequest):
    """发布 Post（立即或定时）"""
    # 验证文本长度
    if len(req.text) > 280:
        raise HTTPException(400, detail="文本长度不能超过 280 字符")
    
    if not req.text.strip():
        raise HTTPException(400, detail="文本不能为空")
    
    # 验证图片数量
    if len(req.images) > 4:
        raise HTTPException(400, detail="最多上传 4 张图片")
    
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
            result = await _run_xpost(
                "post",
                req.text,
                *(["--images"] + req.images if req.images else []),
                *(["--publish"] if req.publish else []),
                "--observe-ms", "900",
                timeout=120
            )
            
            # 记录到队列（已完成状态）
            queue_data = _read_publish_queue()
            task = {
                "id": _generate_queue_id(),
                "type": "post",
                "status": "done" if result.get("ok") else "failed",
                "created_at": now.isoformat(),
                "scheduled_at": scheduled_dt.isoformat(),
                "executed_at": datetime.now().isoformat(),
                "content": {
                    "text": req.text,
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
        task = {
            "id": _generate_queue_id(),
            "type": "post",
            "status": "scheduled",
            "created_at": now.isoformat(),
            "scheduled_at": scheduled_dt.isoformat(),
            "executed_at": None,
            "content": {
                "text": req.text,
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
    return await _run_xpost("scheduler", "run-now", timeout=900)


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
            r = await _run_xpost("radar-scan", timeout=900)
        elif step == "analyze":
            r = await _run_xpost("radar-analyze", "--days", "7")
        elif step == "daily":
            r = await _run_xpost("radar-daily", timeout=300)
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
