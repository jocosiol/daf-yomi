#!/bin/bash
# Daily Daf Yomi build. Feeds DAILY_PROMPT.md to Claude Code in headless mode;
# Claude does the whole pipeline.
#
# launchd (com.jocosiol.dafyomi) fires this every two hours from 06:00 to 22:00,
# and at login — not once at 06:00 — because the Mac is often switched off then
# and launchd does not run a missed job for a machine that was powered down.
# The first attempt that finds a running Mac does the work; the rest hit the
# "already done today" check below and exit in milliseconds.
#
#   Manual run:   ~/daf-yomi/run_daily.sh
#   Log:          ~/Library/Logs/daf-yomi/daily.log
#   Schedule:     com.jocosiol.dafyomi.plist (installed to ~/Library/LaunchAgents)

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
#
# mkdir is the atomic primitive (macOS has no flock(1)). The trap releases the
# lock on a normal exit or a catchable signal — but not on SIGKILL, a panic or
# a power cut. A lock left behind that way used to wedge the job permanently:
# every later run found the directory, logged SKIP and exited 0, so the agent
# looked healthy while building nothing. So the holder records its PID, and a
# lock whose holder is gone is stale and gets broken.
LOCKD="$LOCK.d"
acquire() { mkdir "$LOCKD" 2>/dev/null && echo $$ >"$LOCKD/pid"; }

if ! acquire; then
  holder="$(cat "$LOCKD/pid" 2>/dev/null || true)"
  if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then
    log "SKIP  build already running (pid $holder)"
    exit 0
  fi
  log "WARN  breaking stale lock from pid ${holder:-unknown} (no such process)"
  rm -rf "$LOCKD"
  if ! acquire; then
    log "FAIL  could not acquire $LOCKD after breaking a stale lock"
    exit 1
  fi
fi
trap 'rm -rf "$LOCKD"' EXIT INT TERM

log "===== start ====="

cd "$REPO" || { log "FAIL  cannot cd to $REPO"; exit 1; }

# ---- is there anything to do? ----
# The agent fires at several times of day, because this Mac is not reliably on
# at any single one of them. Checking here — before the network wait and before
# spending a model call — is what makes the extra triggers free: a run with
# nothing to do costs milliseconds.
#
# "Nothing to do" means the buffer is full AND there is nothing left to commit
# or push, so a run that wrote a sheet but died before publishing still gets
# finished by the next trigger. origin/main is a local ref updated by push, so
# this needs no network — which matters when the Mac wakes up offline.
if python3 build/buffer.py >/dev/null 2>&1; then
  unpushed="$(git log --oneline origin/main..HEAD 2>/dev/null | wc -l | tr -d ' ')"
  if [ "$unpushed" = "0" ] && [ -z "$(git status --porcelain)" ]; then
    log "SKIP  buffer full, nothing to publish"
    exit 0
  fi
  log "buffer full but the tree is dirty or unpushed — continuing"
else
  log "buffer short — $(python3 build/buffer.py --missing 2>/dev/null | tr '\n' ' ')"
fi

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

# ---- preflight: the things that silently break an unattended run ----
command -v python3 >/dev/null || { log "FAIL  python3 not on PATH"; exit 1; }
command -v git     >/dev/null || { log "FAIL  git not on PATH"; exit 1; }
command -v claude  >/dev/null || { log "FAIL  claude not on PATH"; exit 1; }
for mod in markdown jinja2 yaml; do
  python3 -c "import $mod" 2>/dev/null || {
    log "FAIL  python '$mod' package missing — pip3 install --user markdown jinja2 pyyaml"
    exit 1
  }
done
[ -f DAILY_PROMPT.md ] || { log "FAIL  DAILY_PROMPT.md not found in $REPO"; exit 1; }
[ -f build/build.py ]  || { log "FAIL  build/build.py not found in $REPO"; exit 1; }

# The sheets must be clean before we start; an unfinished edit left behind by a
# previous run would otherwise be committed as part of today's daf.
if ! python3 build/validate.py content >>"$LOG" 2>&1; then
  log "WARN  content/ was already failing validation before this run"
fi

log "python3=$(command -v python3)  git=$(command -v git)  claude=$(command -v claude)"

# ---- run the pipeline ----
# The exit code has to escape the redirect group, so capture it in a variable
# rather than echoing $? inside the braces where nothing can read it.
CLAUDE_RC=0
echo "----- claude output $(date '+%F %T') -----" >>"$LOG"
claude -p "$(cat DAILY_PROMPT.md)" \
  --allowedTools Bash Read Write Edit Glob Grep \
  --permission-mode acceptEdits \
  >>"$LOG" 2>&1 || CLAUDE_RC=$?
echo "----- claude exit: $CLAUDE_RC -----" >>"$LOG"

# ---- verify the outcome independently of what Claude reported ----
STATUS=0

# A dropped socket mid-run used to be logged and then ignored: the wrapper
# checked validation, today's sheet and unpushed commits, none of which notice
# a run that died halfway. It reported success while leaving a written but
# uncommitted sheet behind.
if [ "$CLAUDE_RC" != "0" ]; then
  log "FAIL  claude exited $CLAUDE_RC — this run did not finish cleanly"
  STATUS=1
fi

# The build gates on this too, but re-running it here means a bad sheet is
# reported by the wrapper even if Claude committed anyway.
if python3 build/validate.py content >>"$LOG" 2>&1; then
  log "validate: clean"
else
  log "FAIL  content/ does not validate — see the validate output above"
  STATUS=1
fi

# Today's sheet should exist and carry today's date. `date +%F` is the local
# civil date; sheets are built at least a day ahead, so a missing file for
# today is a real failure while a missing one for tomorrow is not.
TODAY="$(date +%F)"
if grep -lq "study_date: $TODAY" content/*.md 2>/dev/null; then
  SHEET="$(grep -l "study_date: $TODAY" content/*.md | head -1)"
  log "today's sheet: $SHEET"
  ES="${SHEET%.md}.es.md"
  [ -f "$ES" ] || log "WARN  no Spanish sheet for today ($ES)"
else
  log "FAIL  no sheet in content/ with study_date: $TODAY"
  STATUS=1
fi

# Work written but never committed is invisible to the unpushed-commits check
# below, because it never became a commit in the first place.
if [ -n "$(git status --porcelain)" ]; then
  log "FAIL  uncommitted changes left behind — next run will pick them up:"
  git status --short >>"$LOG"
  STATUS=1
fi

DAF_LIVE="$(curl -s -m 20 "https://jocosiol.github.io/daf-yomi/?cb=$$" \
            | sed -n 's/.*<title>\(.*\)<\/title>.*/\1/p')"
LOCAL_HEAD="$(git log --oneline -1 2>/dev/null)"
UNPUSHED="$(git log --oneline origin/main..HEAD 2>/dev/null | wc -l | tr -d ' ')"

log "local HEAD: $LOCAL_HEAD"
log "unpushed commits: $UNPUSHED"
log "live title: ${DAF_LIVE:-<none>}"

if [ "$UNPUSHED" != "0" ]; then
  log "WARN  $UNPUSHED commit(s) not pushed — check auth (gh auth status / keychain)"
  STATUS=1
fi

log "===== end (status $STATUS) ====="
exit "$STATUS"
