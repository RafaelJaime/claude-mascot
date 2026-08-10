---
name: claude-mascot
description: >
  Dress the Claude Code startup mascot — tie, pirate hat, crown, halo, shades, or
  a smaller companion holding its hand — with a different look per profile.
  Trigger when the user wants to customise, skin, theme or personalise their
  Claude Code startup screen, logo, banner, ASCII art or mascot, or wants to tell
  two Claude Code profiles apart visually. Also: "personalizar claude",
  "cambiar el logo de claude", "customize my claude".
---

# claude-mascot

Purely cosmetic. Each costume is a patched **copy** of the Claude Code binary;
the Homebrew install is never modified, and the launcher falls back to the stock
binary whenever patching fails, so `claude` cannot end up broken.

## Doing the work

Everything runs through one script — `${CLAUDE_PLUGIN_ROOT}/scripts/mascot.sh`,
also copied to `~/.claude-mascot/mascot.sh` once anything is installed:

| Want | Run |
|---|---|
| See the costumes | `mascot.sh list` |
| See what is wired up | `mascot.sh status` |
| Dress a command | `mascot.sh install <costume> [alias] [config-dir]` |
| Undo one | `mascot.sh remove <alias>` |
| Re-apply after an upgrade | `mascot.sh refresh` |
| Remove everything | `mascot.sh uninstall` |

`install`'s third argument sets `CLAUDE_CONFIG_DIR`, which is how a second
profile gets its own costume:

```sh
mascot.sh install tie                                  # `claude` wears a tie
mascot.sh install pirate claude-work ~/.claude-work    # a second profile
```

## What to tell the user

- The costume appears in a **new** shell — `install` writes an alias into a
  managed block in `~/.zshrc`, which is read at shell startup.
- Anything calling the Claude Code binary directly (IDE extensions, scripts,
  non-interactive shells) bypasses the alias and keeps the stock mascot.
- The first launch after a Claude Code upgrade re-patches (a few seconds); the
  plugin's `SessionStart` hook usually does it in the background first.
- Each costume caches a full copy of the binary (~250 MB) under
  `~/.claude-mascot/bin`. Copies from older builds are deleted automatically.

## Requirements

macOS, Claude Code installed via Homebrew, and `python3`. On anything else the
launcher falls back to the stock binary and says so.

## Adding a costume

Costumes are entries in `COSTUMES` in `scripts/patch.py`, each a small function
returning the markup edits that put it on the mascot. Read that file's docstring
first: the patch is byte-length-neutral by necessity, and the budget is bought by
inlining the mascot's memoisation. `patch_region` fails loudly rather than
producing a broken binary.
