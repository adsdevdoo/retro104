#!/usr/bin/env python3
"""Generate hardware/pc104-audio: schematic (from tools/audio_design.py) and project files.

Every connected pin gets a short wire stub ending in a local net label, every unused pin a
no-connect flag, so the schematic reads as the netlist of audio_design.py. Run tools/generate.py
first (shared library). Usage: python tools/gen_audio.py [--force]
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_design as A  # noqa: E402
import generate as G  # noqa: E402
import symbols as S  # noqa: E402
from sexpr import Q, dump, uid  # noqa: E402

REPO = G.REPO
PRJ_NAME = "pc104-audio"
PRJ = os.path.join(REPO, "hardware", PRJ_NAME)
SCH_UUID = uid(PRJ_NAME + ":sch")
P = 2.54


def lib_defs():
    """name -> (sexpr node with retro104: prefix, [(number, x, y, angle)])."""
    out = {}
    for which, name in (("J1", "PC104_J1P1"), ("J2", "PC104_J2P2")):
        rows = "AB" if which == "J1" else "CD"
        pins = []
        for row in rows:
            for n in (G.D.J1_PINS if which == "J1" else G.D.J2_PINS):
                x, y = G.sym_pin_pos(which, row, n)
                pins.append(("%s%d" % (row, n), x, y, 0 if x < 0 else 180))
        out[name] = (G.connector_symbol(which, "retro104:"), pins)
    out["MountingHole_PC104"] = (G.hole_symbol("retro104:"), [])
    for s in S.audio_symbols():
        out[s.name] = (s.node("retro104:"), [(p[0], p[3], p[4], p[5]) for p in s.pins])
    return out


# Schematic placement (mm, A2 sheet). Small two-pin parts are laid out in columns.
BIG = {"CN2": (50.8, 45.72), "CN1": (50.8, 160.02), "U1": (190.5, 129.54), "U2": (309.88, 55.88),
       "U3": (309.88, 101.6), "JP1": (299.72, 137.16), "JP2": (330.2, 137.16), "J1": (563.88, 45.72),
       "J2": (563.88, 66.04), "J3": (563.88, 86.36), "J4": (563.88, 132.08),
       "H1": (495.3, 350.52), "H2": (520.7, 350.52), "H3": (546.1, 350.52), "H4": (571.5, 350.52)}
COLUMNS = [(360.68, 40.64), (424.18, 40.64), (487.68, 40.64), (360.68, 220.98), (424.18, 220.98)]
ROW = 10.16


def place_small(refs):
    pos = {}
    col, row = 0, 0
    for ref in refs:
        x, y0 = COLUMNS[col]
        pos[ref] = (x, y0 + row * ROW)
        row += 1
        if row >= 17:
            col, row = col + 1, 0
    return pos


def label_node(net, x, y, ang, key):
    just = {0: ["justify", "left", "bottom"], 180: ["justify", "right", "bottom"],
            90: ["justify", "left", "bottom"], 270: ["justify", "right", "bottom"]}[ang]
    return ["label", Q(net), ["at", round(x, 4), round(y, 4), ang], ["fields_autoplaced", "yes"],
            ["effects", ["font", ["size", 1.27, 1.27]], just], ["uuid", Q(uid(key))]]


def wire(x1, y1, x2, y2, key):
    return ["wire", ["pts", ["xy", round(x1, 4), round(y1, 4)], ["xy", round(x2, 4), round(y2, 4)]],
            ["stroke", ["width", 0], ["type", "default"]], ["uuid", Q(uid(key))]]


STUB = {0: (-P, 0, 180), 180: (P, 0, 0), 90: (0, P, 270), 270: (0, -P, 90)}  # outward dx, dy, label angle


def sch_prop(name, value, x, y, hide=False):
    eff = ["effects", ["font", ["size", 1.27, 1.27]]]
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value), ["at", round(x, 4), round(y, 4), 0], eff]


def main():
    defs = lib_defs()
    pin_net = {}
    for net, pins in A.NETS.items():
        for ref, pin in pins:
            assert (ref, pin) not in pin_net, (ref, pin)
            pin_net[(ref, pin)] = net
    nc = set(A.NC)
    small = [r for r in A.PARTS if r not in BIG]
    pos = dict(BIG)
    pos.update(place_small(small))

    used = sorted({p["sym"] for p in A.PARTS.values()} | {"PWR_FLAG"})
    sch = ["kicad_sch", ["version", 20250114], ["generator", Q("eeschema")], ["generator_version", Q("9.0")],
           ["uuid", Q(SCH_UUID)], ["paper", Q("A2")],
           ["title_block", ["title", Q("retro104 pc104-audio: PC/104 sound card, ESS ES1868F")],
            ["date", Q("2026-11-15")], ["rev", Q("A")], ["company", Q("retro104")],
            ["comment", 1, Q("Circuit: ESS ES1868 data sheet Appendix B (Fig. 28, 29, 31); decisions: docs/audio-options.md")],
            ["comment", 2, Q("Line out only, line in + mic, game/MIDI 2x8 header, IRQ/DMA as ESS reference")],
            ["comment", 3, Q("Not tested in hardware")]],
           ["lib_symbols"] + [defs[name][0] for name in used]]
    for ref, p in A.PARTS.items():
        node, pins = defs[p["sym"]]
        x, y = pos[ref]
        value = p["value"]
        fp = p["fp"] or {"R": S.FP + "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder",
                         "C": S.FP + "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"}.get(p["sym"])
        if fp is None:
            fp = [q for q in node if isinstance(q, list) and q[0] == "property" and q[1] == "Footprint"][0][2]
        su = uid(PRJ_NAME + ":sym:" + ref)
        is_hole = p["sym"] == "MountingHole_PC104"
        no_bom = p["sym"] in ("MountingHole_PC104", "SolderJumper_3_Bridged12")
        inst = ["symbol", ["lib_id", Q("retro104:" + p["sym"])], ["at", x, y, 0], ["unit", 1],
                ["exclude_from_sim", "yes" if is_hole else "no"], ["in_bom", "no" if no_bom else "yes"],
                ["on_board", "yes"], ["dnp", "no"], ["uuid", Q(su)],
                sch_prop("Reference", ref, x, y - 3.81 if p["sym"] in ("R", "C", "CP", "FerriteBead", "Crystal") else y - 6.35),
                sch_prop("Value", value, x, y + 3.81 if p["sym"] in ("R", "C", "CP", "FerriteBead", "Crystal") else y + 6.35),
                sch_prop("Footprint", fp, x, y, True), sch_prop("Datasheet", "", x, y, True),
                sch_prop("Description", p["note"], x, y, True)]
        if p["mpn"]:
            inst.append(sch_prop("MPN", p["mpn"], x, y, True))
        for num, *_ in pins:
            inst.append(["pin", Q(num), ["uuid", Q(uid("%s:pin:%s:%s" % (PRJ_NAME, ref, num)))]])
        inst.append(["instances", ["project", Q(PRJ_NAME), ["path", Q("/" + SCH_UUID), ["reference", Q(ref)], ["unit", 1]]]])
        sch.append(inst)
        for num, px, py, ang in pins:
            sx, sy = x + px, y - py
            key = "%s:%s:%s" % (PRJ_NAME, ref, num)
            if (ref, num) in nc:
                sch.append(["no_connect", ["at", round(sx, 4), round(sy, 4)], ["uuid", Q(uid(key + ":nc"))]])
                continue
            net = pin_net.get((ref, num))
            if net is None:
                raise SystemExit("pin %s.%s neither connected nor marked NC" % (ref, num))
            dx, dy, la = STUB[ang]
            sch.append(wire(sx, sy, sx + dx, sy + dy, key + ":w"))
            sch.append(label_node(net, sx + dx, sy + dy, la, key + ":l"))
    # power flags
    node, _ = defs["PWR_FLAG"]
    for i, net in enumerate(A.FLAGGED_NETS):
        x, y = 487.68 + i * 12.7, 335.28
        ref = "#FLG%02d" % (i + 1)
        sch.append(["symbol", ["lib_id", Q("retro104:PWR_FLAG")], ["at", x, y, 0], ["unit", 1],
                    ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "no"], ["dnp", "no"],
                    ["uuid", Q(uid(PRJ_NAME + ":flag:" + net))],
                    sch_prop("Reference", ref, x, y - 3.81, True), sch_prop("Value", "PWR_FLAG", x, y - 5.08),
                    sch_prop("Footprint", "", x, y, True), sch_prop("Datasheet", "", x, y, True),
                    sch_prop("Description", "", x, y, True),
                    ["pin", Q("1"), ["uuid", Q(uid(PRJ_NAME + ":flagpin:" + net))]],
                    ["instances", ["project", Q(PRJ_NAME), ["path", Q("/" + SCH_UUID), ["reference", Q(ref)], ["unit", 1]]]]])
        sch.append(wire(x, y, x, y + P, PRJ_NAME + ":flagw:" + net))
        sch.append(label_node(net, x, y + P, 270, PRJ_NAME + ":flagl:" + net))
    notes = (
        "pc104-audio rev A — звуковая карта PC/104 на ESS ES1868F (этап 2).\n"
        "Схема — типовое включение ESS (даташит ES1868, прил. B: рис. 28, 29, 31) с решениями владельца:\n"
        "только линейный выход, вход Line и Mic, без CD-in, IDE, модема, wavetable и кнопок громкости;\n"
        "VDDA от +5 В через ферритовую бусину FB1 (вместо 78L05 от +12 В).\n"
        "IRQA..F = IRQ 9, 5, 7, 10, 11, 12; DRQA..D = 0, 1, 3, 5 — как у ESS и в EEPROM типовых карт.\n"
        "A15..A12 + AEN декодирует U2 (74HCT138), как U2 74LS138 в рис. 28.\n"
        "J4 — game/MIDI 2x8 под стандартный кабель на DB-15 (раскладка — National AN-1130, с. 1).\n"
        "JP1/JP2 по умолчанию 1-2 (H) — данные PnP из EEPROM U3; 2-3 (L) — из внутреннего ПЗУ ES1868.\n"
        "Не проверялось в железе."
    )
    sch.append(["text", Q(notes), ["exclude_from_sim", "no"], ["at", 360.68, 375.92, 0],
                ["effects", ["font", ["size", 1.778, 1.778]], ["justify", "left", "bottom"]],
                ["uuid", Q(uid(PRJ_NAME + ":notes"))]])
    sch.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
    sch.append(["embedded_fonts", "no"])
    G.write(os.path.join(PRJ, PRJ_NAME + ".kicad_sch"), dump(sch))

    pro = os.path.join(PRJ, PRJ_NAME + ".kicad_pro")
    if not os.path.exists(pro) or "--force" in sys.argv:
        d = json.loads(G.project_file())
        d["meta"]["filename"] = PRJ_NAME + ".kicad_pro"
        d["sheets"] = [[SCH_UUID, "Root"]]
        G.write(pro, json.dumps(d, indent=2))
    sym, fp = G.lib_tables()
    G.write(os.path.join(PRJ, "sym-lib-table"), sym)
    G.write(os.path.join(PRJ, "fp-lib-table"), fp)


if __name__ == "__main__":
    main()
