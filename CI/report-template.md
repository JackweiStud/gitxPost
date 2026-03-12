# gitxPost 测试报告模板

日期：
提交：
测试人：
影响模块：

## 1. 本次改动

- 改动文件：
- 目标：
- 风险点：

## 2. 执行用例

| 用例 | 状态 | 备注 |
|------|------|------|
| TC-01 Article 草稿 |  |  |
| TC-02 Article 真发布 |  |  |
| TC-03 Article 图片上传 |  |  |
| TC-04 Grok JSON 输出 |  |  |
| TC-05 Chrome 升级风险回归 |  |  |
| TC-06 Post 纯文本 |  |  |
| TC-07 Post 图文 |  |  |

## 3. 实际结果

### 通过

- 

### 失败

- 

### 未执行

- 

## 4. 结论

- 是否可交付：
- 是否需要补测：
- 遗留风险：

## 5. 真实报告样例（2026-03-12 最小回归）

日期：2026-03-12  
提交：`d7fb3af`  
测试人：Codex  
影响模块：`Article` / `Grok` / `Post`

### 5.1 本次改动

- 改动文件：
  - `browser_cdp_session.py`
  - `auto_publish_uc.py`
  - `grok_hot_posts.py`
  - `auto_publish_post.py`
- 目标：
  - 验证共享 CDP 会话层迁移后，最小回归集仍然稳定可用
- 风险点：
  - 共享浏览器会话层是否误伤旧功能
  - Grok 是否还能返回有效 JSON
  - Article 图片与封面上传是否稳定

### 5.2 执行用例

| 用例 | 状态 | 备注 |
|------|------|------|
| TC-01 Article 草稿 | 通过 | 标题、正文、封面图均成功进入编辑器 |
| TC-02 Article 真发布 | 未执行 | 不属于本轮最小回归 |
| TC-03 Article 图片上传 | 通过 | 内容图 1 张、封面图 1 张均成功 |
| TC-04 Grok JSON 输出 | 通过 | 成功返回 7 条 OpenClaw 相关 JSON 结果 |
| TC-05 Chrome 升级风险回归 | 未执行 | 本轮未单独做 Chrome 升级场景 |
| TC-06 Post 纯文本 | 通过 | 文本输入成功，草稿完成 |
| TC-07 Post 图文 | 未执行 | 不属于本轮最小回归 |

### 5.3 实际结果

#### 通过

- `TC-01`：`content/examples/articleNew.md` 草稿链路通过，返回 `ok=true`
- `TC-03`：`content/examples/agent_skill_guide.md` 图片链路通过，内容图上传成功，封面图上传成功
- `TC-04`：Grok 成功输出 JSON，主题为最近一周 OpenClaw skill / agent / GitHub 相关内容，共 7 条
- `TC-06`：Post 纯文本草稿链路通过，返回 `ok=true`

#### 失败

- 无

#### 未执行

- `TC-02`、`TC-05`、`TC-07`

### 5.4 结论

- 是否可交付：是，最小回归集通过
- 是否需要补测：若要发版，建议补跑 `TC-02 Article 真发布` 与 `TC-07 Post 图文`
- 遗留风险：Grok 结果仍受 X / Grok 外部响应质量影响，属于外部依赖风险

## 6. 真实报告样例（2026-03-12 开源整理后 smoke）

日期：2026-03-12  
提交：工作区整理中（提交前 smoke）  
测试人：Codex  
影响模块：`content` / `article_tooling` / `Article` / `Post` / `Grok` / `README` / `CI`

### 6.1 本次改动

- 改动文件：
  - `README.md`
  - `CHANGELOG.md`
  - `CI/report-template.md`
  - `xpost.py`
  - `auto_publish_uc.py`
  - `article_tooling/scripts/parse_markdown.py`
  - `content/`
- 目标：
  - 验证目录整理、历史资料清理后，主功能仍可用
  - 验证 `content/` 与 `article_tooling/` 新路径不影响 CLI 和真实链路
- 风险点：
  - 路径重构可能导致 CLI、Markdown 解析、发布链路失效
  - `Post` 和 `Grok` 可能被这轮整理误伤

### 6.2 执行用例

| 用例 | 状态 | 备注 |
|------|------|------|
| TC-01 Article 草稿 | 通过 | `content/examples/articleNew.md` 草稿链路通过 |
| TC-02 Article 真发布 | 未执行 | 本轮 smoke 不做真实长文外发 |
| TC-03 Article 图片上传 | 通过 | 内容图和封面图均成功 |
| TC-04 Grok JSON 输出 | 通过 | 成功返回 7 条 OpenClaw skills / GitHub 相关 JSON |
| TC-05 Chrome 升级风险回归 | 未执行 | 本轮未做 Chrome 升级场景 |
| TC-06 Post 纯文本 | 通过 | 草稿链路通过 |
| TC-07 Post 图文 | 通过 | 首次遇到临时网络错误，重试后通过 |

### 6.3 实际结果

#### 通过

- `TC-01`：`Article` 草稿链路通过，标题、正文、封面图成功进入编辑器，返回 `ok=true`
- `TC-03`：`Article` 内容图与封面图链路通过，返回 `ok=true`
- `TC-04`：`Grok` 成功返回 7 条结构化 JSON，主题为最近一周 OpenClaw skills / GitHub 相关内容
- `TC-06`：`Post` 纯文本草稿链路通过，返回 `ok=true`
- `TC-07`：`Post` 图文草稿链路通过，文本输入成功，1 张图片上传成功，返回 `ok=true`
- 补充检查：`xpost doctor`、`xpost --help`、`xpost init`、`xpost validate`、`xpost parse` 全部通过

#### 失败

- 无

#### 未执行

- `TC-02`、`TC-05`

### 6.4 额外发现与修复

- 发现 `xpost init --style ...` 生成的 Markdown 会带 HTML 注释式 prompt 元数据
- 旧解析逻辑会把这段注释误识别为标题或正文的一部分
- 已在 `article_tooling/scripts/parse_markdown.py` 修复：先剥掉 frontmatter 和 HTML 注释，再提取标题和正文
- 修复后实际验证：`init -> validate -> parse` 流程恢复正常

### 6.5 结论

- 是否可交付：是，目录整理后主功能 smoke 通过
- 是否需要补测：若准备发版，建议补跑 `TC-02 Article 真发布`
- 遗留风险：`Post` 图文链路对 X 页面网络状态仍有外部依赖，个别场景可能需要重试
