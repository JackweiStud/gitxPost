#!/usr/bin/env python3
"""
发布队列处理器
定期检查 publish_queue.json，执行到期的定时任务
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import subprocess

BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_FILE = BASE_DIR / "xinfo" / "log" / "publish_queue.json"
XPOST_PY = BASE_DIR / "xpost.py"
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python"


def load_queue():
    """加载队列"""
    if not QUEUE_FILE.exists():
        return {"queue": []}
    try:
        return json.loads(QUEUE_FILE.read_text("utf-8"))
    except Exception:
        return {"queue": []}


def save_queue(data):
    """保存队列"""
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def process_queue():
    """处理队列中的到期任务"""
    data = load_queue()
    queue = data.get("queue", [])
    
    if not queue:
        print("队列为空")
        return
    
    now = datetime.now(timezone.utc)
    processed_count = 0
    
    for task in queue:
        if task.get("status") != "scheduled":
            continue
        
        # 检查是否到期
        scheduled_at = task.get("scheduled_at")
        if not scheduled_at:
            continue
        
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_at.replace('Z', '+00:00'))
            if scheduled_dt.tzinfo is None:
                scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
        except Exception as e:
            print(f"⚠️  任务 {task['id']} 时间格式错误: {e}")
            task["status"] = "failed"
            task["error"] = f"时间格式错误: {str(e)}"
            continue
        
        # 如果还没到时间，跳过
        if scheduled_dt > now:
            continue
        
        # 获取任务内容
        content = task.get("content", {})
        text = content.get("text", "")
        attachments = content.get("attachments", [])
        images = content.get("images", [])
        publish = content.get("publish", True)
        
        if not text:
            print(f"⚠️  任务 {task['id']} 缺少文本内容")
            task["status"] = "failed"
            task["error"] = "缺少文本内容"
            save_queue(data)
            continue
        
        # 执行任务
        print(f"📤 执行任务 {task['id']}: {text[:50]}...")
        task["status"] = "publishing"
        save_queue(data)
        
        try:
            # 构建命令
            cmd = [str(VENV_PYTHON), str(XPOST_PY), "post", text]
            
            media = [
                item.get("path")
                for item in attachments
                if isinstance(item, dict) and item.get("path")
            ]
            if media:
                cmd.extend(["--media"] + media)
            elif images:
                cmd.extend(["--images"] + images)
            
            if publish:
                cmd.append("--publish")
            
            cmd.extend(["--no-wait", "--observe-ms", "900"])
            
            # 执行
            result = subprocess.run(
                cmd,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result.returncode == 0:
                task["status"] = "done"
                task["completed_at"] = datetime.now(timezone.utc).isoformat()
                print(f"✅ 任务 {task['id']} 完成")
            else:
                task["status"] = "failed"
                task["error"] = result.stderr or "执行失败"
                print(f"❌ 任务 {task['id']} 失败: {task['error']}")
            
            processed_count += 1
            
        except subprocess.TimeoutExpired:
            task["status"] = "failed"
            task["error"] = "执行超时"
            print(f"❌ 任务 {task['id']} 超时")
        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            print(f"❌ 任务 {task['id']} 异常: {e}")
        
        # 保存更新
        save_queue(data)
    
    if processed_count > 0:
        print(f"\n✅ 处理了 {processed_count} 个任务")
    else:
        print("没有到期的任务")


if __name__ == "__main__":
    try:
        process_queue()
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
