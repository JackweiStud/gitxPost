#!/bin/bash
# gitxPost 每日自动任务
set -e
cd /Users/jackwl/Code/gitcode/gitxPost
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
source .venv/bin/activate

NODE_BIN="${NODE_BIN:-/opt/homebrew/bin/node}"
if [ ! -x "$NODE_BIN" ]; then
  NODE_BIN="$(command -v node || true)"
fi

LOG_DIR="xinfo/log/runtime"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/scheduler_$(date +%Y-%m-%d).log"

echo "========== $(date) ==========" >> "$LOG"

echo "[1/4] radar-scan --source auto --limit 40..." >> "$LOG"
python xpost.py radar-scan --source auto --limit 40 >> "$LOG" 2>&1 || true

echo "[2/4] radar-daily..." >> "$LOG"
python xpost.py radar-daily >> "$LOG" 2>&1 || true

echo "[3/4] daily-opportunities..." >> "$LOG"
if [ -n "$NODE_BIN" ] && [ -x "$NODE_BIN" ]; then
  "$NODE_BIN" scripts/daily_opportunities.js --json >> "$LOG" 2>&1 || true
else
  echo "node not found; skip daily-opportunities" >> "$LOG"
fi

echo "[4/4] follower-stats..." >> "$LOG"
python xpost.py follower-stats >> "$LOG" 2>&1 || true

echo "[5/5] audit-run-status..." >> "$LOG"
python scripts/audit_daily_run.py >> "$LOG" 2>&1 || true

echo "========== DONE $(date) ==========" >> "$LOG"
