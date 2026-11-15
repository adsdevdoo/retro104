#!/usr/bin/env python3
"""Independent checks of pc104-audio and its fabrication files (no KiCad API needed).

1. Outline (Edge.Cuts in PCB and Gerber) = PC/104 3.775 x 3.550 in.
2. CN1/CN2 pads and H1-H4 at the PC/104 v2.6 Fig. 3/4 coordinates (same as pc104-blank).
3. Every Excellon hit (PTH and NPTH) matches a pad or via of the saved board, diameters included,
   and every drilled pad/via of the board is in the drill files.
4. Audio jacks: body front on the top edge; game header J4 within the bottom I/O overhang region.
Writes hardware/pc104-audio/reports/fab-check.md; exit code 1 on any failure.
"""

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_board as CB  # noqa: E402
import pc104_data as D  # noqa: E402
from sexpr import parse, find, first  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRJ = os.path.join(REPO, "hardware", "pc104-audio")
PCB = os.path.join(PRJ, "pc104-audio.kicad_pcb")
FAB = os.path.join(PRJ, "fabrication", "gerbers")
OUT = os.path.join(PRJ, "reports", "fab-check.md")
TOL = 0.01
FAIL = []


def check(ok, msg):
    if not ok:
        FAIL.append(msg)
    return ok


def rot(x, y, deg):
    a = math.radians(deg)
    # KiCad: y down, positive angle = counter-clockwise on screen
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def board_items(tree):
    """[(ref, pad, x, y, drill_w, drill_h, kind)] for drilled pads, plus vias."""
    out = []
    for fp in find(tree, "footprint"):
        at = first(fp, "at")
        fx, fy, frot = float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0
        ref = str([pp[2] for pp in find(fp, "property") if pp[1] == "Reference"][0])
        for pad in find(fp, "pad"):
            dr = first(pad, "drill")
            if not dr:
                continue
            vals = [v for v in dr[1:] if not isinstance(v, list)]
            if vals and vals[0] == "oval":
                w, h = float(vals[1]), float(vals[2])
            else:
                w = h = float(vals[0])
            pat = first(pad, "at")
            px, py = float(pat[1]), float(pat[2])
            dx, dy = rot(px, py, frot)
            out.append((ref, str(pad[1]), fx + dx, fy + dy, min(w, h), max(w, h), pad[2]))
    for v in find(tree, "via"):
        at = first(v, "at")
        d = float(first(v, "drill")[1])
        out.append(("via", "", float(at[1]), float(at[2]), d, d, "thru_hole"))
    return out


