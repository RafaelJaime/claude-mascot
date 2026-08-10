#!/usr/bin/env python3
"""Patch the Claude Code binary's embedded JS bundle to dress up the startup
mascot.

Claude Code ships as a Bun single-file executable and its transpiled JS bundle
lives inside as plain text, so the mascot's markup can be edited in place. Two
hard constraints shape the patch:

  * The file's total byte length must not change — the Bun payload records module
    offsets, so growing or shrinking the bundle corrupts everything after the
    edit.
  * The bundle is read as Latin-1, so glyphs have to stay written as `\\uXXXX`
    escapes. A literal UTF-8 character renders as mojibake.

The bytes for a costume are bought by stripping the memoisation scaffolding
around the mascot's elements (`let X;if(c[n]===J)X=…,c[n]=X;else X=c[n];` becomes
`let X=…;`). That is pure caching, so inlining it only costs a recompute per
render. Whatever budget is left over is handed back as spaces after the mascot
function's opening brace, keeping the region exactly its original size.

Costumes that need more room than the mascot's own 9x3 cell — a hat's extra row,
a companion's extra columns — also resize the frame the animated wrapper clips
the mascot to, which is a same-length edit and needs no budget.

Everything is located structurally — by the mascot's own glyphs and by the
`clawd_body` / `clawd_background` theme colours — so minified identifiers may be
renamed by an upstream release without breaking the patch.

Usage: patch.py <src-binary> <dst-binary> <costume>
       patch.py --list
"""

import re
import sys

ART = rb"(?:\\u[0-9A-Fa-f]{4})+"

