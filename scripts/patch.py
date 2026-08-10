#!/usr/bin/env python3
"""Patch the Claude Code binary's embedded JS bundle to dress up the startup
mascot: a tie, or a pirate hat.

Claude Code ships as a Bun single-file executable and its transpiled JS bundle
lives inside as plain text, so the mascot's markup can be edited in place. Two
hard constraints shape the patch:

  * The file's total byte length must not change — the Bun payload records module
    offsets, so growing or shrinking the bundle corrupts everything after the
    edit.
  * The bundle is read as Latin-1, so glyphs have to stay written as `\\uXXXX`
    escapes. A literal UTF-8 character renders as mojibake.

The bytes for the costume are bought by stripping the memoisation scaffolding
around the mascot's elements (`let X;if(c[n]===J)X=…,c[n]=X;else X=c[n];` becomes
`let X=…;`). That is pure caching, so inlining it only costs a recompute per
render. Whatever budget is left over is handed back as spaces after the mascot
function's opening brace, keeping the region exactly its original size.

Everything is located structurally — by the mascot's own glyphs and by the
`clawd_body` / `clawd_background` theme colours — so minified identifiers may be
renamed by an upstream release without breaking the patch.

Usage: patch.py <src-binary> <dst-binary> <costume>
       patch.py --list
"""

import re
import sys

COSTUMES = {
    "tie": "a red necktie under a collar notch",
    "pirate": "a tricorn pirate hat",
}

ART = rb"(?:\\u[0-9A-Fa-f]{4})+"

# Row 2 of the mascot, its solid body, drawn over the mascot background colour.
BODY = re.compile(
    rb'(\w+)\.jsx\((\w+),\{color:"clawd_body",'
    rb'backgroundColor:"clawd_background",children:"(' + ART + rb')"\}\)'
)
# Row 3 of the mascot, its two feet, separated by a literal space.
FEET = re.compile(
    rb'(\w+)\.jsxs?\((\w+),\{color:"clawd_body",'
    rb'children:\["  ","(' + ART + rb') (' + ART + rb')","  "\]\}\)'
)
# The column stacking the mascot's rows.
STACK = re.compile(
    rb'(\w+)\.jsxs\((\w+),\{flexDirection:"column",flexShrink:0,'
    rb"children:\[(\w+),(\w+),(\w+)\]\}\)"
)

FUNCTION = re.compile(rb"function \w+\(\w+\)\{")
RETURN = re.compile(rb"return \w+\}")

# The animated wrapper clips the mascot to a fixed number of rows.
FRAME = re.compile(
    rb'height:(\w+),width:\w+,flexDirection:"column",flexShrink:0,overflow:"hidden"'
)

# `let X;if(cache[n]===sentinel)X=<expr>,cache[n]=X;else X=cache[n];`
CONST_MEMO = re.compile(rb"let (\w+);if\((\w+)\[(\d+)\]===\w+\)\1=")
# `let X;if(cache[n]!==dep||…)X=<expr>,cache[n]=dep,…;else X=cache[m];`
VALUE_MEMO = re.compile(rb"let (\w+);if\((\w+)\[\d+\]!==[^)]+\)\1=")


def glyphs(text):
    """Block glyphs spelled the way the bundle spells them: ASCII escapes."""
    return "".join(f"\\u{ord(char):04X}" for char in text).encode()


def costume(name, region):
    """The single (old, new) markup edit that puts `name` on the mascot."""
    if name == "tie":
        body = BODY.search(region)
        feet = FEET.search(region)
        if not body or not feet:
            raise SystemExit("mascot body/feet rows not found")
        jsx, text = feet.group(1), feet.group(2)
        left, right = feet.group(3), feet.group(4)
        # A collar notch sunk into the body, and a red tie hanging below it.
        return [
            (body.group(0), body.group(0).replace(body.group(3), glyphs("██▄██"))),
            (
                feet.group(0),
                b'%s.jsxs(%s,{color:"clawd_body",children:["  ","%s",'
                b'%s.jsx(%s,{color:"error",children:"%s"}),"%s","  "]})'
                % (jsx, text, left, jsx, text, glyphs("▼"), right),
            ),
        ]

    stack = STACK.search(region)
    body = BODY.search(region)
    if not stack or not body:
        raise SystemExit("mascot row stack not found")
    jsx, text = stack.group(1), body.group(2)
    rows = b",".join(stack.group(index) for index in (3, 4, 5))
    # A tricorn hat, dropped on top of the existing rows.
    return [
        (
            stack.group(0),
            b'%s.jsxs(%s,{flexDirection:"column",flexShrink:0,children:['
            b'%s.jsx(%s,{color:"subtle",children:"%s"}),%s]})'
            % (jsx, stack.group(2), jsx, text, glyphs("▗▄▟███▙▄▖"), rows),
        )
    ]


