# CI 验收目录

这个目录用于统一管理 `gitxPost` 的功能验收、回归测试和测试报告模板。

目标：
- 让每次功能改动后都有一套固定的验收入口
- 避免测试用例散落在 `docs/`、根目录报告和临时说明里
- 为后续半自动 CI / 发布前人工验收提供统一基线

## 目录说明

- `test-cases.md`
  - 当前项目统一测试用例
  - 覆盖 `Article`、`Grok`、`Post`
- `report-template.md`
  - 每次改动后的测试报告模板
  - 可以直接复制一份填写

## 使用方式

### 日常改动后的最小回归

每次改动以下文件之一，至少跑一次最小回归集：

- `browser_cdp_session.py`
- `auto_publish_uc.py`
- `grok_hot_posts.py`
- `auto_publish_post.py`
- `xpost.py`

最小回归集：

1. `TC-01` Article 草稿
2. `TC-03` Article 图片上传
3. `TC-04` Grok JSON 输出
4. `TC-06` Post 纯文本

### 发版前完整回归

1. `TC-01` Article 草稿
2. `TC-02` Article 真发布
3. `TC-03` Article 图片上传
4. `TC-04` Grok JSON 输出
5. `TC-05` Chrome 升级风险回归
6. `TC-06` Post 纯文本
7. `TC-07` Post 图文

## 历史文档关系

本目录整合了以下历史文档中的有效内容：

- `docs/article-grok-cdp-migration-test-cases-2026-03-09.md`
- `../gitxPost-migration-test-report-2026-03-12.md`

后续请优先维护 `CI/` 下的文档，把这里作为统一入口。
