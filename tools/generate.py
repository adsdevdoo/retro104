#!/usr/bin/env python3
"""Generate the shared PC/104 library and the pc104-blank schematic/project (KiCad 9).

Writes:
  hardware/lib/retro104.kicad_sym           symbols PC104_J1P1, PC104_J2P2, MountingHole_PC104
  hardware/lib/retro104.pretty/*.kicad_mod   bus connector and mounting-hole footprints
  hardware/lib/3d/*.wrl                      illustrative VRML models (see docs/models.md)
  hardware/pc104-blank/pc104-blank.kicad_sch, .kicad_pro, sym-lib-table, fp-lib-table

All geometry comes from tools/pc104_data.py (PC/104 v2.6 + Samtec ESQ documents).
The PCB is built afterwards by tools/build_board.py (KiCad Python).

Usage: python tools/generate.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc104_data as D  # noqa: E402
from sexpr import Q, dump, uid  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(REPO, "hardware", "lib")
PRJ_NAME = "pc104-blank"
PRJ = os.path.join(REPO, "hardware", PRJ_NAME)

FP_J1 = "PC104_J1P1_2x32_P2.54mm_Stackthrough"
FP_J2 = "PC104_J2P2_2x20_P2.54mm_Stackthrough"
FP_H = "PC104_MountingHole_3.18mm_Pad6.35mm"
MODEL_DIR = "${KIPRJMOD}/../lib/3d/"
P = 2.54
PAD = D.CONNECTOR_PAD_MM
DRILL = D.CONNECTOR_DRILL_MM
MPN = {"J1": "ESQ-132-39-G-D", "J2": "ESQ-120-39-G-D"}
DS_SAMTEC = "${KIPRJMOD}/../../docs/datasheets/samtec-esw-esq-elevated-sockets-f226-rev16jun26.pdf"
DS_PC104 = "${KIPRJMOD}/../../docs/datasheets/pc104-specification-v2.6-2008.pdf"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    print("wrote", os.path.relpath(path, REPO))


# ----------------------------------------------------------------------------- local pad geometry
def j1_local(row, n):
    """J1 footprint coordinates (origin = A1, KiCad y down, board orientation of PC/104 Fig. 3)."""
    x = (D.J1_ROW_X_IN["A"] - D.J1_ROW_X_IN[row]) * D.IN
    y = -(D.j1_y_in(n) - D.j1_y_in(1)) * D.IN
    return x, y


def j2_local(row, n):
    """J2 footprint coordinates (origin = C0)."""
    x = (D.J2_ROW_X_IN["C"] - D.J2_ROW_X_IN[row]) * D.IN
    y = -(D.j2_y_in(n) - D.j2_y_in(0)) * D.IN
    return x, y


def body_local(which):
    """Connector body rectangle (x0, y0, x1, y1) in footprint coordinates, PC/104 Fig. 4."""
    half = D.BODY_W_IN / 2 * D.IN
    end = D.BODY_END_IN * D.IN
    if which == "J1":
        xa, _ = j1_local("A", 1)
        xb, _ = j1_local("B", 1)
        _, ytop = j1_local("A", 32)
    else:
        xa, _ = j2_local("C", 0)
        xb, _ = j2_local("D", 0)
        _, ytop = j2_local("C", 19)
    cx = (xa + xb) / 2
    return cx - half, ytop - end, cx + half, end


# ----------------------------------------------------------------------------- footprint helpers
def font(size=1.0, thick=0.15, mirror=False, justify=None):
    eff = ["effects", ["font", ["size", size, size], ["thickness", thick]]]
    j = []
    if justify:
        j.append(justify)
    if mirror:
        j.append("mirror")
    if j:
        eff.append(["justify"] + j)
    return eff


def fp_prop(name, value, x, y, layer, key, hide=False, size=1.0, thick=0.15, rot=0):
    node = ["property", Q(name), Q(value), ["at", x, y, rot], ["layer", Q(layer)]]
    if hide:
        node.append(["hide", "yes"])
    node += [["uuid", Q(uid(key))], font(size, thick)]
    return node


def fp_text(text, x, y, layer, key, size=1.0, thick=0.15, rot=0, justify=None):
    mirror = layer.startswith("B.")
    return ["fp_text", "user", Q(text), ["at", x, y, rot], ["layer", Q(layer)],
            ["uuid", Q(uid(key))], font(size, thick, mirror, justify)]


def fp_line(x1, y1, x2, y2, layer, width, key):
    return ["fp_line", ["start", x1, y1], ["end", x2, y2],
            ["stroke", ["width", width], ["type", "solid"]], ["layer", Q(layer)], ["uuid", Q(uid(key))]]


def fp_rect(x1, y1, x2, y2, layer, width, key):
    return ["fp_rect", ["start", x1, y1], ["end", x2, y2],
            ["stroke", ["width", width], ["type", "solid"]], ["fill", "no"], ["layer", Q(layer)],
            ["uuid", Q(uid(key))]]


def fp_circle(r, layer, width, key):
    return ["fp_circle", ["center", 0, 0], ["end", r, 0],
            ["stroke", ["width", width], ["type", "solid"]], ["fill", "no"], ["layer", Q(layer)],
            ["uuid", Q(uid(key))]]


def fp_tri(tip_x, tip_y, direction, layer, key, size=0.9):
    """Filled pin-1 arrow; direction +1 points to +x, -1 to -x."""
    h = size / 2
    bx = tip_x - direction * size * 0.8
    pts = [(tip_x, tip_y), (bx, tip_y - h), (bx, tip_y + h)]
    return ["fp_poly", ["pts"] + [["xy", x, y] for x, y in pts],
            ["stroke", ["width", 0.1], ["type", "solid"]], ["fill", "yes"], ["layer", Q(layer)],
            ["uuid", Q(uid(key))]]


def model(path, hide=False):
    node = ["model", Q(MODEL_DIR + path)]
    if hide:
        node.append(["hide", "yes"])
    node += [["offset", ["xyz", 0, 0, 0]], ["scale", ["xyz", 1, 1, 1]], ["rotate", ["xyz", 0, 0, 0]]]
    return node


def tht_pad(num, x, y, square, key):
    shape = "rect" if square else "circle"
    return ["pad", Q(num), "thru_hole", shape, ["at", x, y], ["size", PAD, PAD], ["drill", DRILL],
            ["layers", Q("*.Cu"), Q("*.Mask")], ["remove_unused_layers", "no"], ["uuid", Q(uid(key))]]


def footprint_header(name, descr, tags):
    return ["footprint", Q(name), ["version", 20241229], ["generator", Q("retro104")],
            ["generator_version", Q("1.0")], ["layer", Q("F.Cu")], ["descr", Q(descr)], ["tags", Q(tags)]]


def connector_footprint(which):
    name = FP_J1 if which == "J1" else FP_J2
    rows = "AB" if which == "J1" else "CD"
    local = j1_local if which == "J1" else j2_local
    pins = D.J1_PINS if which == "J1" else D.J2_PINS
    first, last = pins[0], pins[-1]
    x0, y0, x1, y1 = body_local(which)
    k = name + ":"
    if which == "J1":
        descr = ("PC/104 16-bit bus J1/P1, rows A/B, 2x32, 2.54 mm. Geometry: PC/104 Specification v2.6 "
                 "Fig. 3/4. Origin = A1, orientation as Fig. 3 (bus edge to +x, pin 32 to -y). "
                 "Holes 1.02 mm per Samtec ESQ-SDT. Part: Samtec ESQ-132-39-G-D (stackthrough). "
                 "B10 is the PC/104 key location (no pin on P1, plugged hole on J1). "
                 "Advantech PCM-3864/3860 name: CN2.")
    else:
        descr = ("PC/104 16-bit bus J2/P2, rows C/D, 2x20 (pins 0..19), 2.54 mm. Geometry: PC/104 "
                 "Specification v2.6 Fig. 3/4: C0/D0 0.800 in from J1 pin 1, rows at 0.100 in towards "
                 "the bus edge. Origin = C0. Silk edge towards J1/P1 is shared with the J1/P1 outline. "
                 "Part: Samtec ESQ-120-39-G-D (stackthrough). C19 is the PC/104 key location. "
                 "Advantech PCM-3864/3860 name: CN1 (its Row A/Row B = C/D).")
    fp = footprint_header(name, descr, "PC/104 PC104 ISA stackthrough ESQ")
    fp.append(fp_prop("Reference", "REF**", (x0 + x1) / 2, y1 + 4.5, "F.SilkS", k + "ref", size=1.5, thick=0.2))
    fp.append(fp_prop("Value", name, (x0 + x1) / 2, y0 - 2, "F.Fab", k + "val"))
    fp.append(fp_prop("Datasheet", "", 0, 0, "F.Fab", k + "ds", hide=True))
    fp.append(fp_prop("Description", "", 0, 0, "F.Fab", k + "de", hide=True))
    fp.append(["attr", "through_hole"])
    # fabrication: exact body from Fig. 4
    fp.append(fp_rect(x0, y0, x1, y1, "F.Fab", 0.1, k + "fab"))
    fp.append(fp_text("${REFERENCE}", (x0 + x1) / 2, (y0 + y1) / 2, "F.Fab", k + "fabref", rot=90))
    # courtyard: body + 0.05 mm (J1 and J2 bodies are only 0.127 mm apart by the standard)
    fp.append(fp_rect(x0 - 0.05, y0 - 0.05, x1 + 0.05, y1 + 0.05, "F.CrtYd", 0.05, k + "crt"))
    # silkscreen outline 0.2 mm outside the body
    s = 0.2
    if which == "J1":
        fp.append(fp_rect(x0 - s, y0 - s, x1 + s, y1 + s, "F.SilkS", 0.15, k + "silk"))
    else:
        # The inner edge is the J1/P1 outline (bodies are 0.127 mm apart, Fig. 4); stop 0.18 mm short
        # of that line so the two footprints keep the 0.15 mm silk clearance.
        xl = x0 + 0.40
        fp.append(fp_line(xl, y1 + s, x1 + s, y1 + s, "F.SilkS", 0.15, k + "s1"))
        fp.append(fp_line(x1 + s, y1 + s, x1 + s, y0 - s, "F.SilkS", 0.15, k + "s2"))
        fp.append(fp_line(x1 + s, y0 - s, xl, y0 - s, "F.SilkS", 0.15, k + "s3"))
    # row letters at both ends
    for row in rows:
        xr, _ = local(row, first)
        fp.append(fp_text(row, xr, y1 + s + 1.0, "F.SilkS", k + "rl" + row))
        fp.append(fp_text(row, xr, y0 - s - 1.0, "F.SilkS", k + "rh" + row))
    # pin numbers and pin-1 arrow on the outer side (J1: -x side, J2: +x side)
    side = -1 if which == "J1" else 1
    xo = (x0 - s) if which == "J1" else (x1 + s)
    tip = xo + side * 0.2
    num_x = xo + side * 1.95
    ticks = [first, 10, 20, last] if which == "J1" else [first, 10, last]
    for layer in ("F.SilkS", "B.SilkS"):
        fp.append(fp_tri(tip, 0, -side, layer, k + "tri" + layer))
        for n in ticks:
            _, yn = local(rows[0], n)
            fp.append(fp_text(str(n), num_x + side * (0.3 if n >= 10 else 0), yn, layer,
                              k + "n%d%s" % (n, layer)))
    # key location note on the fabrication layer
    key_pad = "B10" if which == "J1" else "C19"
    kx, ky = local(key_pad[0], int(key_pad[1:]))
    fp.append(fp_text("KEY " + key_pad, kx + side * 7.5 if which == "J1" else kx, ky if which == "J1" else y0 - 3.0,
                      "F.Fab", k + "key", size=0.8, thick=0.12))
    for row in rows:
        for n in pins:
            x, y = local(row, n)
            pad = "%s%d" % (row, n)
            fp.append(tht_pad(pad, x, y, (row, n) == (rows[0], first), k + pad))
    fp.append(["embedded_fonts", "no"])
    fp.append(model("Samtec_%s_illustrative.wrl" % MPN[which]))
    fp.append(model("PC104_host_%s_socket_mating_reference.wrl" % which, hide=True))
    return name, dump(fp)


def hole_footprint():
    name = FP_H
    k = name + ":"
    fp = footprint_header(
        name,
        "PC/104 mounting hole: 0.125 in (3.18 mm) plated hole, 0.250 in (6.35 mm) pad, "
        "PC/104 Specification v2.6 Fig. 3. No net (electrically empty).",
        "PC/104 mounting hole standoff")
    fp.append(fp_prop("Reference", "REF**", 0, -4.2, "F.Fab", k + "ref"))
    fp.append(fp_prop("Value", name, 0, 4.2, "F.Fab", k + "val"))
    fp.append(fp_prop("Datasheet", "", 0, 0, "F.Fab", k + "ds", hide=True))
    fp.append(fp_prop("Description", "", 0, 0, "F.Fab", k + "de", hide=True))
    fp.append(["attr", "exclude_from_pos_files", "exclude_from_bom"])
    fp.append(fp_circle(D.HOLE_PAD_MM / 2, "F.Fab", 0.1, k + "fab"))
    fp.append(fp_circle(D.HOLE_PAD_MM / 2 + 0.25, "F.CrtYd", 0.05, k + "crt"))
    fp.append(["pad", Q(""), "thru_hole", "circle", ["at", 0, 0], ["size", D.HOLE_PAD_MM, D.HOLE_PAD_MM],
               ["drill", D.HOLE_DRILL_MM], ["layers", Q("*.Cu"), Q("*.Mask")],
               ["remove_unused_layers", "no"], ["uuid", Q(uid(k + "pad"))]])
    fp.append(["embedded_fonts", "no"])
    fp.append(model("PC104_standoff_0.600in_illustrative.wrl", hide=True))
    return name, dump(fp)


# ----------------------------------------------------------------------------- VRML models
class Mesh:
    def __init__(self):
        self.pts, self.faces = [], []

    def add(self, pts, faces):
        base = len(self.pts)
        self.pts += pts
        self.faces += [[base + i for i in f] for f in faces]

    def box(self, x0, x1, y0, y1, z0, z1):
        """Footprint coordinates (mm, y down) -> stored as model coordinates later."""
        p = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [3, 0, 4, 7], [1, 2, 6, 5]]
        self.add(p, f)

    def prism(self, r, n, z0, z1, phase=0.0):
        import math
        ring0 = [(r * math.cos(phase + 2 * math.pi * i / n), r * math.sin(phase + 2 * math.pi * i / n), z0)
                 for i in range(n)]
        ring1 = [(x, y, z1) for x, y, _ in ring0]
        f = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
        f += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
        self.add(ring0 + ring1, f)


def vrml(title, info, shapes):
    """shapes: [(Mesh, (r, g, b))]. KiCad VRML unit = 0.1 inch; model y = -footprint y."""
    out = ["#VRML V2.0 utf8", 'WorldInfo { title "%s" info [ %s ] }' % (title, ", ".join('"%s"' % i for i in info))]
    for mesh, (r, g, b) in shapes:
        pts = ", ".join("%.5f %.5f %.5f" % (x / 2.54, -y / 2.54, z / 2.54) for x, y, z in mesh.pts)
        idx = ", ".join(",".join(str(i) for i in reversed(f)) + ",-1" for f in mesh.faces)  # y flip mirrors winding
        out.append("Shape {\n appearance Appearance { material Material { diffuseColor %.3f %.3f %.3f "
                   "specularColor 0.2 0.2 0.2 shininess 0.3 } }\n geometry IndexedFaceSet {\n  solid FALSE\n"
                   "  coord Coordinate { point [ %s ] }\n  coordIndex [ %s ]\n }\n}" % (r, g, b, pts, idx))
    return "\n".join(out)


BLACK = (0.06, 0.06, 0.06)
OPEN = (0.50, 0.50, 0.50)
GOLD = (0.85, 0.65, 0.20)
HOST = (0.10, 0.13, 0.32)
STEEL = (0.75, 0.75, 0.78)


def connector_models(which):
    rows = "AB" if which == "J1" else "CD"
    local = j1_local if which == "J1" else j2_local
    pins = D.J1_PINS if which == "J1" else D.J2_PINS
    x0, y0, x1, y1 = body_local(which)
    pos = [local(r, n) for r in rows for n in pins]
    h, t, sq = D.BODY_H_MM, D.TAIL_MM, D.TAIL_SQ_MM
    # stackthrough connector on this board
    body, opening, tails = Mesh(), Mesh(), Mesh()
    body.box(x0, x1, y0, y1, 0, h)
    for x, y in pos:
        opening.box(x - 0.5, x + 0.5, y - 0.5, y + 0.5, h, h + 0.03)
        tails.box(x - sq / 2, x + sq / 2, y - sq / 2, y + sq / 2, -t, 0.02)
    info = ["ILLUSTRATIVE model generated by tools/generate.py, not a Samtec model",
            "Body %.3f x %.3f x %.2f mm (PC/104 v2.6 Fig. 4, Samtec ESQ lead style -39 B=.435)" % (x1 - x0, y1 - y0, h),
            "Tails %.2f mm square, %.2f mm below the body (Samtec ESQ -39 A=.480)" % (sq, t)]
    stack = vrml("Samtec %s (illustrative)" % MPN[which], info,
                 [(body, BLACK), (opening, OPEN), (tails, GOLD)])
    # host socket at the PC/104 stack distance below this board (mating reference only)
    zb = -(1.6 + D.STANDOFF_MM)
    hbody, hopen = Mesh(), Mesh()
    hbody.box(x0, x1, y0, y1, zb, zb + h)
    for x, y in pos:
        hopen.box(x - 0.5, x + 0.5, y - 0.5, y + 0.5, zb + h, zb + h + 0.03)
    hinfo = ["MATING REFERENCE ONLY, not part of this board and not in the BOM",
             "Female PC/104 %s socket of the host (PCM-3864 %s) at 0.600 in stack spacing" % (which, D.CN_OF_J[which]),
             "Body height .435 in per PC/104 v2.6 Fig. 4; host top surface at z=%.2f mm" % zb]
    host = vrml("Host %s socket (mating reference)" % which, hinfo, [(hbody, HOST), (hopen, OPEN)])
    return stack, host


def standoff_model():
    zb = -(1.6 + D.STANDOFF_MM)
    st, head = Mesh(), Mesh()
    st.prism(4.76 / 3 ** 0.5, 6, zb, -1.6)  # 3/16 in across flats hex
    head.prism(2.75, 20, 0, 2.0)
    info = ["ILLUSTRATIVE: 0.600 in (15.24 mm) standoff per PC/104 v2.6 Fig. 7 and screw head",
            "Not part of this board; hidden by default, shown only in the mating render"]
    return vrml("PC/104 standoff 0.600 in (illustrative)", info, [(st, STEEL), (head, STEEL)])


# ----------------------------------------------------------------------------- symbols
def sym_prop(name, value, x, y, hide=False, key=""):
    eff = ["effects", ["font", ["size", 1.27, 1.27]]]
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value), ["at", x, y, 0], eff]


def sym_pin(name, number, x, y, angle):
    return ["pin", "passive", "line", ["at", x, y, angle], ["length", 3.81],
            ["name", Q(name), ["effects", ["font", ["size", 1.27, 1.27]]]],
            ["number", Q(number), ["effects", ["font", ["size", 1.27, 1.27]]]]]


SYM_PIN_X = 13.97


def sym_pin_pos(which, row, n):
    """Pin connection point in symbol coordinates (y up)."""
    first = 1 if which == "J1" else 0
    left = row in "AC"
    return (-SYM_PIN_X if left else SYM_PIN_X), -(n - first) * P


def connector_symbol(which, prefix=""):
    name = "PC104_J1P1" if which == "J1" else "PC104_J2P2"
    rows = "AB" if which == "J1" else "CD"
    pins = D.J1_PINS if which == "J1" else D.J2_PINS
    bottom = -(len(pins) - 1) * P - P
    desc = ("PC/104 16-bit bus %s, rows %s/%s. Pin names: PC/104 Specification v2.6 Table 2. "
            "Advantech PCM-3864/3860 calls this connector %s." % (
                "J1/P1" if which == "J1" else "J2/P2", rows[0], rows[1], D.CN_OF_J[which]))
    sym = ["symbol", Q(prefix + name), ["pin_names", ["offset", 1.016]], ["exclude_from_sim", "no"],
           ["in_bom", "yes"], ["on_board", "yes"],
           sym_prop("Reference", "CN", 0, 5.08), sym_prop("Value", name, 0, bottom - 2.54),
           sym_prop("Footprint", "retro104:" + (FP_J1 if which == "J1" else FP_J2), 0, 0, True),
           sym_prop("Datasheet", DS_PC104, 0, 0, True), sym_prop("Description", desc, 0, 0, True),
           sym_prop("ki_keywords", "PC/104 PC104 ISA bus connector", 0, 0, True)]
    body = ["symbol", Q(name + "_0_1"),
            ["rectangle", ["start", -10.16, P], ["end", 10.16, bottom],
             ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]]
    pin_unit = ["symbol", Q(name + "_1_1")]
    for row in rows:
        for i, sname in enumerate(D.SPEC[row]):
            n = i + D.first_pin(row)
            x, y = sym_pin_pos(which, row, n)
            pin_unit.append(sym_pin(D.kicad_pin_name(sname), "%s%d" % (row, n), x, y, 0 if x < 0 else 180))
    sym += [body, pin_unit, ["embedded_fonts", "no"]]
    return sym


def hole_symbol(prefix=""):
    return ["symbol", Q(prefix + "MountingHole_PC104"), ["pin_names", ["offset", 1.016], ["hide", "yes"]],
            ["exclude_from_sim", "yes"], ["in_bom", "no"], ["on_board", "yes"],
            sym_prop("Reference", "H", 0, 5.08), sym_prop("Value", "MountingHole_PC104", 0, 3.175),
            sym_prop("Footprint", "retro104:" + FP_H, 0, 0, True),
            sym_prop("Datasheet", DS_PC104, 0, 0, True),
            sym_prop("Description", "PC/104 mounting hole, 3.18 mm plated, 6.35 mm pad, no net", 0, 0, True),
            ["symbol", Q("MountingHole_PC104_0_1"),
             ["circle", ["center", 0, 0], ["radius", 1.27], ["stroke", ["width", 1.27], ["type", "default"]],
              ["fill", ["type", "none"]]]],
            ["embedded_fonts", "no"]]


def symbol_library():
    import symbols
    lib = ["kicad_symbol_lib", ["version", 20241209], ["generator", Q("retro104")], ["generator_version", Q("1.0")],
           connector_symbol("J1"), connector_symbol("J2"), hole_symbol()]
    lib += [s.node() for s in symbols.audio_symbols()]
    return dump(lib)


# ----------------------------------------------------------------------------- schematic
SCH_UUID = uid("pc104-blank:sch")
PLACEMENT = {
    # ref: (lib symbol, value, footprint, x, y)
    "CN2": ("PC104_J1P1", MPN["J1"], FP_J1, 88.9, 50.8),
    "CN1": ("PC104_J2P2", MPN["J2"], FP_J2, 170.18, 50.8),
    "H1": ("MountingHole_PC104", "MountingHole_3.18mm", FP_H, 228.6, 50.8),
    "H2": ("MountingHole_PC104", "MountingHole_3.18mm", FP_H, 228.6, 60.96),
    "H3": ("MountingHole_PC104", "MountingHole_3.18mm", FP_H, 228.6, 71.12),
    "H4": ("MountingHole_PC104", "MountingHole_3.18mm", FP_H, 228.6, 81.28),
}
# PC/104 position (inches, Fig. 3) of each hole, matched in build_board.py
HOLE_OF_REF = {"H1": D.HOLES_IN[0], "H2": D.HOLES_IN[1], "H3": D.HOLES_IN[2], "H4": D.HOLES_IN[3]}


def sch_prop(name, value, x, y, hide=False, justify=None):
    eff = ["effects", ["font", ["size", 1.27, 1.27]]]
    if justify:
        eff.append(["justify", justify])
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value), ["at", x, y, 0], eff]


def schematic():
    lib_syms = ["lib_symbols", connector_symbol("J1", "retro104:"), connector_symbol("J2", "retro104:"),
                hole_symbol("retro104:")]
    sch = ["kicad_sch", ["version", 20250114], ["generator", Q("eeschema")], ["generator_version", Q("9.0")],
           ["uuid", Q(SCH_UUID)], ["paper", Q("A3")],
           ["title_block", ["title", Q("retro104 pc104-blank: PC/104 mating board (no circuits)")],
            ["date", Q("2026-11-15")], ["rev", Q("A")], ["company", Q("retro104")],
            ["comment", 1, Q("Stage 1: mechanical mating board for Advantech PCM-3864/3860 Rev.A1 CN1/CN2")],
            ["comment", 2, Q("Pin names: PC/104 Specification v2.6 Table 2. All pins intentionally not connected")],
            ["comment", 3, Q("Not tested in hardware")]],
           lib_syms]
    for ref, (sym, value, fpn, x, y) in PLACEMENT.items():
        which = "J1" if sym == "PC104_J1P1" else "J2" if sym == "PC104_J2P2" else None
        su = uid("pc104-blank:sym:" + ref)
        node = ["symbol", ["lib_id", Q("retro104:" + sym)], ["at", x, y, 0], ["unit", 1],
                ["exclude_from_sim", "no" if which else "yes"], ["in_bom", "yes" if which else "no"],
                ["on_board", "yes"], ["dnp", "no"], ["uuid", Q(su)]]
        if which:
            npins = len(D.J1_PINS if which == "J1" else D.J2_PINS)
            node += [sch_prop("Reference", ref, x, y - 5.08),
                     sch_prop("Value", value, x, y + (npins - 1) * P + 5.08),
                     sch_prop("Footprint", "retro104:" + fpn, x, y, True),
                     sch_prop("Datasheet", DS_SAMTEC, x, y, True),
                     sch_prop("Description", "PC/104 %s stackthrough, Samtec %s; Advantech PCM-3864 name %s" % (
                         "J1/P1 (A/B)" if which == "J1" else "J2/P2 (C/D)", value, ref), x, y, True),
                     sch_prop("Manufacturer", "Samtec", x, y, True),
                     sch_prop("MPN", value, x, y, True)]
            rows = "AB" if which == "J1" else "CD"
            for row in rows:
                for n in (D.J1_PINS if which == "J1" else D.J2_PINS):
                    node.append(["pin", Q("%s%d" % (row, n)), ["uuid", Q(uid("pc104-blank:pin:%s:%s%d" % (ref, row, n)))]])
        else:
            node += [sch_prop("Reference", ref, x + 2.54, y - 1.27, justify="left"),
                     sch_prop("Value", value, x + 2.54, y + 1.27, justify="left"),
                     sch_prop("Footprint", "retro104:" + fpn, x, y, True),
                     sch_prop("Datasheet", DS_PC104, x, y, True),
                     sch_prop("Description", "PC/104 mounting hole, no net", x, y, True)]
        node.append(["instances", ["project", Q(PRJ_NAME), ["path", Q("/" + SCH_UUID), ["reference", Q(ref)], ["unit", 1]]]])
        sch.append(node)
        if which:
            rows = "AB" if which == "J1" else "CD"
            for row in rows:
                for n in (D.J1_PINS if which == "J1" else D.J2_PINS):
                    px, py = sym_pin_pos(which, row, n)
                    sch.append(["no_connect", ["at", round(x + px, 4), round(y - py, 4)],
                                ["uuid", Q(uid("pc104-blank:nc:%s:%s%d" % (ref, row, n)))]])
    notes = (
        "Пустая механическая плата-ответка PC/104 (этап 1). Электрических цепей нет:\n"
        "все контакты CN1/CN2 отмечены как неподключённые, отверстия H1-H4 без цепи.\n"
        "Имена выводов: PC/104 Specification v2.6, Table 2 (p. B-2).\n"
        "Advantech PCM-3864/3860 (руководство ed.1, с. 67): CN2 = PC/104 J1 (ряды A/B, 1-32),\n"
        "CN1 = PC/104 J2 (ряды C/D, 0-19; в руководстве названы Row A/Row B).\n"
        "Отличия Advantech: B10 = GND (в стандарте KEY), C19 = N/C (KEY).\n"
        "Разъёмы: Samtec ESQ-132-39-G-D и ESQ-120-39-G-D (stackthrough, штыри вниз в гнёзда хоста).\n"
        "Это не аудиокарта. В железе не проверялось."
    )
    sch.append(["text", Q(notes), ["exclude_from_sim", "no"], ["at", 213.36, 101.6, 0],
                ["effects", ["font", ["size", 1.778, 1.778]], ["justify", "left", "bottom"]],
                ["uuid", Q(uid("pc104-blank:notes"))]])
    sch.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
    sch.append(["embedded_fonts", "no"])
    return dump(sch)


# ----------------------------------------------------------------------------- project files
def project_file():
    pro = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.05, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                    "copper_text_size_v": 1.5, "copper_text_thickness": 0.3, "courtyard_line_width": 0.05,
                    "fab_line_width": 0.1, "fab_text_size_h": 1.0, "fab_text_size_v": 1.0,
                    "fab_text_thickness": 0.15, "other_line_width": 0.1, "silk_line_width": 0.15,
                    "silk_text_size_h": 1.0, "silk_text_size_v": 1.0, "silk_text_thickness": 0.15,
                },
                "meta": {"version": 2},
                "rules": {
                    "max_error": 0.005, "min_clearance": 0.2, "min_connection": 0.0,
                    "min_copper_edge_clearance": 0.3, "min_groove_width": 0.0, "min_hole_clearance": 0.25,
                    "min_hole_to_hole": 0.25, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
                    "min_resolved_spokes": 2, "min_silk_clearance": 0.15, "min_text_height": 1.0,
                    "min_text_thickness": 0.15, "min_through_hole_diameter": 0.3, "min_track_width": 0.2,
                    "min_via_annular_width": 0.13, "min_via_diameter": 0.6,
                    "solder_mask_to_copper_clearance": 0.0, "use_height_for_length_calcs": True,
                },
                "drc_exclusions": [],
            },
            "layer_presets": [], "viewports": [],
        },
        "boards": [],
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": PRJ_NAME + ".kicad_pro", "version": 3},
        "net_settings": {
            "classes": [{
                "name": "Default", "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.7,
                "via_drill": 0.3, "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_gap": 0.25,
                "diff_pair_via_gap": 0.25, "diff_pair_width": 0.2, "bus_width": 12, "wire_width": 6,
                "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
                "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647,
            }],
            "meta": {"version": 4}, "net_colors": None, "netclass_assignments": None, "netclass_patterns": [],
        },
        "pcbnew": {"page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [[SCH_UUID, "Root"]],
        "text_variables": {},
    }
    return json.dumps(pro, indent=2)


def lib_tables():
    sym = ('(sym_lib_table\n\t(version 7)\n\t(lib (name "retro104")(type "KiCad")'
           '(uri "${KIPRJMOD}/../lib/retro104.kicad_sym")(options "")(descr "retro104 shared PC/104 symbols"))\n)')
    fp = ('(fp_lib_table\n\t(version 7)\n\t(lib (name "retro104")(type "KiCad")'
          '(uri "${KIPRJMOD}/../lib/retro104.pretty")(options "")(descr "retro104 shared PC/104 footprints"))\n)')
    return sym, fp


def main():
    write(os.path.join(LIB, "retro104.kicad_sym"), symbol_library())
    for gen in (lambda: connector_footprint("J1"), lambda: connector_footprint("J2"), hole_footprint):
        name, text = gen()
        write(os.path.join(LIB, "retro104.pretty", name + ".kicad_mod"), text)
    for which in ("J1", "J2"):
        stack, host = connector_models(which)
        write(os.path.join(LIB, "3d", "Samtec_%s_illustrative.wrl" % MPN[which]), stack)
        write(os.path.join(LIB, "3d", "PC104_host_%s_socket_mating_reference.wrl" % which), host)
    write(os.path.join(LIB, "3d", "PC104_standoff_0.600in_illustrative.wrl"), standoff_model())
    import stock_parts
    for name in stock_parts.copy_stock(os.path.join(LIB, "retro104.pretty"), os.path.join(LIB, "3d")):
        print("copied stock footprint", name)
    write(os.path.join(PRJ, PRJ_NAME + ".kicad_sch"), schematic())
    pro = os.path.join(PRJ, PRJ_NAME + ".kicad_pro")
    if os.path.exists(pro) and "--force" not in sys.argv:
        print("kept existing", os.path.relpath(pro, REPO), "(use --force to overwrite)")
    else:
        write(pro, project_file())
    sym, fp = lib_tables()
    write(os.path.join(PRJ, "sym-lib-table"), sym)
    write(os.path.join(PRJ, "fp-lib-table"), fp)


if __name__ == "__main__":
    main()
