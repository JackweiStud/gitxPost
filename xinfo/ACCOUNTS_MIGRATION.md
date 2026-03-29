# TARGET_ACCOUNTS 迁移文档

## 迁移概述

将 `TARGET_ACCOUNTS` 从 `x_ideas_scan.py` 中的 Python 列表迁移到独立的 `accounts.json` 配置文件。

## 迁移日期

2026-03-29

## 变更内容

### 新增文件

1. **xinfo/accounts.json** - 账号配置文件
   - 格式：JSON
   - 包含：账号 handle、备注、状态（active/removed）、添加/移除日期

2. **xinfo/migrate_accounts.py** - 一次性迁移脚本
   - 从旧的 Python 列表提取数据
   - 生成 JSON 配置文件

### 修改文件

1. **xinfo/x_ideas_scan.py**
   - 删除：硬编码的 TARGET_ACCOUNTS 列表（约 300 行）
   - 新增：`load_target_accounts()` 函数从 JSON 读取
   - 新增：`ACCOUNTS_CONFIG_FILE` 常量

2. **xinfo/manage_accounts.py**
   - 完全重写：从操作 Python 文件改为操作 JSON 文件
   - 简化：不再需要正则解析 Python 代码
   - 增强：更安全的备份和恢复机制

3. **xinfo/analyze_network.py**
   - 修改：`load_target_accounts()` 函数从 JSON 读取
   - 新增：`ACCOUNTS_FILE` 常量

4. **web/api/server.py**
   - 修改：`_read_accounts_from_file()` 函数从 JSON 读取
   - 新增：`ACCOUNTS_JSON` 常量
   - 简化：不再需要正则解析 Python 代码

## 数据统计

- 总账号数：261
- 活跃账号：242
- 已移除账号：19

## 优势

### 1. 关注点分离
- ✅ 配置与代码完全分离
- ✅ 不会因为修改配置而破坏 Python 语法

### 2. 易于维护
- ✅ JSON 格式标准化，易于解析
- ✅ 不需要复杂的正则表达式
- ✅ 支持更丰富的元数据

### 3. 更安全
- ✅ 自动备份机制（保留最近 10 份）
- ✅ 不会意外修改代码逻辑
- ✅ JSON 解析错误不会影响程序运行

### 4. 扩展性
- ✅ 可以轻松添加新字段（标签、分组、优先级等）
- ✅ 支持更复杂的账号管理逻辑

## 兼容性

### 前端（零改动）
- ✅ Web UI 账号管理页面
- ✅ 周报账号操作面板
- ✅ 所有 API 接口

### 后端 API（零改动）
- ✅ `GET /api/radar/accounts`
- ✅ `POST /api/radar/accounts`
- ✅ `DELETE /api/radar/accounts/{handle}`
- ✅ `PUT /api/radar/accounts/{handle}/restore`

### CLI 命令（零改动）
- ✅ `xpost.py radar-accounts list`
- ✅ `xpost.py radar-accounts add`
- ✅ `xpost.py radar-accounts remove`
- ✅ `xpost.py radar-accounts restore`

## 测试验证

### 1. 账号管理
```bash
# 列出账号
python3 xinfo/manage_accounts.py list

# 添加账号
python3 xinfo/manage_accounts.py add test_user "测试账号"

# 移除账号
python3 xinfo/manage_accounts.py remove test_user

# 恢复账号
python3 xinfo/manage_accounts.py restore test_user
```

### 2. 扫描功能
```bash
# 验证扫描脚本能正确加载账号
python3 -c "from xinfo.x_ideas_scan import TARGET_ACCOUNTS; print(len(TARGET_ACCOUNTS))"
```

### 3. 分析功能
```bash
# 验证分析脚本能正确加载账号
python3 -c "from xinfo.analyze_network import load_target_accounts; print(len(load_target_accounts()))"
```

### 4. Web API
- 访问 http://localhost:8900/api/radar/accounts
- 检查账号列表是否正常显示

## 回滚方案

如果需要回滚到旧版本：

1. 恢复备份的 `x_ideas_scan.py`（包含 TARGET_ACCOUNTS 列表）
2. 恢复旧版本的 `manage_accounts.py`
3. 恢复旧版本的 `analyze_network.py`
4. 恢复旧版本的 `web/api/server.py`

备份文件位置：
- `xinfo/log/account_backups/` - JSON 配置备份
- Git 历史记录 - 代码备份

## 注意事项

1. **首次运行**：确保 `accounts.json` 文件存在且格式正确
2. **权限**：确保 `accounts.json` 文件可读写
3. **备份**：每次修改都会自动备份，保留最近 10 份
4. **同步**：所有模块都从同一个 JSON 文件读取，数据一致性有保障

## 未来改进

可以考虑的增强功能：

1. **账号分组**：按类别（AI 研究、创业者、投资人等）分组
2. **优先级**：为账号设置优先级，影响扫描顺序
3. **标签系统**：为账号添加多个标签，便于筛选
4. **统计信息**：记录账号的扫描次数、推文数量等
5. **导入导出**：支持从 CSV/Excel 批量导入账号