def strip_memoisation(region, pattern):
    """Inline elements cached by `pattern`, freeing their caching scaffolding."""
    position = 0
    while True:
        match = pattern.search(region, position)
        if not match:
            return region
        var, cache = match.group(1), match.group(2)
        tail = re.compile(
            rb"(?:,%s\[\d+\]=[\w.]+)+;else %s=%s\[\d+\];"
            % (re.escape(cache), re.escape(var), re.escape(cache))
        )
        end = tail.search(region, match.end())
        if not end:
            position = match.end()
            continue
        region = (
            region[: match.start()]
            + b"let %s=" % var
            + region[match.end() : end.start()]
            + b";"
            + region[end.end() :]
        )
        position = match.start()


def patch_region(region, name):
    original_size = len(region)
    edits = costume(name, region)

    patched = strip_memoisation(region, CONST_MEMO)
    if len(patched) - original_size + sum(len(new) - len(old) for old, new in edits) > 0:
        patched = strip_memoisation(patched, VALUE_MEMO)

    for old, new in edits:
        if patched.count(old) != 1:
            raise SystemExit(f"markup to replace is not unique: {old[:48]!r}")
        patched = patched.replace(old, new)

    padding = original_size - len(patched)
    if padding < 0:
        raise SystemExit(f"{name}: costume needs {-padding} more bytes than are free")
    opening = FUNCTION.match(patched)
    patched = patched[: opening.end()] + b" " * padding + patched[opening.end() :]

    assert len(patched) == original_size
    return patched


def region_bounds(data):
    """Byte range of the mascot component, from its `function` to its `return`.

    Other components draw with the mascot's colours too, so every candidate is
    validated by requiring all three of its rows to sit in the same function.
    """
    # Anchor on a cheap literal first: regex-scanning the whole binary is slow.
    anchor = b'backgroundColor:"clawd_background",children:"\\u'
    at = data.find(anchor)
    while at != -1:
        lo = max(0, at - 20000)
        starts = [match.start() for match in FUNCTION.finditer(data, lo, at)]
        end = RETURN.search(data, at, at + 20000)
        if starts and end:
            region = bytes(data[starts[-1] : end.end()])
            if BODY.search(region) and FEET.search(region) and STACK.search(region):
                return starts[-1], end.end()
        at = data.find(anchor, at + 1)
    raise SystemExit("mascot not found — the bundle no longer looks like this")


def unclip_frame(data):
    """Always reserve the mascot's taller frame, so a fourth row is not clipped.

    The animated wrapper reserves `base` rows, or `base + 1` when it expects the
    mascot to crouch. Taking the taller branch unconditionally is a same-length
    edit, so it needs no byte budget of its own.
    """
    frame = FRAME.search(data)
    if not frame:
        raise SystemExit("mascot frame not found")
    reserve = re.compile(rb"const %s=\w+\?(\w+)\+1:\1;" % re.escape(frame.group(1)))
    height = reserve.search(data)
    if not height:
        raise SystemExit("mascot row reserve not found")
    taller = b"const %s=%s+1" % (frame.group(1), height.group(1))
    data[height.start() : height.end()] = taller.ljust(height.end() - height.start() - 1) + b";"


def main():
    if sys.argv[1:] == ["--list"]:
        for name, description in COSTUMES.items():
            print(f"{name:8} {description}")
        return
    if len(sys.argv) != 4 or sys.argv[3] not in COSTUMES:
        raise SystemExit(f"usage: {sys.argv[0]} <src> <dst> <{'|'.join(COSTUMES)}>")
    src, dst, name = sys.argv[1:4]

    data = bytearray(open(src, "rb").read())
    original_size = len(data)

    lo, hi = region_bounds(data)
    data[lo:hi] = patch_region(bytes(data[lo:hi]), name)
    if name == "pirate":
        unclip_frame(data)

    if len(data) != original_size:
        raise SystemExit("internal error: file size changed")

    with open(dst, "wb") as out:
        out.write(data)
    print(f"applied the {name} costume")


if __name__ == "__main__":
    main()
