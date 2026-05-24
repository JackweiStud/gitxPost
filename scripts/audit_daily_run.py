#!/usr/bin/env python3
"""
gitxPost 全栈自动巡检与审计工具：
1. 探测后端 API 服务 (8900 端口) 健康度
2. 探测前端 Vite 服务 (5900 端口) 连通性
3. 检查调度总日志 (scheduler_*.log) 中是否存在运行异常
4. 汇总多维度结果，若存在任何异常，使用本地 LLM 提炼总结，并使用 gh CLI 提交 GitHub Issue。
"""

import os
import re
import sys
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# 载入项目环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass

def check_api_server_health(port: int = 8900) -> tuple[bool, str]:
    """探测后端 API 服务的健康状态"""
    url = f"http://127.0.0.1:{port}/api/radar/reports"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                return True, "API 服务响应正常 (200)"
            else:
                return False, f"API 服务响应异常，HTTP 状态码: {response.status}"
    except urllib.error.HTTPError as e:
        return False, f"API 服务返回 HTTP 错误: {e.code}"
    except Exception as e:
        return False, f"API 服务连接失败 (已离线或假死): {e}"

def check_frontend_server_health(port: int = 5900) -> tuple[bool, str]:
    """探测前端 Vite 服务是否在监听"""
    url = f"http://127.0.0.1:{port}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            return True, "前端 UI Vite 服务响应正常"
    except Exception as e:
        return False, f"前端 UI Vite 服务连接失败 (已离线): {e}"

def _infer_llm_kind(api_url: str) -> str:
    value = (api_url or "").lower()
    if "/messages" in value or "anthropic" in value:
        return "anthropic"
    return "openai"

def _openai_chat_completions_url(api_url: str) -> str:
    url = (api_url or "").strip().rstrip("/")
    if not url:
        return url
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return f"{url}/chat/completions"
    return url

def _call_llm_once(spec: dict, prompt: str) -> str:
    kind = spec["kind"]
    payload = {
        "model": spec["model"],
        "max_tokens": 1000,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }
    if kind == "anthropic":
        url = spec["api_url"].rstrip("/")
        if url.endswith("/v1"):
            url = f"{url}/messages"
        elif not url.endswith("/messages"):
            url = f"{url}/v1/messages"
    else:
        url = _openai_chat_completions_url(spec["api_url"])

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
    )
    request.add_header("Content-Type", "application/json")
    if kind == "anthropic":
        request.add_header("x-api-key", spec["api_key"])
        request.add_header("anthropic-version", "2023-06-01")
    else:
        request.add_header("Authorization", f"Bearer {spec['api_key']}")

    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8")
    
    data = json.loads(raw)
    if kind == "anthropic":
        parts = [item.get("text", "") for item in data.get("content", []) if item.get("type") == "text"]
        return "\n".join(parts).strip()
    else:
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("No choices in OpenAI response")
        return str((choices[0].get("message") or {}).get("content", "")).strip()

def summarize_errors_with_llm(combined_errors: str) -> dict:
    """调用项目配置的 LLM，提炼汇总多维度的异常信息"""
    chain = []
    primary_key = os.getenv("XPOST_LLM_API_KEY")
    primary_url = os.getenv("XPOST_LLM_API_URL")
    primary_model = os.getenv("XPOST_LLM_MODEL")
    if primary_key and primary_url and primary_model:
        chain.append({
            "api_url": primary_url,
            "api_key": primary_key,
            "model": primary_model,
            "kind": _infer_llm_kind(primary_url)
        })
    
    fallback_url = os.getenv("XPOST_LLM_FALLBACK_API_URL")
    fallback_key = os.getenv("XPOST_LLM_FALLBACK_API_KEY")
    fallback_model = os.getenv("XPOST_LLM_FALLBACK_MODEL")
    if fallback_url and fallback_key and fallback_model:
        chain.append({
            "api_url": fallback_url,
            "api_key": fallback_key,
            "model": fallback_model,
            "kind": (os.getenv("XPOST_LLM_FALLBACK_API_KIND") or "openai").strip().lower()
        })
        
    prompt = f"""你是一个智能运维与质量分析助手。我这里有多个层面的自动任务及服务检测到的异常信息。请帮我合并分析它们，并总结成适合提交到 GitHub Issue 的格式。
    
    异常汇总如下：
    \"\"\"
    {combined_errors}
    \"\"\"
    
    请严格只输出一个符合如下格式的 JSON，不要输出任何 Markdown 代码块标签，不要有任何额外的解释说明：
    {{
      "title": "[自动检测] (用一句话总结主要发生了什么严重的层面的异常，含核心报错词)",
      "body": "#### 发生时间\\n- 本地定时巡检\\n\\n#### 异常大图概览\\n(对这几个异常现象做一个2句话内的关联汇总分析)\\n\\n#### 详细探测数据\\n(在这里列出具体前端、后端或自动任务的出错堆栈或离线描述，每个错误限制在 12 行以内)\\n\\n#### 建议排查方向\\n(提供 2-3 条针对这些故障可能原因的具体排查动作，比如检查 server.py 进程、检查代理网络等)"
    }}
    """
    
    for spec in chain:
        try:
            res_text = _call_llm_once(spec, prompt)
            # 清理 Markdown 包裹
            cleaned = re.sub(r"^```[\w]*\n?", "", res_text.strip())
            cleaned = re.sub(r"\n?```$", "", cleaned.strip()).strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(cleaned[start:end])
        except Exception as e:
            print(f"LLM 提炼出错 ({spec.get('model')}): {e}")
            continue
            
    # 兜底纯文本
    return {
        "title": "[自动检测] 发现项目有功能服务或自动任务异常",
        "body": f"#### 异常汇总现场\n{combined_errors[:1200]}"
    }

