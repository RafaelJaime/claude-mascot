# claude-mascot

Give each Claude Code profile its own startup mascot, so two terminals are told
apart at a glance.

```
 ▐▛███▜▌   Claude Code v2.1.220        ▗▄▟███▙▄▖   Claude Code v2.1.220
▝▜██▄██▛▘  Opus 5 · Claude Max          ▐▛███▜▌    Opus 5 · Claude Max
  ▘▘▼▝▝    ~/work/personal             ▝▜█████▛▘   ~/work/clients
                                         ▘▘ ▝▝
       tie                                    pirate hat
```

Purely cosmetic. It never touches your Homebrew install: each costume is a
patched *copy* of the binary, rebuilt automatically whenever Claude Code updates.

## Install

```
/plugin marketplace add RafaelJaime/claude-mascot
/plugin install claude-mascot
```

Then dress your commands:

```
/mascot install tie
/mascot install pirate claude-work ~/.claude-work
```

`install <costume> [alias] [config-dir]` wires up a shell alias — the third
argument sets `CLAUDE_CONFIG_DIR`, which is how you run a second profile. Open a
new shell and the costume is there.

Everything the slash command does is also a plain CLI, if you prefer:

```
~/.claude-mascot/mascot.sh status | list | refresh | remove <alias> | uninstall
```

## Requirements

macOS with Claude Code installed through Homebrew, plus `python3` (the system one
is fine). Both are checked at runtime — if anything is missing, or a costume
cannot be applied, the alias silently falls back to the stock binary, so `claude`
never breaks.

## How it works

Claude Code ships as a Bun single-file executable, and its transpiled JS bundle
lives inside as plain text. The startup mascot is drawn by a small component out
of block-drawing glyphs, so its markup can be edited in place. Two constraints
shape the patch:

- **The file's byte length must not change.** The Bun payload records module
  offsets, so growing or shrinking the bundle corrupts everything after the edit.
- **Glyphs must stay written as `\uXXXX` escapes.** The bundle is read as
  Latin-1; a literal UTF-8 character comes out as mojibake.

The bytes for a costume are therefore bought from the mascot itself: the
memoisation scaffolding around its constant elements (`let X;if(c[n]===J)X=…;else
X=c[n];` → `let X=…;`) is pure caching, so inlining it frees ~100 bytes and only
costs a recompute per render. Leftover budget is handed back as spaces. The hat
needs a fourth row that the animated wrapper would clip, so the wrapper is also
made to always reserve its taller frame — a same-length edit.

Nothing is located by minified name. The mascot is found through its own glyphs
and the `clawd_body` / `clawd_background` theme colours, and the identifiers
around it are read back out of the match, so an upstream release renaming its
internals does not break the patch.

The patched copy is then ad-hoc re-signed (keeping the original entitlements —
without `allow-jit` the JS engine is killed on launch) and stripped of its
quarantine flag, which macOS otherwise treats as fatal on an ad-hoc signature.

`scripts/run.sh` is what the alias points at: it resolves the Homebrew binary,
builds and caches a patched copy keyed by that build's size and mtime, checks the
result actually starts, and execs it. The plugin's `SessionStart` hook re-runs
that in the background, so after `brew upgrade claude-code` the costume is
already rebuilt by the time you open the next session.

## Caveats

- Each costume keeps a full copy of the binary (~250 MB) under
  `~/.claude-mascot/bin`. Copies from older builds are deleted on refresh.
- Anything invoking `/opt/homebrew/bin/claude` directly — IDE extensions,
  scripts, non-interactive shells — bypasses the alias and shows the stock
  mascot.
- Apple Terminal gets a different, lower-resolution mascot from another code
  path, which is left untouched.
- `install` and `remove` rewrite a marked block in `~/.zshrc`
  (`# >>> claude-mascot >>>`). Nothing outside that block is modified.

## Adding a costume

Costumes live in `COSTUMES` in `scripts/patch.py`; each one returns the markup
edits that put it on the mascot, written against the identifiers found in the
match. Keep an eye on the byte budget — `patch_region` fails loudly rather than
producing a broken binary, and `run.sh` falls back to stock when it does.

## Disclaimer

Unofficial and not affiliated with Anthropic. It modifies a local copy of the
Claude Code binary for cosmetic reasons only; nothing about licensing,
authentication or telemetry is touched. A future release may reshape the mascot
enough that patching stops applying, in which case you get the stock mascot back
until the patterns are updated.

MIT licensed.
