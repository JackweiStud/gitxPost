#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manage_accounts.py — X 雷达账号管理工具

用法：
  python3 manage_accounts.py list                          # 列出所有活跃账号
  python3 manage_accounts.py add <username> "<注释>"       # 添加账号
  python3 manage_accounts.py remove <username>             # 注释掉账号（保留历史）
  python3 manage_accounts.py restore <username>            # 恢复已注释的账号

示例：
  python3 manage_accounts.py add QuiverAI "AI数据分析，多方推荐"
  python3 manage_accounts.py remove elvissun
  python3 manage_accounts.py list
"""

import sys
import os
import re
import shutil
from datetime import datetime

SCAN_FILE = os.path.join(os.path.dirname(__file__), 'x_ideas_scan.py')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'log', 'account_backups')


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def make_backup():
    """修改前备份 x_ideas_scan.py，保留最近 10 份。"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(BACKUP_DIR, f'x_ideas_scan_{ts}.py')
    shutil.copy2(SCAN_FILE, dst)
    # 清理多余备份（只保留最新 10 份）
    backups = sorted(os.listdir(BACKUP_DIR))
    for old in backups[:-10]:
        os.remove(os.path.join(BACKUP_DIR, old))
    return dst


def read_file():
    with open(SCAN_FILE, encoding='utf-8') as f:
        return f.read()


