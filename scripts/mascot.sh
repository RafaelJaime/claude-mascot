#!/bin/sh
# claude-mascot — give each Claude Code profile its own startup mascot.
#
#   mascot.sh install <costume> [alias] [config-dir]   wire up a costumed command
#   mascot.sh remove <alias>                           drop one
#   mascot.sh refresh                                  re-apply for the current build
#   mascot.sh hook                                     refresh in the background
#   mascot.sh status                                   what is wired up right now
#   mascot.sh list                                     available costumes
#   mascot.sh uninstall                                remove everything
#
# State (the launcher, its scripts, cached patched binaries and the costume
# registry) lives in ~/.claude-mascot so shell aliases have a stable path,
# independent of where this plugin happens to be installed.

set -eu

scripts="$(cd "$(dirname "$0")" && pwd)"
state="${CLAUDE_MASCOT_HOME:-$HOME/.claude-mascot}"
config="$state/config"
rc="${CLAUDE_MASCOT_RC:-$HOME/.zshrc}"
open_marker="# >>> claude-mascot >>>"
close_marker="# <<< claude-mascot <<<"

sync_scripts() {
    mkdir -p "$state/bin"
    # Skipped when invoked through the copy that already lives in the state dir.
    if [ "$scripts" != "$state" ]; then
        cp "$scripts/patch.py" "$scripts/run.sh" "$scripts/mascot.sh" "$state/"
        chmod +x "$state/patch.py" "$state/run.sh" "$state/mascot.sh"
    fi
    [ -f "$config" ] || : >"$config"
}

# Rewrite the managed block in the shell rc from the costume registry.
write_aliases() {
    tmp="$(mktemp)"
    if [ -f "$rc" ]; then
        # `open` and `close` are awk built-ins, hence the blander names.
        awk -v head="$open_marker" -v foot="$close_marker" '
            $0 == head { skip = 1 }
            skip != 1 { print }
            $0 == foot { skip = 0 }
        ' "$rc" >"$tmp"
    fi

    if [ -s "$config" ]; then
        printf '%s\n' "$open_marker" >>"$tmp"
        while IFS='	' read -r name costume env; do
            [ -n "$name" ] || continue
            printf "alias %s='%s\$HOME/.claude-mascot/run.sh %s'\n" \
                "$name" "${env:+CLAUDE_CONFIG_DIR=$env }" "$costume" >>"$tmp"
        done <"$config"
        printf '%s\n' "$close_marker" >>"$tmp"
    fi

    # Written in place, so the rc keeps its own permissions.
    cat "$tmp" >"$rc"
    rm -f "$tmp"
}

register() {
    name="$1"
    costume="$2"
    env="${3:-}"
    case "$env" in "~/"*) env="$HOME/${env#\~/}" ;; esac
    tmp="$(mktemp)"
    [ -f "$config" ] && grep -v "^$name	" "$config" >"$tmp" || :
    printf '%s\t%s\t%s\n' "$name" "$costume" "$env" >>"$tmp"
    sort -o "$tmp" "$tmp"
    mv "$tmp" "$config"
}

# Build the patched binary now, so the next launch is instant instead of ~4s.
warm() {
    while IFS='	' read -r name costume env; do
        [ -n "$costume" ] || continue
        "$state/run.sh" "$costume" --version >/dev/null 2>&1 || true
    done <"$config"
}

# A patched copy is ~250 MB, so costumes nobody wears any more do not get to stay.
prune() {
    for binary in "$state"/bin/claude-*; do
        [ -e "$binary" ] || continue
        worn="$(basename "$binary")"
        worn="${worn#claude-}"
        worn="${worn%%-*}"
        grep -q "	$worn	" "$config" || rm -f "$binary"
    done
}

case "${1:-status}" in
    install)
        [ $# -ge 2 ] || { echo "usage: mascot.sh install <costume> [alias] [config-dir]" >&2; exit 2; }
        sync_scripts
        register "${3:-claude}" "$2" "${4:-}"
        write_aliases
        warm
        prune
        echo "claude-mascot: ${3:-claude} now wears the $2 costume — open a new shell to see it"
        ;;
    remove)
        [ $# -ge 2 ] || { echo "usage: mascot.sh remove <alias>" >&2; exit 2; }
        tmp="$(mktemp)"
        grep -v "^$2	" "$config" >"$tmp" || :
        mv "$tmp" "$config"
        write_aliases
        prune
        echo "claude-mascot: $2 is back to the stock mascot"
        ;;
    refresh)
        sync_scripts
        write_aliases
        warm
        prune
        ;;
    hook)
        # Claude Code was just upgraded? Re-patch for the new build without
        # holding up session start — the costume lands on the next launch.
        [ -s "$config" ] || exit 0
        ("$0" refresh >/dev/null 2>&1 &) || true
        ;;
    status)
        echo "state:     $state"
        echo "shell rc:  $rc"
        if [ -s "$config" ]; then
            echo "costumes:"
            while IFS='	' read -r name costume env; do
                [ -n "$name" ] || continue
                printf '  %-16s %-8s %s\n' "$name" "$costume" "${env:-(default profile)}"
            done <"$config"
        else
            echo "costumes:  none wired up yet"
        fi
        echo "cached:"
        ls -1 "$state/bin" 2>/dev/null | sed 's/^/  /' || echo "  (none)"
        ;;
    list)
        python3 "$scripts/patch.py" --list
        ;;
    uninstall)
        : >"$config"
        write_aliases
        rm -rf "$state"
        echo "claude-mascot: removed"
        ;;
    *)
        sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
        exit 2
        ;;
esac
