#!/bin/bash
# Daily Daf Yomi build. Invoked by launchd (com.jocosiol.dafyomi) at 06:00 local time.
# Feeds DAILY_PROMPT.md to Claude Code in headless mode; Claude does the whole pipeline.
#
#   Manual run:   ~/daf-yomi/run_daily.sh
#   Log:          ~/Library/Logs/daf-yomi/daily.log

set -uo pipefail

REPO="/Users/moshecosio/daf-yomi"
LOGDIR="$HOME/Library/Logs/daf-yomi"
LOG="$LOGDIR/daily.log"
LOCK="$LOGDIR/.lock"

# launchd hands us a bare environment — spell out everything we need.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="${HOME:-/Users/moshecosio}"
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"

mkdir -p "$LOGDIR"

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"; }

# ---- single-instance guard: never let two builds race on the same git repo ----
exec 9>"$LOCK"
if ! flock -n 9 2>/dev/null; then
  # macOS has no flock(1); fall back to a mkdir-based lock.
  if ! mkdir "$LOCK.d" 2>/dev/null; then
    log "SKIP  another run is already in progress"
    exit 0
  fi
  trap 'rmdir "$LOCK.d" 2>/dev/null' EXIT
fi

log "===== start ====="

# ---- keep the log from growing without bound ----
if [ -f "$LOG" ] && [ "$(wc -c <"$LOG")" -gt 2000000 ]; then
  mv "$LOG" "$LOG.1"
  log "rotated log"
fi

# ---- wait for the network (the Mac may have just woken up) ----
for i in $(seq 1 30); do
  if curl -sf -m 8 -o /dev/null https://www.sefaria.org/api/calendars; then
    [ "$i" -gt 1 ] && log "network ready after ${i} attempt(s)"
    break
  fi
  if [ "$i" -eq 30 ] ; then
    log "FAIL  no network after 30 attempts (~5 min) — giving up"
    log "===== end (network) ====="
    exit 1
  fi
  sleep 10
done

cd "$REPO" || { log "FAIL  cannot cd to $REPO"; exit 1; }

# ---- preflight: the things that silently break an unattended run ----
command -v python3 >/dev/null || { log "FAIL  python3 not on PATH"; exit 1; }
command -v git     >/dev/null || { log "FAIL  git not on PATH"; exit 1; }
command -v claude  >/dev/null || { log "FAIL  claude not on PATH"; exit 1; }
python3 -c 'import markdown' 2>/dev/null || { log "FAIL  python 'markdown' package missing"; exit 1; }
[ -f DAILY_PROMPT.md ] || { log "FAIL  DAILY_PROMPT.md not found in $REPO"; exit 1; }

log "python3=$(command -v python3)  git=$(command -v git)  claude=$(command -v claude)"

# ---- run the pipeline ----
{
  echo "----- claude output $(date '+%F %T') -----"
  claude -p "$(cat DAILY_PROMPT.md)" \
    --allowedTools Bash Read Write Edit Glob Grep \
    --permission-mode acceptEdits \
    2>&1
  echo "----- claude exit: $? -----"
} >>"$LOG" 2>&1

# ---- verify the outcome independently of what Claude reported ----
DAF_LIVE="$(curl -s -m 20 "https://jocosiol.github.io/daf-yomi/?cb=$$" \
            | sed -n 's/.*<title>\(.*\)<\/title>.*/\1/p')"
LOCAL_HEAD="$(git log --oneline -1 2>/dev/null)"
UNPUSHED="$(git log --oneline origin/main..HEAD 2>/dev/null | wc -l | tr -d ' ')"

log "local HEAD: $LOCAL_HEAD"
log "unpushed commits: $UNPUSHED"
log "live title: ${DAF_LIVE:-<none>}"

if [ "$UNPUSHED" != "0" ]; then
  log "WARN  $UNPUSHED commit(s) not pushed — check auth (gh auth status / keychain)"
fi

log "===== end ====="