def find_latest_scheduler_log() -> Path:
    log_dir = Path(__file__).resolve().parents[1] / "xinfo" / "log" / "runtime"
    print(f"DEBUG: 正在扫描日志目录: {log_dir} (目录存在: {log_dir.exists()})")
    logs = list(log_dir.glob("scheduler_*.log"))
    if not logs:
        raise FileNotFoundError(f"未找到任何 scheduler_*.log 日志文件")
    logs.sort(key=lambda x: x.stat().st_mtime)
    return logs[-1]

def extract_errors(log_path: Path) -> str:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    
    lines = content.splitlines()
    error_idx = []
    for idx, line in enumerate(lines):
        if '"ok": false' in line or "Exception" in line or "fetch failed" in line or "生成失败" in line:
            error_idx.append(idx)
            
    if not error_idx:
        return ""
        
    first_err = error_idx[0]
    start = max(0, first_err - 5)
    end = min(len(lines), first_err + 25)
    return "\n".join(lines[start:end])

def main():
    errors_found = []
    
    # 1. 扫描自动任务日志
    try:
        log_path = find_latest_scheduler_log()
        print(f"正在分析最新任务日志: {log_path.name}")
        error_context = extract_errors(log_path)
        if error_context:
            errors_found.append(f"### [自动任务执行异常]\n日志源: {log_path.name}\n\n```\n{error_context}\n```")
    except Exception as e:
        print(f"扫描任务日志出错: {e}")

    # 2. 检测后端 API 服务
    print("正在检查后端 API 服务 (端口 8900) 的健康状态...")
    api_ok, api_msg = check_api_server_health(8900)
    if not api_ok:
        errors_found.append(f"### [后端 API 服务离线/异常]\n描述: {api_msg}")

    # 3. 检测前端 UI 服务
    print("正在检查前端 UI 服务 (端口 5900) 的连通状态...")
    fe_ok, fe_msg = check_frontend_server_health(5900)
    if not fe_ok:
        errors_found.append(f"### [前端 UI 服务离线/异常]\n描述: {fe_msg}")

    if not errors_found:
        print("🎉 经全栈体检，今天的所有自动任务、后端服务及前端容器运行正常，未发现任何功能异常！")
        return 0
        
    print(f"检测到 {len(errors_found)} 处异常，正在调用 LLM 进行提炼并生成 GitHub Issue...")
    combined_errors = "\n\n---\n\n".join(errors_found)
    issue_data = summarize_errors_with_llm(combined_errors)
    
    print(f"提炼结果：\n[标题]: {issue_data['title']}\n[内容]: {issue_data['body'][:150]}...")
    
    print("正在通过本地 gh 命令行工具提报 Issue...")
    cmd = [
        "gh", "issue", "create",
        "--title", issue_data["title"],
        "--body", issue_data["body"]
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[1]))
    if res.returncode == 0:
        print("🎉 GitHub Issue 提报成功！链接如下：")
        print(res.stdout.strip())
        return 0
    else:
        print("❌ gh 命令提报失败：", res.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
