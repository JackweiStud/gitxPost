#!/bin/bash
# gitxPost 每日自动任务
set -e
cd /Users/jackwl/Code/gitcode/gitxPost
source .venv/bin/activate

LOG_DIR="xinfo/log/runtime"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/scheduler_$(date +%Y-%m-%d).log"

echo "========== $(date) ==========" >> "$LOG"

echo "[1/3] radar-scan..." >> "$LOG"
python xpost.py radar-scan >> "$LOG" 2>&1 || true

echo "[2/3] radar-daily..." >> "$LOG"
python xpost.py radar-daily >> "$LOG" 2>&1 || true

echo "[3/3] follower-stats..." >> "$LOG"
python xpost.py follower-stats >> "$LOG" 2>&1 || true

echo "========== DONE $(date) ==========" >> "$LOG"
