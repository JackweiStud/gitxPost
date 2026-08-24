#!/bin/bash
# gitxPost 每日自动任务
# 参数: auto(默认) | scan | full
# auto: 先扫描；当天全部成功或当天最后一班再生成日报
# 最后一班按任务开始时刻判断，避免扫描耗时把窗口吃掉
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
START_TS="$(date '+%Y-%m-%d %H:%M:%S')"
START_DAY="$(date '+%Y-%m-%d')"
LOG="$LOG_DIR/scheduler_${START_DAY}.log"

MODE="${1:-auto}"
run_full=0
decide_reason=""

echo "========== $START_TS mode=$MODE ==========" >> "$LOG"

echo "[scan] radar-scan --source auto --limit 100..." >> "$LOG"
python xpost.py radar-scan --source auto --limit 100 >> "$LOG" 2>&1 || true

parse_should_full() {
  python -c '
import json, sys
data = json.loads(sys.stdin.read())
if "full" not in data:
    sys.exit(1)
print(int(bool(data.get("full"))))
print((data.get("reason") or "").replace("\n", " "))
'
}

fallback_last_slot() {
  python -c '
from datetime import datetime
import sys
import xpost
now = datetime.strptime(sys.argv[1], "%Y-%m-%d %H:%M:%S")
times = xpost._load_installed_scheduler_times()
print(int(xpost._is_last_scheduler_slot(now, times)))
' "$1"
}

case "$MODE" in
  full) run_full=1; decide_reason="forced_full" ;;
  scan) run_full=0; decide_reason="forced_scan" ;;
  *)
    DECISION="$(python xpost.py scheduler should-full --now "$START_TS" 2>>"$LOG")" || DECISION=""
    PARSED=""
    if [ -n "$DECISION" ]; then
      echo "[decide] $DECISION" >> "$LOG"
      PARSED="$(printf '%s' "$DECISION" | parse_should_full 2>>"$LOG")" || PARSED=""
    fi
    if [ -n "$PARSED" ]; then
      run_full="$(printf '%s' "$PARSED" | sed -n '1p')"
      decide_reason="$(printf '%s' "$PARSED" | sed -n '2p')"
    else
      echo "[decide] should-full 失败，回退 last-slot now=$START_TS" >> "$LOG"
      FALLBACK="$(fallback_last_slot "$START_TS" 2>>"$LOG")" || FALLBACK=""
      if [ "$FALLBACK" = "1" ]; then
        run_full=1
        decide_reason="fallback_last_slot"
      else
        run_full=0
        decide_reason="fallback_scan"
      fi
    fi
    ;;
esac

echo "[mode] full=$run_full reason=$decide_reason start=$START_TS" >> "$LOG"

if [ "$run_full" -eq 1 ]; then
  echo "[daily] radar-daily..." >> "$LOG"
  python xpost.py radar-daily >> "$LOG" 2>&1 || true

  echo "[opportunities] daily-opportunities..." >> "$LOG"
  if [ -n "$NODE_BIN" ] && [ -x "$NODE_BIN" ]; then
    "$NODE_BIN" scripts/daily_opportunities.js --json >> "$LOG" 2>&1 || true
  else
    echo "node not found; skip daily-opportunities" >> "$LOG"
  fi

  echo "[followers] follower-stats..." >> "$LOG"
  python xpost.py follower-stats >> "$LOG" 2>&1 || true

  echo "[audit] audit-run-status..." >> "$LOG"
  python scripts/audit_daily_run.py >> "$LOG" 2>&1 || true
else
  echo "[skip] 本日不生成日报 reason=$decide_reason" >> "$LOG"
fi

echo "========== DONE $(date '+%Y-%m-%d %H:%M:%S') ==========" >> "$LOG"
