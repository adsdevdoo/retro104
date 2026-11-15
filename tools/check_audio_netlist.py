#!/usr/bin/env python3
"""Compare the netlist exported from pc104-audio.kicad_sch with tools/audio_design.py.

Usage: python tools/check_audio_netlist.py build/audio/pc104-audio.net
Writes hardware/pc104-audio/reports/netlist-check.txt; exit code 1 on any difference.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_design as A  # noqa: E402
from sexpr import parse, find, first  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "hardware", "pc104-audio", "reports", "netlist-check.txt")


def main():
    tree = parse(open(sys.argv[1], encoding="utf-8").read())
    got = {}
    for net in find(first(tree, "nets"), "net"):
        name = str(first(net, "name")[1])
        name = name[1:] if name.startswith("/") else name  # local labels get the root sheet prefix
        got[name] = sorted((str(first(n, "ref")[1]), str(first(n, "pin")[1])) for n in find(net, "node"))
    comps = {str(first(c, "ref")[1]): str(first(c, "value")[1]) for c in find(first(tree, "components"), "comp")}
    errors = []
    for net, pins in A.NETS.items():
        want = sorted(pins)
        have = got.get(net)
        if have is None:
            errors.append("net %s missing" % net)
        elif have != want:
            errors.append("net %s differs: extra %s, missing %s" % (
                net, sorted(set(have) - set(want)), sorted(set(want) - set(have))))
    for ref, pin in A.NC:
        nets = [n for n, pins in got.items() if (ref, pin) in pins]
        if len(nets) != 1 or not nets[0].startswith("unconnected-") or len(got[nets[0]]) != 1:
            errors.append("NC pin %s.%s is in %s" % (ref, pin, nets))
    extra = [n for n in got if n not in A.NETS and not n.startswith("unconnected-")]
    errors += ["unexpected net %s %s" % (n, got[n]) for n in extra]
    missing_parts = [r for r in A.PARTS if r not in comps]
    errors += ["component %s missing" % r for r in missing_parts]
    for r, p in A.PARTS.items():
        if r in comps and comps[r] != p["value"]:
            errors.append("component %s value %s != %s" % (r, comps[r], p["value"]))
    lines = ["pc104-audio: netlist vs tools/audio_design.py",
             "nets in design: %d, nets in netlist: %d (of them unconnected-*: %d)" % (
                 len(A.NETS), len(got), sum(1 for n in got if n.startswith("unconnected-"))),
             "pins connected: %d, pins marked NC: %d, components: %d" % (
                 sum(len(v) for v in A.NETS.values()), len(A.NC), len(A.PARTS)),
             "differences: %d" % len(errors)] + errors
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
