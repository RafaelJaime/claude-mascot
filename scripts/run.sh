#!/bin/sh
# Launch Claude Code with a costumed startup mascot.
#
#   run.sh <costume> [claude args...]
#
# Patched binaries are cached per Claude Code build. When Claude Code is upgraded
# the cache key changes and the costume is re-applied on the next launch. If
# patching ever fails — upstream reshaped the mascot, signing was refused, the
# result would not start — this falls back to the stock binary, so the `claude`
# command never breaks.

set -eu

costume="$1"
shift

scripts="$(cd "$(dirname "$0")" && pwd)"
state="${CLAUDE_MASCOT_HOME:-$HOME/.claude-mascot}"
launcher="${CLAUDE_MASCOT_BIN:-/opt/homebrew/bin/claude}"

real="$(readlink "$launcher" || true)"
[ -n "$real" ] || real="$launcher"
case "$real" in
    /*) ;;
    *) real="$(dirname "$launcher")/$real" ;;
esac

if [ ! -x "$real" ]; then
    echo "claude-mascot: no Claude Code binary at $launcher" >&2
    exit 127
fi

# Keyed by the upstream build *and* the recipe, so editing a costume rebuilds too.
build="$(stat -f '%z-%m' "$real")"
recipe="$(shasum "$scripts/patch.py" | cut -c1-8)"
patched="$state/bin/claude-$costume-$build-$recipe"

if [ ! -x "$patched" ]; then
    mkdir -p "$state/bin"
    rm -f "$state/bin/claude-$costume-"*
    if python3 "$scripts/patch.py" "$real" "$patched.tmp" "$costume" >/dev/null &&
        codesign -f -s - --preserve-metadata=entitlements,flags "$patched.tmp" 2>/dev/null &&
        # Copies inherit the quarantine flag; ad-hoc signed + quarantined is killed on exec.
        { xattr -c "$patched.tmp" 2>/dev/null || true; } &&
        chmod +x "$patched.tmp" &&
        "$patched.tmp" --version >/dev/null 2>&1; then
        mv "$patched.tmp" "$patched"
    else
        rm -f "$patched.tmp"
        echo "claude-mascot: could not apply the $costume costume, using stock Claude Code" >&2
        exec "$real" "$@"
    fi
fi

exec "$patched" "$@"
