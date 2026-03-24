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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # gitxPost root
XINFO_LOG = BASE_DIR / "xinfo" / "log"
XINFO_DAY = XINFO_LOG / "day"
XINFO_WEEK = XINFO_LOG / "week"
RESULT_JSON = BASE_DIR / "xinfo" / "RESULT.json"
INTERESTS_JSON = XINFO_LOG / "interests.json"
ACTIONS_JSON = XINFO_LOG / "actions.json"
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"
XPOST_PY = BASE_DIR / "xpost.py"
GENERATE_REPLIES_PY = BASE_DIR / "skills" / "x-reply-assistV2" / "scripts" / "generate_replies.py"

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
    for line in markdown_content.split("\n"):
        line = line.strip()
        if not line.startswith("•"):
            continue
        m = re.match(
            r'•\s*(.+?)(?:：|:)\s*(.+?)(?:—|–)\s*@(\w+)\s*·\s*\[原文↗\]\((https://x\.com/[^)]+)\)',
            line,
        )
        if m:
            tweets.append({
                "title": m.group(1).strip(),
                "summary": m.group(2).strip(),
                "author": m.group(3).strip(),
                "url": m.group(4).split("#")[0],
            })

    return {
        "frontmatter": frontmatter,
        "markdown": markdown_content,
        "tweet_links": list(dict.fromkeys(tweet_links)),
        "tweets": tweets,
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
    try:
        return json.loads(out)
    except Exception:
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

@app.get("/api/accounts")
async def list_accounts():
    return await _run_xpost("radar-accounts", "list")


# ---------------------------------------------------------------------------
# Routes: Pipeline (简易版)
# ---------------------------------------------------------------------------

class PipelineRunRequest(BaseModel):
    steps: list[str]  # ["scan", "analyze", "daily"]


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
