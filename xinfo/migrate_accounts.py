#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移脚本：从 x_ideas_scan.py 提取 TARGET_ACCOUNTS 并生成 accounts.json
"""

import json
import re
from datetime import datetime
from pathlib import Path

SCAN_FILE = Path(__file__).parent / "x_ideas_scan.py"
OUTPUT_FILE = Path(__file__).parent / "accounts.json"


def extract_accounts():
    """从 x_ideas_scan.py 提取账号数据"""
    content = SCAN_FILE.read_text("utf-8")
    
    # 提取 TARGET_ACCOUNTS 列表
    match = re.search(
        r'TARGET_ACCOUNTS\s*=\s*\[(.*?)\n\]',
        content,
        re.DOTALL
    )
    
    if not match:
        raise ValueError("找不到 TARGET_ACCOUNTS 定义")
    
    accounts_block = match.group(1)
    accounts = []
    
    for line in accounts_block.split('\n'):
        line = line.strip()
        
        # 跳过空行和纯注释行
        if not line or (line.startswith('#') and '"' not in line):
            continue
        
        # 活跃账号：以 " 开头
        if line.startswith('"'):
            match = re.match(r'"(\w+)",?\s*#?\s*(.*)', line)
            if match:
                handle = match.group(1)
                note = match.group(2).strip()
                accounts.append({
                    "handle": handle,
                    "note": note,
                    "status": "active",
                    "added_at": "2026-01-01"  # 默认日期
                })
        
        # 已移除账号：以 # 开头，后面跟 "username"
        elif line.startswith('#') and '"' in line:
            # 匹配 #"username",# 注释  ← 移除 2026-03-11
            match = re.search(r'#\s*"(\w+)",?\s*#?\s*(.*?)(?:←\s*移除\s*(\d{4}-\d{2}-\d{2}))?$', line)
            if match:
                handle = match.group(1)
                note = match.group(2).strip()
                removed_date = match.group(3) or "2026-03-01"  # 默认移除日期
                accounts.append({
                    "handle": handle,
                    "note": note,
                    "status": "removed",
                    "added_at": "2026-01-01",
                    "removed_at": removed_date
                })
    
    return accounts


def main():
    print("开始迁移 TARGET_ACCOUNTS...")
    print(f"源文件: {SCAN_FILE}")
    print(f"目标文件: {OUTPUT_FILE}")
    
    accounts = extract_accounts()
    
    # 生成 JSON 数据
    data = {
        "version": "1.0",
        "updated_at": datetime.now().isoformat(),
        "accounts": accounts
    }
    
    # 写入文件
    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    active_count = sum(1 for a in accounts if a["status"] == "active")
    removed_count = sum(1 for a in accounts if a["status"] == "removed")
    
    print(f"\n✅ 迁移完成！")
    print(f"   总账号数: {len(accounts)}")
    print(f"   活跃账号: {active_count}")
    print(f"   已移除账号: {removed_count}")
    print(f"\n生成文件: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
