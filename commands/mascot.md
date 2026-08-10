---
allowed-tools: Bash
description: Dress the Claude Code startup mascot — tie, pirate hat, crown, halo, shades, buddy
argument-hint: "[install <costume> [alias] [config-dir] | remove <alias> | refresh | uninstall]"
---

## Wardrobe

!`"${CLAUDE_PLUGIN_ROOT}/scripts/mascot.sh" list 2>/dev/null || ~/.claude-mascot/mascot.sh list`

## Currently worn

!`"${CLAUDE_PLUGIN_ROOT}/scripts/mascot.sh" status 2>/dev/null || ~/.claude-mascot/mascot.sh status`

## Your task

Arguments: `$ARGUMENTS`

**If the arguments are empty** — this is a menu request. Do not call any tool, do
not investigate anything, do not offer to do the work. Reply immediately with the
wardrobe and what each command currently wears, both taken from above, and this
line on how to pick:

    /claude-mascot:mascot install <costume> [command] [config-dir]

with one worked example (`install buddy`, and `install crown claude-work
~/.claude-work` for a second profile). Then stop. That is the whole reply.

**If arguments were given**, run exactly one command:

```
"${CLAUDE_PLUGIN_ROOT}/scripts/mascot.sh" $ARGUMENTS
```

and report its output in a line or two. No other tools, no follow-up work.

Worth mentioning after an `install`: the costume shows up in a **new** shell,
since the alias is read from the shell rc at startup.