# Row 2 of the mascot, its solid body, drawn over the mascot background colour.
BODY = re.compile(
    rb'(\w+)=(\w+)\.jsx\((\w+),\{color:"clawd_body",'
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
# The frame the animated wrapper clips the mascot to.
FRAME = re.compile(
    rb'height:(\w+),width:(\w+),flexDirection:"column",flexShrink:0,'
    rb'overflow:"hidden"'
)

FUNCTION = re.compile(rb"function \w+\(\w+\)\{")
RETURN = re.compile(rb"return \w+\}")

# `let X;if(cache[n]===sentinel)X=<expr>,cache[n]=X;else X=cache[n];`
CONST_MEMO = re.compile(rb"let (\w+);if\((\w+)\[(\d+)\]===\w+\)\1=")
# `let X;if(cache[n]!==dep||…)X=<expr>,cache[n]=dep,…;else X=cache[m];`
VALUE_MEMO = re.compile(rb"let (\w+);if\((\w+)\[\d+\]!==[^)]+\)\1=")


def glyphs(art):
    """Block glyphs spelled the way the bundle spells them: ASCII escapes."""
    return "".join(
        char if char == " " else f"\\u{ord(char):04X}" for char in art
    ).encode()


def analyse(region):
    """The mascot's rows and the identifiers the bundle happens to use for them."""
    body, feet, stack = (
        pattern.search(region) for pattern in (BODY, FEET, STACK)
    )
    if not (body and feet and stack):
        raise SystemExit("the mascot's rows are not where they used to be")
    # Row 2 is the row whose middle child is the body — that is what tells it
    # apart from row 1, which has the same shape.
    row2 = re.search(
        rb"(\w+)\.jsxs\((\w+),\{children:\[(\w+),%s,(\w+)\]\}\)"
        % re.escape(body.group(1)),
        region,
    )
    if not row2:
        raise SystemExit("the mascot's body row is not where it used to be")
    return {
        "jsx": feet.group(1),
        "text": feet.group(2),
        "body": body,
        "feet": feet,
        "row2": row2,
        "stack": stack,
    }


def hat(parts, art, colour):
    """Sit `art` on the mascot's head, as a row above the ones it already has."""
    stack = parts["stack"]
    brim = b'%s.jsx(%s,{color:"%s",children:"%s"})' % (
        parts["jsx"],
        parts["text"],
        colour.encode(),
        glyphs(art),
    )
    rows = b",".join(stack.group(index) for index in (3, 4, 5))
    return [
        (
            stack.group(0),
            b'%s.jsxs(%s,{flexDirection:"column",flexShrink:0,children:[%s,%s]})'
            % (stack.group(1), stack.group(2), brim, rows),
        )
    ], {"taller": True}


def tie(parts):
    """A collar notch sunk into the body, with a red tie hanging below it."""
    body, feet = parts["body"], parts["feet"]
    return [
        (body.group(0), body.group(0).replace(body.group(4), glyphs("██▄██"))),
        (
            feet.group(0),
            b'%s.jsxs(%s,{color:"clawd_body",children:["  ","%s",'
            b'%s.jsx(%s,{color:"error",children:"%s"}),"%s","  "]})'
            % (
                feet.group(1),
                feet.group(2),
                feet.group(3),
                parts["jsx"],
                parts["text"],
                glyphs("▼"),
                feet.group(4),
            ),
        ),
    ], {}


def shades(parts):
    """A dark visor across the body's top edge, right where the eyes would be."""
    body = parts["body"]
    return [
        (body.group(0), body.group(0).replace(body.group(4), glyphs("█▄▄▄█")))
    ], {}


def buddy(parts):
    """A smaller mascot, standing on the same line, holding the big one's hand."""
    row2, feet = parts["row2"], parts["feet"]
    friend = b'%s.jsx(%s,{color:"clawd_body",children:"%s"})' % (
        parts["jsx"],
        parts["text"],
        glyphs("─▟█▙"),
    )
    return [
        (row2.group(0), row2.group(0)[:-3] + b"," + friend + b"]})"),
        (feet.group(0), feet.group(0)[:-3] + b',"' + glyphs(" ▘ ▝") + b'"]})'),
    ], {"columns": 13}


COSTUMES = {
    "tie": (tie, "a red necktie under a collar notch"),
    "pirate": (
        lambda parts: hat(parts, "▗▄▟███▙▄▖", "subtle"),
        "a tricorn pirate hat",
    ),
    "crown": (
        lambda parts: hat(parts, " ▄█▄█▄█▄ ", "chromeYellow"),
        "a golden crown",
    ),
    "halo": (
        lambda parts: hat(parts, "  ▗▄▄▄▖  ", "chromeYellow"),
        "a halo, floating overhead",
    ),
    "shades": (shades, "sunglasses"),
    "buddy": (buddy, "hand in hand with a smaller mascot"),
}


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
    edits, frame = COSTUMES[name][0](analyse(region))
    cost = sum(len(new) - len(old) for old, new in edits)

    patched = strip_memoisation(region, CONST_MEMO)
    if len(patched) - original_size + cost > 0:
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
    return patched, frame


def resize_frame(data, taller=False, columns=None):
    """Grow the frame the animated wrapper clips the mascot to.

    Both edits keep their original length: the height takes the wrapper's own
    taller branch — it already reserves one more row for a crouching mascot — and
    the width is written as a literal in the space the identifier occupied.
    """
    if not taller and not columns:
        return
    frame = FRAME.search(data)
    if not frame:
        raise SystemExit("the mascot's frame is not where it used to be")

    if taller:
        reserve = re.compile(rb"const %s=\w+\?(\w+)\+1:\1;" % re.escape(frame.group(1)))
        height = reserve.search(data)
        if not height:
            raise SystemExit("the mascot's row reserve is not where it used to be")
        room = height.end() - height.start() - 1
        data[height.start() : height.end()] = (
            b"const %s=%s+1" % (frame.group(1), height.group(1))
        ).ljust(room) + b";"

    if columns:
        room = len(frame.group(2)) + len(b"width:")
        wider = b"width:%d" % columns
        if len(wider) > room:
            raise SystemExit("no room to widen the mascot's frame")
        start = frame.start(2) - len(b"width:")
        data[start : start + room] = wider.ljust(room)


def region_bounds(data):
    """Byte range of the mascot component, from its `function` to its `return`.

    Other components draw with the mascot's colours too, so every candidate is
    validated by requiring all of its rows to sit in the same function.
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


def main():
    if sys.argv[1:] == ["--list"]:
        for name, (_, description) in COSTUMES.items():
            print(f"{name:8} {description}")
        return
    if len(sys.argv) != 4 or sys.argv[3] not in COSTUMES:
        raise SystemExit(f"usage: {sys.argv[0]} <src> <dst> <{'|'.join(COSTUMES)}>")
    src, dst, name = sys.argv[1:4]

    data = bytearray(open(src, "rb").read())
    original_size = len(data)

    lo, hi = region_bounds(data)
    data[lo:hi], frame = patch_region(bytes(data[lo:hi]), name)
    resize_frame(data, **frame)

    if len(data) != original_size:
        raise SystemExit("internal error: file size changed")

    with open(dst, "wb") as out:
        out.write(data)
    print(f"applied the {name} costume")


if __name__ == "__main__":
    main()
