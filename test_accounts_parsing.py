#!/usr/bin/env python3
"""测试账号解析功能"""

import re
from pathlib import Path

X_IDEAS_SCAN_PY = Path("xinfo/x_ideas_scan.py")

def _read_accounts_from_file() -> dict:
    """直接从 x_ideas_scan.py 文件读取账号列表（不依赖 xpost 子进程）"""
    active = []
    removed = []
    
    if not X_IDEAS_SCAN_PY.exists():
        return {"active": active, "removed": removed}
    
    try:
        content = X_IDEAS_SCAN_PY.read_text("utf-8")
        
        # 提取 TARGET_ACCOUNTS 列表内容
        # 匹配从 TARGET_ACCOUNTS = [ 到对应的 ]
        match = re.search(
            r'TARGET_ACCOUNTS\s*=\s*\[(.*?)\n\]',
            content,
            re.DOTALL
        )
        
        if not match:
            return {"active": active, "removed": removed}
        
        accounts_block = match.group(1)
        
        # 解析每一行
        for line in accounts_block.split('\n'):
            line = line.strip()
            
            # 跳过空行
            if not line:
                continue
            
            # 跳过纯注释行（不包含账号的注释）
            if line.startswith('#') and '"' not in line:
                continue
            
            # 匹配账号：可能是 "username", 或 #"username",# 注释
            # 活跃账号：以 " 开头
            if line.startswith('"'):
                match = re.match(r'"(\w+)"', line)
                if match:
                    active.append({"handle": match.group(1), "status": "active"})
            # 已移除账号：以 # 开头，后面跟 "username"
            elif line.startswith('#') and '"' in line:
                match = re.search(r'#\s*"(\w+)"', line)
                if match:
                    removed.append({"handle": match.group(1), "status": "removed"})
        
        return {"active": active, "removed": removed}
    
    except Exception as e:
        print(f"读取账号文件失败: {e}")
        return {"active": active, "removed": removed}


if __name__ == "__main__":
    result = _read_accounts_from_file()
    
    print(f"✅ 活跃账号: {len(result['active'])} 个")
    print(f"❌ 已移除账号: {len(result['removed'])} 个")
    
    print("\n前 5 个活跃账号:")
    for acc in result['active'][:5]:
        print(f"  - @{acc['handle']}")
    
    print("\n前 10 个已移除账号:")
    for acc in result['removed'][:10]:
        print(f"  - @{acc['handle']}")
    
    print("\n✓ 测试完成！")
