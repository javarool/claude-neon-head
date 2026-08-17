#!/usr/bin/env bash
# Single control point for neonhead from Claude Code hooks (see
# .claude/settings.example.json) and from the neonhead-react skill.
#
#   neonhead.sh start
#   neonhead.sh stop
#   neonhead.sh status
#   neonhead.sh emotion doubt 0.7
#   neonhead.sh gesture no
#   neonhead.sh title "neonhead: $PWD"
#   neonhead.sh say "thinking..."
#   neonhead.sh say "thinking..." 2.5    # pace the phrase to ~2.5s
#
# start/stop/status track the process via a pidfile (not pkill-by-name).
# emotion/gesture/title/say are fire-and-forget UDP datagrams straight to
# the app's own listener (net.py) - no python/venv needed for those. The
# port itself is guarded by net.py (refuses to start a second instance),
# not by this script.
set -uo pipefail

# Lives at .claude/skills/neonhead-react/neonhead.sh - repo root is three
# levels up.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PIDFILE="$DIR/.neonhead.pid"
LOGFILE="$DIR/.neonhead.log"
PORT=9955

is_running() {
    [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

json_escape() {
    local s="${1//\\/\\\\}"
    printf '%s' "${s//\"/\\\"}"
}

send() {
    # bash's /dev/udp pseudo-device - no nc/python needed for a fire-and-
    # forget datagram.
    printf '%s' "$1" > "/dev/udp/127.0.0.1/$PORT" 2>/dev/null || true
}

start() {
    if is_running; then
        echo "neonhead already running (pid $(cat "$PIDFILE"))"
        return 0
    fi
    rm -f "$PIDFILE"   # stale, from a crashed process
    # setsid fully daemonizes into a new session - without it, an async
    # hook invocation of this script can end up blocked in wait() on the
    # backgrounded child instead of returning. $! is captured inside the
    # same $(...) subshell that starts the job: a plain `cmd &` inside a
    # subshell does NOT set $! in the caller, only within that subshell.
    local pid
    pid="$(cd "$DIR" && { setsid nohup ./run.sh >>"$LOGFILE" 2>&1 </dev/null & } ; echo $!)"
    echo "$pid" >"$PIDFILE"
    echo "neonhead started (pid $pid, log: $LOGFILE)"
}

stop() {
    if ! is_running; then
        rm -f "$PIDFILE"
        echo "neonhead not running"
        return 0
    fi
    local pid
    pid="$(cat "$PIDFILE")"
    # Ask nicely first (net "quit" command -> app.py sets running=False,
    # which lets it close the window and release the ports on its own);
    # only signal it if it doesn't exit within ~2s.
    send '{"type":"quit"}'
    for _ in $(seq 1 20); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
    done
    kill -0 "$pid" 2>/dev/null && kill "$pid" 2>/dev/null
    rm -f "$PIDFILE"
    echo "neonhead stopped"
}

status() {
    if is_running; then
        echo "running (pid $(cat "$PIDFILE"))"
    else
        echo "stopped"
    fi
}

cue() {
    is_running || return 0
    # The process may be alive but not yet bound to its UDP socket (right
    # after start) - a cue sent before then is silently dropped, no error,
    # no retry. Give it up to ~5s to finish coming up.
    for _ in $(seq 1 50); do
        grep -q 'listening on' "$LOGFILE" 2>/dev/null && break
        sleep 0.1
    done
    local kind="$1" name="${2:-}"
    [[ -n "$name" ]] || return 0
    case "$kind" in
        emotion)
            send "{\"type\":\"emotion\",\"name\":\"$(json_escape "$name")\",\"weight\":${3:-1.0}}"
            ;;
        gesture)
            send "{\"type\":\"gesture\",\"name\":\"$(json_escape "$name")\"}"
            ;;
        title)
            # text may contain spaces - take everything from $2 on.
            send "{\"type\":\"title\",\"text\":\"$(json_escape "${*:2}")\"}"
            ;;
        say)
            # text may contain spaces, so the trailing arg is only treated
            # as a SECONDS duration when it's numeric and there's more than
            # one word left over for the text itself.
            local args=("${@:2}") secs=""
            if [[ ${#args[@]} -gt 1 && "${args[-1]}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
                secs="${args[-1]}"
                unset 'args[-1]'
            fi
            # Mouth-only viseme animation (text_to_timeline in app.py), no
            # audio; app.py always repeats it 3x with pauses so a reaction
            # actually registers.
            if [[ -n "$secs" ]]; then
                send "{\"type\":\"say\",\"text\":\"$(json_escape "${args[*]}")\",\"seconds\":$secs}"
            else
                send "{\"type\":\"say\",\"text\":\"$(json_escape "${args[*]}")\"}"
            fi
            ;;
    esac
}

cmd="${1:-}"
[[ $# -gt 0 ]] && shift
case "$cmd" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    emotion|gesture|title|say) cue "$cmd" "$@" ;;
    *) echo "usage: $0 start|stop|status|emotion NAME [WEIGHT]|gesture NAME|title TEXT|say TEXT [SECONDS]" >&2; exit 1 ;;
esac