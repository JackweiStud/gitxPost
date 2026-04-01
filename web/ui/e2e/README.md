# Web UI E2E Regression

This folder holds repeatable browser regressions for the article workflow.

## Run

From `web/ui`:

```bash
npm run e2e:article
```

Or from the repo root:

```bash
python3 web/ui/e2e/article_workflow_regression.py
```

## What it covers

- Create a new article from the list page
- Edit content and wait for autosave
- Run one-click generation
- Publish the article
- Create a second article and verify the editor opens the new route instead of reusing the previously published one
