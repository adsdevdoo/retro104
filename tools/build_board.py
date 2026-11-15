"""Build hardware/pc104-blank/pc104-blank.kicad_pcb with the KiCad 9 Python API.

Run with KiCad's Python after tools/generate.py and the netlist export:
  "C:/Program Files/KiCad/9.0/bin/python.exe" tools/build_board.py build/pc104-blank.net

Board orientation = PC/104 v2.6 Fig. 3 top view: bus connectors on the right edge, J1 pin 1 at the
bottom. PC/104 (X, Y) in inches maps to KiCad mm as  x = RIGHT - X*25.4,  y = BOTTOM - Y*25.4.
The drill/place origin is the bottom-left board corner, so Gerber/Excellon coordinates are positive.
Also writes pc104-blank-mating.kicad_pcb (all mating-reference 3D models visible, not committed).
"""

import os
import re
import shutil
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc104_data as D  # noqa: E402
from sexpr import parse, find, first, uid  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRJ = os.path.join(REPO, "hardware", "pc104-blank")
LIBDIR = os.path.join(REPO, "hardware", "lib", "retro104.pretty")
OUT = os.path.join(PRJ, "pc104-blank.kicad_pcb")
OUT_MATING = os.path.join(PRJ, "pc104-blank-mating.kicad_pcb")

LEFT, TOP = 50.0, 50.0
RIGHT = LEFT + D.BOARD_X_IN * D.IN
BOTTOM = TOP + D.BOARD_Y_IN * D.IN
FP_J1 = "PC104_J1P1_2x32_P2.54mm_Stackthrough"
FP_J2 = "PC104_J2P2_2x20_P2.54mm_Stackthrough"
FP_H = "PC104_MountingHole_3.18mm_Pad6.35mm"


def mm(v):
    return pcbnew.FromMM(v)


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def kxy(x_in, y_in):
    return RIGHT - x_in * D.IN, BOTTOM - y_in * D.IN


def read_netlist(path):
    tree = parse(open(path, encoding="utf-8").read())
    nets = {}
    for net in find(first(tree, "nets"), "net"):
        name = first(net, "name")[1]
        for node in find(net, "node"):
            nets[(first(node, "ref")[1], first(node, "pin")[1])] = name
    return nets


def add_text(board, text, x, y, size, layer, thick=None, mirror=False, justify="center"):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick if thick else max(0.15, size * 0.15)))
    t.SetHorizJustify({"center": pcbnew.GR_TEXT_H_ALIGN_CENTER, "left": pcbnew.GR_TEXT_H_ALIGN_LEFT}[justify])
    t.SetMirrored(mirror)
    t.SetPosition(V(x, y))
    board.Add(t)
    return t


def add_segment(board, x1, y1, x2, y2, layer, width):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(x1, y1))
    s.SetEnd(V(x2, y2))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)


def add_dimension(board, x1, y1, x2, y2, height):
    d = pcbnew.PCB_DIM_ALIGNED(board, pcbnew.PCB_DIM_ALIGNED_T)
    d.SetLayer(pcbnew.Dwgs_User)
    d.SetStart(V(x1, y1))
    d.SetEnd(V(x2, y2))
    d.SetHeight(mm(height))
    d.SetUnitsMode(pcbnew.DIM_UNITS_MODE_MM)
    d.SetPrecision(pcbnew.DIM_PRECISION_X_XX)
    d.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    d.SetLineThickness(mm(0.1))
    d.Update()
    board.Add(d)


def place(board, nets, ref, fpname, x, y, value, ref_at=None, ref_layer=pcbnew.F_SilkS, ref_size=1.5):
    fp = pcbnew.FootprintLoad(LIBDIR, fpname)
    if fp is None:
        raise SystemExit("footprint not found: " + fpname)
    fp.SetFPID(pcbnew.LIB_ID("retro104", fpname))
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPath(pcbnew.KIID_PATH("/" + uid("pc104-blank:sym:" + ref)))
    fp.SetSheetname("/")
    fp.SetSheetfile("pc104-blank.kicad_sch")
    fp.SetPosition(V(x, y))
    r = fp.Reference()
    r.SetLayer(ref_layer)
    r.SetTextSize(pcbnew.VECTOR2I(mm(ref_size), mm(ref_size)))
    r.SetTextThickness(mm(0.2 if ref_size >= 1.5 else 0.15))
    if ref_at:
        r.SetPosition(V(*ref_at))
    for pad in fp.Pads():
        num = pad.GetNumber()
        if not num:
            continue  # mounting hole pad: intentionally no net
        name = nets.get((ref, num))
        if name is None:
            raise SystemExit("pad %s.%s missing in netlist" % (ref, num))
        net = board.FindNet(name)
        if net is None:
            net = pcbnew.NETINFO_ITEM(board, name)
            board.Add(net)
        pad.SetNet(net)
    board.Add(fp)
    return fp


