# claude-mascot

Give each Claude Code profile its own startup mascot, so two terminals are told
apart at a glance.

```
   ▄█▄█▄█▄         ▗▄▟███▙▄▖          ▗▄▄▄▖
   ▐▛███▜▌          ▐▛███▜▌          ▐▛███▜▌
  ▝▜█████▛▘        ▝▜█████▛▘        ▝▜█████▛▘
    ▘▘ ▝▝            ▘▘ ▝▝            ▘▘ ▝▝
    crown            pirate            halo

   ▐▛███▜▌          ▐▛███▜▌          ▐▛███▜▌
  ▝▜██▄██▛▘        ▝▜█▄▄▄█▛▘        ▝▜█████▛▘─▟█▙
    ▘▘▼▝▝            ▘▘ ▝▝            ▘▘ ▝▝   ▘ ▝
     tie             shades           buddy
```

The crown and halo are gold, the tie is red, the hat is dark — colour comes from
the theme, so every costume follows light and dark alike.

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

The plugin also ships a skill, so asking Claude to "customise my Claude Code
mascot" — or to make two profiles tell themselves apart — is enough; it will
reach for the same commands.

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
match, plus any frame it needs — `{"taller": True}` for a hat's extra row,
`{"columns": n}` for a companion's extra width. Keep an eye on the byte budget:
`patch_region` fails loudly rather than producing a broken binary, and `run.sh`
falls back to stock when it does.

## Prior art

Customising Claude Code's looks is well-trodden ground, and there is no official
support for it — the request to make the startup mascot configurable
([#43834](https://github.com/anthropics/claude-code/issues/43834)) was closed as
a duplicate of a still-open one.

- [tweakcc](https://github.com/Piebald-AI/tweakcc) is the broad, mature tool:
  themes, system prompts, spinners, thinking verbs, input styling. It patches
  `cli.js` on npm installs and repacks the native binary with node-lief. It can
  *hide* the startup logo and change the banner message, but not dress the
  mascot, and it keeps a single config — no per-profile looks.
- [claudecode-buddy-crack](https://github.com/Pickle-Pixel/claudecode-buddy-crack)
  customises the *companion pet* (species, rarity, hats, eyes) by flipping a
  spread in the binary — same byte-length discipline as here — and re-patches
  from a `SessionStart` hook.
- **clawd-modifier**, an openclaw skill, changes the mascot's colours and bolts
  arms and accessories onto its ASCII art.

What this one does differently: a costume **per profile**, wired through shell
aliases and `CLAUDE_CONFIG_DIR`; patched builds cached and rebuilt automatically
per upstream binary; a launch check with a fallback to stock; and structural
anchors (glyphs and theme colour names) instead of minified identifiers.

## Disclaimer

Unofficial and not affiliated with Anthropic. It modifies a local copy of the
Claude Code binary for cosmetic reasons only; nothing about licensing,
authentication or telemetry is touched. A future release may reshape the mascot
enough that patching stops applying, in which case you get the stock mascot back
until the patterns are updated.

MIT licensed.
