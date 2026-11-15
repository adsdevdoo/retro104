#!/usr/bin/env python3
"""Independent checks of pc104-blank against the source documents (no KiCad API needed).

1. Pinout: symbol pin names vs PC/104 v2.6 Table 2 and Advantech PCM-3864 manual p. 67.
2. Geometry: every pad and hole of the saved .kicad_pcb vs PC/104 v2.6 Fig. 3/4 coordinates.
3. Electrically empty: one pad per net, only "unconnected-*" nets, holes without net.
4. Fabrication: Excellon PTH hits/diameters and Gerber Edge.Cuts extents vs the same expectations.

Writes hardware/pc104-blank/reports/pinout-check.md and fab-check.md; exit code 1 on any failure.
Usage: python tools/check_board.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc104_data as D  # noqa: E402
from sexpr import parse, find, first  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRJ = os.path.join(REPO, "hardware", "pc104-blank")
PCB = os.path.join(PRJ, "pc104-blank.kicad_pcb")
SYM = os.path.join(REPO, "hardware", "lib", "retro104.kicad_sym")
FAB = os.path.join(PRJ, "fabrication", "gerbers")
REPORTS = os.path.join(PRJ, "reports")
TOL = 0.001  # mm
FAIL = []


def check(ok, msg):
    if not ok:
        FAIL.append(msg)
    return ok


def board_outline(tree):
    xs, ys = [], []
    for g in find(tree, "gr_line"):
        if first(g, "layer")[1] == "Edge.Cuts":
            for k in ("start", "end"):
                p = first(g, k)
                xs.append(float(p[1]))
                ys.append(float(p[2]))
    return min(xs), min(ys), max(xs), max(ys)


def pcb_pads(tree):
    """{(ref, pad): dict(x, y, drill, size, net)} in board mm; footprints are not rotated here."""
    out = {}
    for fp in find(tree, "footprint"):
        at = first(fp, "at")
        check(len(at) < 4 or float(at[3]) == 0, "footprint rotated: %s" % at)
        fx, fy = float(at[1]), float(at[2])
        ref = [p[2] for p in find(fp, "property") if p[1] == "Reference"][0]
        lib = fp[1]
        for pad in find(fp, "pad"):
            pat = first(pad, "at")
            net = first(pad, "net")
            out[(str(ref), str(pad[1]))] = {
                "x": fx + float(pat[1]), "y": fy + float(pat[2]), "lib": str(lib),
                "drill": float(first(pad, "drill")[1]), "size": float(first(pad, "size")[1]),
                "shape": pad[3], "net": str(net[2]) if net else "",
            }
    return out


def symbol_pins():
    tree = parse(open(SYM, encoding="utf-8").read())
    pins = {}
    for sym in find(tree, "symbol"):
        for unit in find(sym, "symbol"):
            for pin in find(unit, "pin"):
                pins[str(first(pin, "number")[1])] = str(first(pin, "name")[1])
    return pins


def unbar(name):
    m = re.fullmatch(r"~\{(.+)\}", name)
    return m.group(1) + "*" if m else name


def main():
    tree = parse(open(PCB, encoding="utf-8").read())
    x0, y0, x1, y1 = board_outline(tree)
    w, h = x1 - x0, y1 - y0
    check(abs(w - D.BOARD_X_IN * D.IN) < TOL and abs(h - D.BOARD_Y_IN * D.IN) < TOL,
          "outline %.3f x %.3f mm" % (w, h))

    def to_in(x, y):  # board mm -> PC/104 Fig. 3 inches
        return (x1 - x) / D.IN, (y1 - y) / D.IN

    pads = pcb_pads(tree)
    sym = symbol_pins()
    rows_md = []
    nets_seen = {}
    n_ok = 0
    for pad, row, n, xi, yi, spec in D.pad_list("ABCD"):
        ref = "CN2" if row in "AB" else "CN1"
        p = pads.get((ref, pad))
        status = []
        if not check(p is not None, "missing pad %s.%s" % (ref, pad)):
            continue
        px, py = to_in(p["x"], p["y"])
        dx, dy = (px - xi) * D.IN, (py - yi) * D.IN
        pos_ok = check(abs(dx) < TOL and abs(dy) < TOL, "%s.%s off by %.4f/%.4f mm" % (ref, pad, dx, dy))
        check(abs(p["drill"] - D.CONNECTOR_DRILL_MM) < TOL and abs(p["size"] - D.CONNECTOR_PAD_MM) < TOL,
              "%s.%s drill/size %s/%s" % (ref, pad, p["drill"], p["size"]))
        check(p["net"].startswith("unconnected-"), "%s.%s has net %s" % (ref, pad, p["net"]))
        nets_seen.setdefault(p["net"], []).append(pad)
        sname = unbar(sym.get(pad, "?"))
        check(sname == spec, "symbol pin %s named %s, spec %s" % (pad, sname, spec))
        adv = D.ADVANTECH[row][n - D.first_pin(row)]
        a, s = D.normalize(adv), D.normalize(spec)
        if a == s and adv.replace(" ", "").replace("0V", "GND") != spec.replace("*", ""):
            note = "то же, другое имя" if adv.upper().replace(" ", "") not in ("0V",) else "0 V = GND"
        elif a == s:
            note = "совпадает"
        else:
            note = "**отличие**"
        if pad in D.KEY_PADS:
            note += "; ключ PC/104"
        if pos_ok:
            n_ok += 1
        rows_md.append("| %s | %s | %s | %.3f | %.3f | %s | %s %s %d: %s | %s |" % (
            ref, pad, "J1" if row in "AB" else "J2", xi, yi, spec,
            D.ADVANTECH_CN[row], D.ADVANTECH_ROW[row], n, adv, note))
    single = all(len(v) == 1 for v in nets_seen.values())
    check(single, "a net connects more than one pad")
    holes = [(k, v) for k, v in pads.items() if k[0].startswith("H")]
    hole_lines = []
    for i, (hx, hy) in enumerate(D.HOLES_IN):
        ref = "H%d" % (i + 1)
        p = pads.get((ref, ""))
        if not check(p is not None, "missing hole " + ref):
            continue
        px, py = to_in(p["x"], p["y"])
        ok = check(abs(px - hx) * D.IN < TOL and abs(py - hy) * D.IN < TOL, "%s at %.4f,%.4f in" % (ref, px, py))
        check(abs(p["drill"] - D.HOLE_DRILL_MM) < TOL and abs(p["size"] - D.HOLE_PAD_MM) < TOL, ref + " size")
        check(p["net"] == "", ref + " has a net")
        hole_lines.append("| %s | %.3f | %.3f | %.2f / %.2f | %s |" % (
            ref, hx, hy, p["drill"], p["size"], "совпадает" if ok else "ОШИБКА"))
    check(len(holes) == 4, "expected 4 mounting holes, found %d" % len(holes))

    diffs = [r for r in rows_md if "**отличие**" in r]
    md = ["# Сверка контактов CN1/CN2 (pc104-blank rev A)", "",
          "Сгенерировано `tools/check_board.py` по сохранённым `pc104-blank.kicad_pcb` и `retro104.kicad_sym`.",
          "Координаты X/Y — дюймы в системе PC/104 v2.6 рис. 3 (с. A-3): начало у края с шиной возле J1 pin 1,",
          "X — от края с разъёмами внутрь платы, Y — вдоль разъёмов от pin 1 к pin 32. Сигналы стандарта —",
          "табл. 2 (с. B-2); Advantech — руководство PCM-3864/3860 ed.1, прил. C, с. 67.", "",
          "## Итог", "",
          "- Контур по Edge.Cuts: %.3f × %.3f мм (стандарт 3.775 × 3.550 in = 95.885 × 90.170 мм)." % (w, h),
          "- Площадок на своих местах (допуск %.3f мм): %d из 104; отверстие %.2f мм, площадка %.2f мм." % (
              TOL, n_ok, D.CONNECTOR_DRILL_MM, D.CONNECTOR_PAD_MM),
          "- Имена выводов символов совпадают с табл. 2 PC/104 v2.6: %s." % (
              "да" if not any("symbol pin" in f for f in FAIL) else "НЕТ"),
          "- Каждая площадка — в собственной цепи `unconnected-*`, общих цепей нет: %s." % ("да" if single else "НЕТ"),
          "- Отличия руководства Advantech от стандарта: %d (B10 и C19, см. таблицу)." % len(diffs),
          "- Переименования из PC/104 v2.5 (IOCHCHK→IOCHK*, RESETDRV→RESET, ENDXFR→SRDY*, SYSCLK→BCLK,",
          "  MASTER→MASTER16*) и запись «0 V» вместо GND отличиями не считаются: это те же сигналы.",
          "- Нумерация Advantech: CN2 = PC/104 J1 (ряды A/B), CN1 = PC/104 J2; ряды C/D в руководстве",
          "  названы «Row A/Row B». На плате обозначения CN1/CN2 совпадают с хостом, номера площадок —",
          "  по стандарту (A1…B32, C0…D19).", "",
          "## Крепёжные отверстия", "",
          "| Обозн. | X, in | Y, in | Сверло / площадка, мм | Результат |", "|---|---|---|---|---|"] + hole_lines + [
          "", "## Контакты", "",
          "| CN | Площадка | PC/104 | X, in | Y, in | PC/104 v2.6 | Advantech (с. 67) | Сверка |",
          "|---|---|---|---|---|---|---|---|"] + rows_md + [
          "", "## Результат проверки", "",
          ("Ошибок нет." if not FAIL else "ОШИБКИ:\n\n" + "\n".join("- " + f for f in FAIL))]
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "pinout-check.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    fab_check(w, h)
    print("pinout-check: %d pads, %d holes, %d failures" % (n_ok, len(hole_lines), len(FAIL)))
    for f in FAIL:
        print("FAIL:", f)
    return 1 if FAIL else 0


def parse_excellon(path):
    tools, hits, cur = {}, [], None
    for line in open(path, encoding="ascii"):
        line = line.strip()
        m = re.fullmatch(r"T(\d+)C([\d.]+)", line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        m = re.fullmatch(r"T(\d+)", line)
        if m:
            cur = m.group(1)
            continue
        m = re.fullmatch(r"X(-?[\d.]+)Y(-?[\d.]+)", line)
        if m:
            hits.append((tools[cur], float(m.group(1)), float(m.group(2))))
    return hits


def gerber_extents(path):
    xs, ys = [], []
    for m in re.finditer(r"X(-?\d+)Y(-?\d+)D0[12]", open(path, encoding="ascii").read()):
        xs.append(int(m.group(1)) / 1e6)
        ys.append(int(m.group(2)) / 1e6)
    return min(xs), min(ys), max(xs), max(ys)


def fab_check(w, h):
    lines = ["# Проверка файлов производства (pc104-blank rev A)", "",
             "Сгенерировано `tools/check_board.py` по файлам в `fabrication/gerbers/` (не по PCB).", ""]
    gx0, gy0, gx1, gy1 = gerber_extents(os.path.join(FAB, "pc104-blank-Edge_Cuts.gm1"))
    ok = check(abs(gx0) < TOL and abs(gy0) < TOL and abs(gx1 - w) < TOL and abs(gy1 - h) < TOL,
               "Edge.Cuts gerber extents %.3f,%.3f..%.3f,%.3f" % (gx0, gy0, gx1, gy1))
    lines.append("- Edge.Cuts: от (%.3f; %.3f) до (%.3f; %.3f) мм, начало — левый нижний угол: %s." % (
        gx0, gy0, gx1, gy1, "совпадает с 95.885 × 90.170" if ok else "ОШИБКА"))
    hits = parse_excellon(os.path.join(FAB, "pc104-blank-PTH.drl"))
    npth = parse_excellon(os.path.join(FAB, "pc104-blank-NPTH.drl"))
    expected = {}
    for pad, row, n, xi, yi, _ in D.pad_list("ABCD"):
        expected[(round(xi * 1000), round(yi * 1000))] = ("pin " + pad, D.CONNECTOR_DRILL_MM)
    for i, (hx, hy) in enumerate(D.HOLES_IN):
        expected[(round(hx * 1000), round(hy * 1000))] = ("H%d" % (i + 1), D.HOLE_DRILL_MM)
    found = {}
    for dia, x, y in hits:
        xi, yi = (w - x) / D.IN, y / D.IN  # Excellon: origin bottom-left, Y up
        key = (round(xi * 1000), round(yi * 1000))
        exact = abs(xi * 1000 - key[0]) * D.IN / 1000 < TOL and abs(yi * 1000 - key[1]) * D.IN / 1000 < TOL
        check(exact and key in expected, "unexpected drill hit %.3f,%.3f" % (x, y))
        if key in expected:
            check(abs(dia - expected[key][1]) < TOL, "%s drilled %.3f" % (expected[key][0], dia))
            found[key] = dia
    missing = [v[0] for k, v in expected.items() if k not in found]
    check(not missing, "missing drill hits: %s" % missing)
    check(not npth, "NPTH file not empty")
    by_dia = {}
    for dia, _, _ in hits:
        by_dia[dia] = by_dia.get(dia, 0) + 1
    lines.append("- PTH Excellon: %s; всего %d отверстий, ожидалось %d; лишних и пропущенных нет: %s." % (
        ", ".join("%d × Ø%.2f мм" % (c, d) for d, c in sorted(by_dia.items())), len(hits), len(expected),
        "да" if not missing and len(hits) == len(expected) else "НЕТ"))
    lines.append("- Каждое отверстие из Excellon пересчитано в координаты PC/104 рис. 3 и найдено в таблице "
                 "стандарта (допуск %.3f мм)." % TOL)
    lines.append("- NPTH Excellon: %d отверстий (неметаллизированных отверстий в проекте нет)." % len(npth))
    flashes = len(re.findall(r"D03\*", open(os.path.join(FAB, "pc104-blank-F_Cu.gtl"), encoding="ascii").read()))
    flashes_b = len(re.findall(r"D03\*", open(os.path.join(FAB, "pc104-blank-B_Cu.gbl"), encoding="ascii").read()))
    check(flashes == 108 and flashes_b == 108, "copper flashes %d/%d" % (flashes, flashes_b))
    draws = len(re.findall(r"D01\*", open(os.path.join(FAB, "pc104-blank-F_Cu.gtl"), encoding="ascii").read()))
    check(draws == 0, "F.Cu contains %d draws (tracks)" % draws)
    lines.append("- Медь: F.Cu %d и B.Cu %d площадок (104 контакта + 4 отверстия), дорожек на F.Cu: %d." % (
        flashes, flashes_b, draws))
    lines += ["", "Результат: " + ("ошибок нет." if not FAIL else "ЕСТЬ ОШИБКИ, см. вывод скрипта.")]
    with open(os.path.join(REPORTS, "fab-check.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
