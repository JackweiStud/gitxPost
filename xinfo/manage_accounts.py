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
import json
import shutil
from datetime import datetime

ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), 'accounts.json')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'log', 'account_backups')


# ── 工具函数 ─────────────────────────────────────────────────────────────────

def make_backup():
    """修改前备份 accounts.json，保留最近 10 份。"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(BACKUP_DIR, f'accounts_{ts}.json')
    shutil.copy2(ACCOUNTS_FILE, dst)
    # 清理多余备份（只保留最新 10 份）
    backups = sorted(os.listdir(BACKUP_DIR))
    for old in backups[:-10]:
        os.remove(os.path.join(BACKUP_DIR, old))
    return dst


def read_accounts():
    """读取账号配置文件"""
    with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_accounts(data):
    """写入账号配置文件"""
    with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_active_accounts(data):
    """提取活跃账号"""
    return [acc for acc in data['accounts'] if acc['status'] == 'active']


def get_removed_accounts(data):
    """提取已移除账号"""
    return [acc for acc in data['accounts'] if acc['status'] == 'removed']


# ── 子命令 ─────────────────────────────────────────────────────────────────

def cmd_list():
    data = read_accounts()
    active = get_active_accounts(data)
    removed = get_removed_accounts(data)

    print(f'\n✅ 活跃账号 ({len(active)} 个):')
    for i, acc in enumerate(active, 1):
        note = acc.get('note', '')
        print(f'  {i:2d}. @{acc["handle"]:<20} {note}')

    if removed:
        print(f'\n💤 已注释/移除账号 ({len(removed)} 个):')
        for acc in removed:
            note = acc.get('note', '')
            removed_at = acc.get('removed_at', '')
            print(f'      @{acc["handle"]:<20} {note} (移除于 {removed_at})')
    print()


def cmd_add(username: str, note: str = ''):
    username = username.lstrip('@')
    data = read_accounts()
    
    # 检查是否已存在
    for acc in data['accounts']:
        if acc['handle'].lower() == username.lower():
            if acc['status'] == 'active':
                print(f'⚠️  @{username} 已在活跃列表中，无需添加。')
                return
            elif acc['status'] == 'removed':
                print(f'ℹ️  @{username} 已在注释中，请用 restore 命令恢复。')
                return
    
    backup = make_backup()
    
    # 添加新账号
    new_account = {
        "handle": username,
        "note": note,
        "status": "active",
        "added_at": datetime.now().strftime('%Y-%m-%d')
    }
    data['accounts'].append(new_account)
    data['updated_at'] = datetime.now().isoformat()
    
    write_accounts(data)
    print(f'✅ 已添加 @{username}{" — " + note if note else ""}')
    print(f'   备份: {backup}')


def cmd_remove(username: str):
    username = username.lstrip('@')
    data = read_accounts()
    
    found = False
    for acc in data['accounts']:
        if acc['handle'].lower() == username.lower():
            if acc['status'] == 'removed':
                print(f'⚠️  @{username} 已经处于注释状态。')
                return
            elif acc['status'] == 'active':
                backup = make_backup()
                
                # 标记为已移除
                acc['status'] = 'removed'
                acc['removed_at'] = datetime.now().strftime('%Y-%m-%d')
                data['updated_at'] = datetime.now().isoformat()
                
                write_accounts(data)
                print(f'✅ 已注释 @{username}（历史记录保留）')
                print(f'   备份: {backup}')
                found = True
                break
    
    if not found:
        print(f'⚠️  @{username} 不在活跃列表中。')


def cmd_restore(username: str):
    username = username.lstrip('@')
    data = read_accounts()
    
    found = False
    for acc in data['accounts']:
        if acc['handle'].lower() == username.lower():
            if acc['status'] == 'active':
                print(f'⚠️  @{username} 已经是活跃状态。')
                return
            elif acc['status'] == 'removed':
                backup = make_backup()
                
                # 恢复为活跃
                acc['status'] = 'active'
                if 'removed_at' in acc:
                    del acc['removed_at']
                data['updated_at'] = datetime.now().isoformat()
                
                write_accounts(data)
                print(f'✅ 已恢复 @{username}')
                print(f'   备份: {backup}')
                found = True
                break
    
    if not found:
        print(f'⚠️  @{username} 不在已注释列表中，无法恢复。')


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