def main():
    netlist = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "build", "pc104-blank.net")
    nets = read_netlist(netlist)
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetAuxOrigin(V(LEFT, BOTTOM))
    ds.SetGridOrigin(V(LEFT, BOTTOM))
    tb = board.GetTitleBlock()
    tb.SetTitle("retro104 pc104-blank: PC/104 mating board (no circuits)")
    tb.SetRevision("A")
    tb.SetDate("2026-11-15")
    tb.SetCompany("retro104")
    tb.SetComment(0, "PC/104 v2.6 module 3.775 x 3.550 in, 16-bit bus J1/P1 + J2/P2, Samtec ESQ stackthrough")
    tb.SetComment(1, "Mates Advantech PCM-3864/3860 Rev.A1 CN2 (=J1) and CN1 (=J2), female")
    tb.SetComment(2, "Electrically empty. Not tested in hardware")

    # outline (PC/104 v2.6 Fig. 3), square corners as drawn in the standard
    corners = [(LEFT, TOP), (RIGHT, TOP), (RIGHT, BOTTOM), (LEFT, BOTTOM)]
    for i in range(4):
        add_segment(board, *corners[i], *corners[(i + 1) % 4], pcbnew.Edge_Cuts, 0.05)

    # bus connectors: CN2 = PC/104 J1/P1 (A/B), CN1 = PC/104 J2/P2 (C/D), Advantech names
    ax, ay = kxy(D.J1_ROW_X_IN["A"], D.j1_y_in(1))
    cx, cy = kxy(D.J2_ROW_X_IN["C"], D.j2_y_in(0))
    place(board, nets, "CN2", FP_J1, ax, ay, "ESQ-132-39-G-D", ref_at=(124.5, 97.0))
    place(board, nets, "CN1", FP_J2, cx, cy, "ESQ-120-39-G-D", ref_at=(141.6, 119.6))
    add_text(board, "J1/P1 A,B", 124.5, 99.4, 1.0, pcbnew.F_SilkS)
    add_text(board, "J2 C,D", 141.6, 121.9, 1.0, pcbnew.F_SilkS)

    # mounting holes H1..H4 in the order of D.HOLES_IN
    for i, (hx, hy) in enumerate(D.HOLES_IN):
        x, y = kxy(hx, hy)
        place(board, nets, "H%d" % (i + 1), FP_H, x, y, "MountingHole_3.18mm",
              ref_at=(x, y), ref_layer=pcbnew.F_Fab, ref_size=1.0)

    # top silkscreen
    S = pcbnew.F_SilkS
    mid = (LEFT + 128.0) / 2
    add_text(board, "PC/104", mid, 66.0, 5.0, S, thick=0.8)
    add_text(board, "retro104  pc104-blank  rev A", mid, 74.0, 1.5, S, thick=0.2)
    lines = [
        "PC/104 v2.6 16-bit module, no circuits",
        "CN2 = J1/P1 rows A,B 1-32",
        "CN1 = J2/P2 rows C,D 0-19",
        "Pin 1: square pad + arrow (CN2 A1, CN1 C0)",
        "Stackthrough Samtec ESQ-132-39 / ESQ-120-39",
        "mates PCM-3864/3860 CN2/CN1 (female)",
        "pin 32 end faces PCM-3864 COM1",
    ]
    for i, s in enumerate(lines):
        add_text(board, s, mid, 80.0 + i * 2.4, 1.0, S)
    # bottom silkscreen (mirrored, reads from below)
    B = pcbnew.B_SilkS
    add_text(board, "PC/104  retro104 pc104-blank A", mid, 118.0, 1.5, B, thick=0.2, mirror=True)
    add_text(board, "bottom: P1/P2 tails into host CN2/CN1", mid, 121.0, 1.0, B, mirror=True)
    add_text(board, "CN2 A1 / CN1 C0 = arrows", mid, 123.4, 1.0, B, mirror=True)

    # documentation layers: PC/104 limits and key locations
    C = pcbnew.Cmts_User
    notes = [
        "PC/104 v2.6 Fig. 3: max component height top .435 in (11.05 mm), bottom .100 in (2.54 mm)",
        "Key locations B10 (CN2) and C19 (CN1): no pin on P1/P2, plugged hole on J1/J2 (v2.6 Sec. 2.3)",
        "PCM-3864 manual p.67: B10 = GND, C19 = N/C. Holes kept: they accept keyed and unkeyed parts",
        "Mounting holes 3.18 mm, pad 6.35 mm, standoffs .600 in (15.24 mm)",
    ]
    for i, s in enumerate(notes):
        add_text(board, s, LEFT + 2, BOTTOM + 6 + i * 2.0, 1.0, C, justify="left")
    add_dimension(board, LEFT, TOP, RIGHT, TOP, -4.0)
    add_dimension(board, LEFT, TOP, LEFT, BOTTOM, 4.0)

    pcbnew.SaveBoard(OUT, board, True)  # keep the generated .kicad_pro rules
    print("saved", os.path.relpath(OUT, REPO))

    # Mating view: same board with the hidden reference models (host sockets, standoffs) shown.
    # A project file next to it keeps ${KIPRJMOD} pointing at this directory for kicad-cli.
    text = open(OUT, encoding="utf-8").read()
    text, n = re.subn(r'(\(model "[^"]+"\s*\n)\s*\(hide yes\)\s*\n', r"\1", text)
    with open(OUT_MATING, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    shutil.copyfile(os.path.join(PRJ, "pc104-blank.kicad_pro"), OUT_MATING.replace(".kicad_pcb", ".kicad_pro"))
    print("saved", os.path.relpath(OUT_MATING, REPO), "(%d reference models shown, not committed)" % n)


if __name__ == "__main__":
    main()
