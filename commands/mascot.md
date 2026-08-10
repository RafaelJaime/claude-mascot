---
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/scripts/mascot.sh:*)
description: Dress the Claude Code startup mascot (tie, pirate hat) per profile
argument-hint: [install <costume> [alias] [config-dir] | remove <alias> | list | status | refresh | uninstall]
---

## Context

- Current setup: !`"${CLAUDE_PLUGIN_ROOT}/scripts/mascot.sh" status`
- Available costumes: !`"${CLAUDE_PLUGIN_ROOT}/scripts/mascot.sh" list`

## Your task

The user asked: `$ARGUMENTS`

Run the matching `"${CLAUDE_PLUGIN_ROOT}/scripts/mascot.sh"` subcommand and report the
result. Use `install <costume> [alias] [config-dir]` to dress a command,
`remove <alias>` to undo one, `refresh` to re-apply after a Claude Code upgrade,
and `uninstall` to remove everything.

If the request is ambiguous, ask which costume and which command name it applies
to before running anything — `install` rewrites a managed block in the user's
shell rc.

Two things to tell the user when a costume is installed:

- The costume shows up in a **new** shell, since the alias is read from the shell
  rc at startup.
- Anything calling `/opt/homebrew/bin/claude` directly (IDE extensions, scripts,
  non-interactive shells) bypasses the alias and keeps the stock mascot.