def write_file(content: str):
    with open(SCAN_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


def find_target_block(content: str):
    """返回 TARGET_ACCOUNTS = [ ... ] 的起止行号（0-indexed），及列表行。"""
    lines = content.splitlines(keepends=True)
    start, end = None, None
    for i, line in enumerate(lines):
        if 'TARGET_ACCOUNTS = [' in line:
            start = i
        if start is not None and line.strip() == ']' and i > start:
            end = i
            break
    if start is None or end is None:
        raise ValueError('找不到 TARGET_ACCOUNTS 列表块')
    return start, end, lines


def get_active_accounts(lines, start, end):
    """提取活跃（未注释）账号名。"""
    active = []
    for line in lines[start+1:end]:
        stripped = line.strip()
        if stripped.startswith('"') and not stripped.startswith('#'):
            m = re.match(r'"(\w+)"', stripped)
            if m:
                active.append(m.group(1))
    return active


def get_commented_accounts(lines, start, end):
    """提取已注释账号名。"""
    commented = []
    for line in lines[start+1:end]:
        stripped = line.strip()
        if stripped.startswith('#"') or stripped.startswith('#"'):
            m = re.match(r'#"(\w+)"', stripped)
            if m:
                commented.append(m.group(1))
        elif re.match(r'#\s*"(\w+)"', stripped):
            m = re.match(r'#\s*"(\w+)"', stripped)
            if m:
                commented.append(m.group(1))
    return commented


# ── 子命令 ─────────────────────────────────────────────────────────────────

def cmd_list():
    content = read_file()
    lines = content.splitlines(keepends=True)
    start, end, lines = find_target_block(content)
    active = get_active_accounts(lines, start, end)
    commented = get_commented_accounts(lines, start, end)

    print(f'\n✅ 活跃账号 ({len(active)} 个):')
    for i, acc in enumerate(active, 1):
        print(f'  {i:2d}. @{acc}')

    if commented:
        print(f'\n💤 已注释/移除账号 ({len(commented)} 个):')
        for acc in commented:
            print(f'      @{acc}')
    print()


def cmd_add(username: str, note: str = ''):
    username = username.lstrip('@')
    content = read_file()
    start, end, lines = find_target_block(content)
    active = get_active_accounts(lines, start, end)

    if username.lower() in [a.lower() for a in active]:
        print(f'⚠️  @{username} 已在活跃列表中，无需添加。')
        return

    # 恢复已注释的账号
    commented = get_commented_accounts(lines, start, end)
    if username.lower() in [c.lower() for c in commented]:
        print(f'ℹ️  @{username} 已在注释中，请用 restore 命令恢复。')
        return

    backup = make_backup()

    # 在 ] 前面插入新账号（插入到"其他技术"区域末尾，或紧贴 ] 之前）
    note_str = f'  # {note}' if note else ''
    new_line = f'    "{username}",{note_str}\n'

    lines.insert(end, new_line)
    write_file(''.join(lines))
    print(f'✅ 已添加 @{username}{" — " + note if note else ""}')
    print(f'   备份: {backup}')


def cmd_remove(username: str):
    username = username.lstrip('@')
    content = read_file()
    start, end, lines = find_target_block(content)
    active = get_active_accounts(lines, start, end)

    if username.lower() not in [a.lower() for a in active]:
        print(f'⚠️  @{username} 不在活跃列表中。')
        # 提示是否已注释
        commented = get_commented_accounts(lines, start, end)
        if username.lower() in [c.lower() for c in commented]:
            print(f'   该账号已经处于注释状态。')
        return

    backup = make_backup()

    new_lines = []
    removed = False
    for i, line in enumerate(lines):
        if i >= start + 1 and i < end:
            stripped = line.strip()
            if stripped.startswith('"') and not stripped.startswith('#'):
                m = re.match(r'"(\w+)"', stripped)
                if m and m.group(1).lower() == username.lower():
                    # 注释掉这行，加上移除原因和日期
                    indent = len(line) - len(line.lstrip())
                    rest = line.strip()
                    # 保留已有注释，追加移除日期
                    if '#' in rest:
                        rest = rest[:rest.index('#')].strip() + rest[rest.index('#'):]
                        new_line = ' ' * indent + '#' + rest + f'  ← 移除 {datetime.now().strftime("%Y-%m-%d")}\n'
                    else:
                        new_line = ' ' * indent + '#' + rest + f'  # 移除 {datetime.now().strftime("%Y-%m-%d")}\n'
                    new_lines.append(new_line)
                    removed = True
                    continue
        new_lines.append(line)

    if removed:
        write_file(''.join(new_lines))
        print(f'✅ 已注释 @{username}（历史记录保留）')
        print(f'   备份: {backup}')
    else:
        print(f'❌ 未找到 @{username} 的精确匹配行')


def cmd_restore(username: str):
    username = username.lstrip('@')
    content = read_file()
    start, end, lines = find_target_block(content)
    commented = get_commented_accounts(lines, start, end)

    if username.lower() not in [c.lower() for c in commented]:
        print(f'⚠️  @{username} 不在已注释列表中，无法恢复。')
        return

    backup = make_backup()

    new_lines = []
    restored = False
    for i, line in enumerate(lines):
        if i >= start + 1 and i < end:
            stripped = line.strip()
            m = re.match(r'#\s*"(\w+)"', stripped)
            if m and m.group(1).lower() == username.lower():
                # 去掉注释符，清除"移除"注记
                indent = len(line) - len(line.lstrip())
                restored_line = ' ' * indent + stripped[1:].strip()
                # 移除 ← 移除 xxxx-xx-xx 标记
                restored_line = re.sub(r'\s*←\s*移除\s*\d{4}-\d{2}-\d{2}', '', restored_line)
                # 移除 # 移除 xxxx-xx-xx 标记
                restored_line = re.sub(r'\s*#\s*移除\s*\d{4}-\d{2}-\d{2}', '', restored_line)
                new_lines.append(restored_line.rstrip() + '\n')
                restored = True
                continue
        new_lines.append(line)

    if restored:
        write_file(''.join(new_lines))
        print(f'✅ 已恢复 @{username}')
        print(f'   备份: {backup}')
    else:
        print(f'❌ 恢复失败，请手动检查 x_ideas_scan.py')


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0].lower()

    if cmd == 'list':
        cmd_list()
    elif cmd == 'add':
        if len(args) < 2:
            print('用法: python3 manage_accounts.py add <username> "<注释>"')
            return
        username = args[1]
        note = args[2] if len(args) > 2 else ''
        cmd_add(username, note)
    elif cmd == 'remove':
        if len(args) < 2:
            print('用法: python3 manage_accounts.py remove <username>')
            return
        cmd_remove(args[1])
    elif cmd == 'restore':
        if len(args) < 2:
            print('用法: python3 manage_accounts.py restore <username>')
            return
        cmd_restore(args[1])
    else:
        print(f'未知命令: {cmd}')
        print('可用命令: list / add / remove / restore')


if __name__ == '__main__':
    main()