def excellon(path):
    tools, hits, cur = {}, [], None
    lines = open(path, encoding="ascii").read().splitlines()
    for line in lines:
        line = line.strip()
        m = re.fullmatch(r"T(\d+)C([\d.]+)", line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        m = re.fullmatch(r"T(\d+)", line)
        if m:
            cur = m.group(1)
            continue
        m = re.fullmatch(r"X(-?[\d.]+)Y(-?[\d.]+)(?:G85X(-?[\d.]+)Y(-?[\d.]+))?", line)
        if m:
            x, y = float(m.group(1)), float(m.group(2))
            if m.group(3):  # routed slot: centre and length
                x2, y2 = float(m.group(3)), float(m.group(4))
                hits.append((tools[cur], (x + x2) / 2, (y + y2) / 2, math.hypot(x2 - x, y2 - y) + tools[cur]))
            else:
                hits.append((tools[cur], x, y, tools[cur]))
    return hits


def main():
    tree = parse(open(PCB, encoding="utf-8").read())
    x0, y0, x1, y1 = CB.board_outline(tree)
    w, h = x1 - x0, y1 - y0
    lines = ["# Проверка pc104-audio rev A и файлов производства", "",
             "Сгенерировано `tools/check_audio_board.py` по `pc104-audio.kicad_pcb` и `fabrication/gerbers/`.", ""]
    check(abs(w - D.BOARD_X_IN * D.IN) < 0.001 and abs(h - D.BOARD_Y_IN * D.IN) < 0.001, "outline %.3f x %.3f" % (w, h))
    lines.append("- Контур по Edge.Cuts: %.3f × %.3f мм." % (w, h))
    gx0, gy0, gx1, gy1 = CB.gerber_extents(os.path.join(FAB, "pc104-audio-Edge_Cuts.gm1"))
    check(abs(gx1 - gx0 - w) < 0.001 and abs(gy1 - gy0 - h) < 0.001, "Edge.Cuts gerber %.3f x %.3f" % (gx1 - gx0, gy1 - gy0))
    lines.append("- Edge.Cuts в Gerber: %.3f × %.3f мм, начало — левый нижний угол." % (gx1 - gx0, gy1 - gy0))

    pads = CB.pcb_pads(tree) if False else None  # check_board.pcb_pads asserts unrotated footprints
    items = board_items(tree)
    by_ref = {(r, pd): (x, y, dw) for r, pd, x, y, dw, dh, k in items}
    n_ok = 0
    for pad, row, n, xi, yi, _ in D.pad_list("ABCD"):
        ref = "CN2" if row in "AB" else "CN1"
        x, y, dw = by_ref[(ref, pad)]
        X, Y = (x1 - x) / D.IN, (y1 - y) / D.IN
        if check(abs(X - xi) * D.IN < 0.001 and abs(Y - yi) * D.IN < 0.001 and abs(dw - D.CONNECTOR_DRILL_MM) < 0.001,
                 "%s.%s at %.4f,%.4f in" % (ref, pad, X, Y)):
            n_ok += 1
    holes_ok = 0
    for i, (hx, hy) in enumerate(D.HOLES_IN):
        x, y, dw = by_ref[("H%d" % (i + 1), "")]
        if check(abs((x1 - x) / D.IN - hx) * D.IN < 0.001 and abs((y1 - y) / D.IN - hy) * D.IN < 0.001
                 and abs(dw - D.HOLE_DRILL_MM) < 0.001, "H%d" % (i + 1)):
            holes_ok += 1
    lines.append("- CN2/CN1: %d из 104 контактов и %d из 4 крепёжных отверстий на местах PC/104 v2.6 "
                 "(допуск 0.001 мм), как на pc104-blank." % (n_ok, holes_ok))

    # drill files vs board
    pth = excellon(os.path.join(FAB, "pc104-audio-PTH.drl"))
    npth = excellon(os.path.join(FAB, "pc104-audio-NPTH.drl"))
    want = [(r, pd, x - x0, y1 - y, dw, k) for r, pd, x, y, dw, dh, k in items]  # Excellon: Y up
    unmatched = list(want)
    extra = []
    for kind, hits in (("PTH", pth), ("NPTH", npth)):
        for dia, x, y, length in hits:
            m = [it for it in unmatched if abs(it[2] - x) < TOL and abs(it[3] - y) < TOL]
            if not m:
                extra.append("%s %.3f,%.3f d%.2f" % (kind, x, y, dia))
                continue
            it = m[0]
            check(abs(it[4] - dia) < TOL, "%s.%s drilled %.2f, pad %.2f" % (it[0], it[1], dia, it[4]))
            check((kind == "NPTH") == (it[5] == "np_thru_hole"), "%s.%s plating mismatch" % (it[0], it[1]))
            unmatched.remove(it)
    check(not extra, "drill hits without pad/via: %s" % extra[:5])
    check(not unmatched, "pads/vias missing in drill files: %s" % [(u[0], u[1]) for u in unmatched[:5]])
    vias = sum(1 for it in items if it[0] == "via")
    by_d = {}
    for dia, *_ in pth:
        by_d[dia] = by_d.get(dia, 0) + 1
    lines.append("- PTH Excellon: %d отверстий (%s), из них переходных %d; NPTH: %d (монтажные штыри гнёзд "
                 "Ø1.2 мм, 5 × 3). Все совпали с площадками/переходными платы, лишних и пропущенных нет: %s." % (
                     len(pth), ", ".join("%d × Ø%.2f" % (c, d) for d, c in sorted(by_d.items())), vias, len(npth),
                     "да" if not extra and not unmatched else "НЕТ"))

    # mechanics of the I/O connectors
    fps = {str([pp[2] for pp in find(f, "property") if pp[1] == "Reference"][0]): f for f in find(tree, "footprint")}
    for ref in ("J1", "J2", "J3"):
        at = first(fps[ref], "at")
        front = float(at[2]) - 3.5  # rotated 180: connector edge at local y = +3.5
        check(abs(front - y0) < 0.001, "%s front at %.3f" % (ref, front))
    lines.append("- Гнёзда J1–J3: передняя грань корпуса на верхнем крае (y = %.3f мм), центры X = %s мм "
                 "от правого края (зона выступа PC/104 по верхнему краю: 8.26…87.63 мм)." % (
                     y0, ", ".join("%.2f" % (x1 - float(first(fps[r], "at")[1])) for r in ("J1", "J2", "J3"))))
    jx = [it[2] for it in items if it[0] == "J4"]
    lo, hi = x1 - max(jx), x1 - min(jx)
    check(8.26 <= lo and hi <= 87.63, "J4 outside the overhang region: %.2f..%.2f" % (lo, hi))
    lines.append("- J4 (game/MIDI): выводы от %.2f до %.2f мм от правого края, внутри зоны выступа нижнего края." % (lo, hi))
    lines += ["", "Результат: " + ("ошибок нет." if not FAIL else "ЕСТЬ ОШИБКИ:\n\n" + "\n".join("- " + f for f in FAIL))]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
