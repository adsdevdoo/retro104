"""Minimal S-expression writer/reader for KiCad 9 files (deterministic output)."""

import re
import uuid

NS = uuid.UUID("2b0c6c0e-7d1e-4f0a-9d43-104104104104")


def uid(key):
    return str(uuid.uuid5(NS, key))


class Q(str):
    """A string that must be written in double quotes."""


def fmt(v):
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return str(v)
    s = ("%.6f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _atom(a):
    if isinstance(a, Q):
        return '"%s"' % a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    if isinstance(a, (int, float)):
        return fmt(a)
    return str(a)


def dump(node, indent=0):
    """node = [head, item, ...]; items are nodes (lists) or atoms."""
    tab = "\t" * indent
    if not any(isinstance(x, list) for x in node):
        return tab + "(" + " ".join(_atom(x) for x in node) + ")"
    head = [node[0]]
    rest = node[1:]
    # keep leading atoms on the head line
    while rest and not isinstance(rest[0], list):
        head.append(rest.pop(0))
    lines = [tab + "(" + " ".join(_atom(x) for x in head)]
    for x in rest:
        if isinstance(x, list):
            lines.append(dump(x, indent + 1))
        else:
            lines.append("\t" * (indent + 1) + _atom(x))
    lines.append(tab + ")")
    return "\n".join(lines)


_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


def parse(text):
    """Parse an S-expression into nested lists; quoted strings become Q."""
    stack = [[]]
    pos = 0
    while True:
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            stack[-1].append(done)
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(m.group(4))
    return stack[0][0]


def find(node, head):
    return [x for x in node if isinstance(x, list) and x and x[0] == head]


def first(node, head):
    r = find(node, head)
    return r[0] if r else None
