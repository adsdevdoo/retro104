"""Place pc104-audio and export a Specctra DSN for FreeRouting (KiCad 9 Python).

  "C:/Program Files/KiCad/9.0/bin/python.exe" tools/build_audio_board.py build/audio/pc104-audio.net

Writes build/audio/placed.kicad_pcb (+ placed.kicad_pro with net classes) and build/audio/placed.dsn.
Outline, mounting holes and CN1/CN2 come from the same PC/104 data as pc104-blank.
Board orientation = PC/104 v2.6 Fig. 3 (bus edge right, J1 pin 1 at the bottom); the top edge
(pin 32 end) faces the PCM-3864 I/O edge, so the audio jacks sit there; the right-angle game/MIDI
header sits on the bottom edge. Both edges are PC/104 I/O overhang regions (Fig. 3).
"""

import os
import shutil
import sys

import pcbnew as p

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_design as A  # noqa: E402
import pc104_data as D  # noqa: E402
from sexpr import dump, parse, find, first, uid  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(REPO, "hardware", "lib", "retro104.pretty")
BUILD = os.path.join(REPO, "build", "audio")
PRJ_NAME = "pc104-audio"
LEFT, TOP = 50.0, 50.0
RIGHT = LEFT + D.BOARD_X_IN * D.IN
BOTTOM = TOP + D.BOARD_Y_IN * D.IN
JACK_Y = TOP + 3.5  # SJ1-3523N: posts 1.0/3.5 mm from the body front; body front on the board edge

# ref: (x, y, rotation) in KiCad mm; see docs/pc104-audio.md for the layout rationale
PLACE = {
    "U1": (95.0, 96.0, 180),
    "J1": (66.0, JACK_Y, 180), "J2": (81.5, JACK_Y, 180), "J3": (97.0, JACK_Y, 180),
    "J4": (104.0, 126.35, -90),
    # line out / line in / mic, row A
    "C21": (63.0, 67.0, 0), "C22": (70.5, 67.0, 0), "C17": (78.0, 67.0, 90), "C18": (81.5, 67.0, 90),
    "C20": (93.0, 67.0, 90), "R3": (96.5, 67.0, 90), "R2": (100.0, 67.0, 90), "C19": (106.5, 67.0, 0),
    # row B: CMR, VDDA filter
    "C10": (99.0, 74.0, 0), "C8": (87.5, 74.0, 0), "FB1": (81.0, 74.0, 0),
    # row C: reference, filter and VDDA bypass, next to pins 39-47
    "C11": (97.5, 80.0, 90), "C12": (95.0, 80.0, 90), "C9": (92.5, 80.0, 90), "C13": (90.0, 80.0, 90),
    "C14": (87.5, 80.0, 90), "C15": (85.0, 80.0, 90), "C16": (82.5, 80.0, 90),
    # U1 decoupling (pins 3, 26 right; 57, 80 left)
    "C1": (106.5, 104.0, 90), "C2": (106.5, 89.2, 90), "C3": (83.0, 90.5, 90), "C4": (83.0, 105.4, 90),
    # crystal next to XI/XO (pins 78/79)
    "Y1": (78.5, 103.0, 90), "C23": (74.0, 99.0, 90), "C24": (74.0, 103.5, 90),
    # address decode, EEPROM, PnP selection
    "U2": (114.0, 92.0, 0), "C5": (114.0, 99.5, 0), "U3": (111.0, 103.0, 0), "C6": (121.5, 110.0, 90),
    "JP1": (125.5, 102.0, 0), "JP2": (125.5, 106.0, 0), "R1": (125.5, 110.0, 0), "C7": (125.5, 116.0, 0),
    "R4": (96.0, 111.0, 90), "R5": (98.5, 111.0, 90),
}
JOY_ROWS = [115.5, 119.0, 122.5]
JOY = ["R6", "R10", "C25", "R7", "R11", "C26", "R8",
       "R12", "C27", "R9", "R13", "C28", "R18", "R19",
       "R14", "C29", "R15", "C30", "R16", "C31", "R17", "C32", "FB2", "C33"]
for i, ref in enumerate(JOY):
    PLACE[ref] = (62.0 + (i % 8) * 4.5, JOY_ROWS[i // 8], 0)

# silkscreen references stay visible for these; 0805/CP/FB references go to F.Fab (assembly drawing)
SILK_REFS = {"U1", "U2", "U3", "Y1", "J1", "J2", "J3", "J4", "JP1", "JP2", "CN1", "CN2"}
NOT_IN_BOM = ("MountingHole_PC104", "SolderJumper_3_Bridged12")
# absolute positions of the silkscreen references (horizontal text, away from pads)
REF_AT = {
    "U1": (95.0, 96.0), "U2": (114.0, 92.0), "U3": (114.81, 106.81), "Y1": (78.5, 100.56),
    "J1": (66.0, 57.0), "J2": (81.5, 57.0), "J3": (97.0, 57.0), "J4": (95.1, 134.5),
    "JP1": (129.6, 102.0), "JP2": (129.6, 106.0), "CN2": (124.5, 80.0), "CN1": (141.6, 119.6),
}


def mm(v):
    return p.FromMM(v)


def V(x, y):
    return p.VECTOR2I(mm(x), mm(y))


def kxy(x_in, y_in):
    return RIGHT - x_in * D.IN, BOTTOM - y_in * D.IN


def read_netlist(path):
    tree = parse(open(path, encoding="utf-8").read())
    nets = {}
    for net in find(first(tree, "nets"), "net"):
        name = str(first(net, "name")[1])
        for node in find(net, "node"):
            nets[(str(first(node, "ref")[1]), str(first(node, "pin")[1]))] = name
    return nets


def fp_of(ref):
    part = A.PARTS[ref]
    if part["fp"]:
        return part["fp"].split(":", 1)[1]
    return {"R": "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", "C": "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder",
            "FerriteBead": "L_0805_2012Metric_Pad1.15x1.40mm_HandSolder", "CP": "CP_Elec_4x5.4",
            "Crystal": "Crystal_HC49-4H_Vertical", "ES1868": "PQFP-100_14x20mm_P0.65mm",
            "74HCT138": "SOIC-16_3.9x9.9mm_P1.27mm", "93C66": "DIP-8_W7.62mm_Socket_LongPads",
            "Jack_TRS": "Jack_3.5mm_CUI_SJ1-3523N_Horizontal_Slots",
            "Conn_02x08_Odd_Even": "IDC-Header_2x08_P2.54mm_Horizontal",
            "SolderJumper_3_Bridged12": "SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm",
            "PC104_J1P1": "PC104_J1P1_2x32_P2.54mm_Stackthrough", "PC104_J2P2": "PC104_J2P2_2x20_P2.54mm_Stackthrough",
            "MountingHole_PC104": "PC104_MountingHole_3.18mm_Pad6.35mm"}[part["sym"]]


def add_segment(b, x1, y1, x2, y2):
    s = p.PCB_SHAPE(b)
    s.SetShape(p.SHAPE_T_SEGMENT)
    s.SetStart(V(x1, y1))
    s.SetEnd(V(x2, y2))
    s.SetLayer(p.Edge_Cuts)
    s.SetWidth(mm(0.05))
    b.Add(s)


def main():
    nets_by_pin = read_netlist(sys.argv[1] if len(sys.argv) > 1 else os.path.join(BUILD, PRJ_NAME + ".net"))
    b = p.BOARD()
    ds = b.GetDesignSettings()
    ds.SetAuxOrigin(V(LEFT, BOTTOM))
    ds.SetGridOrigin(V(LEFT, BOTTOM))
    ds.m_MinClearance = mm(0.2)
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_CopperEdgeClearance = mm(0.3)
    ns = ds.m_NetSettings
    dflt = ns.GetDefaultNetclass()
    dflt.SetTrackWidth(mm(0.25))
    dflt.SetClearance(mm(0.2))
    dflt.SetViaDiameter(mm(0.7))
    dflt.SetViaDrill(mm(0.3))
    power = p.NETCLASS("Power")
    power.SetClearance(mm(0.2))
    power.SetTrackWidth(mm(0.4))  # 0.4 mm still enters a 0.65 mm pitch QFP pad with 0.2 mm clearance
    power.SetViaDiameter(mm(0.8))
    power.SetViaDrill(mm(0.4))
    ns.SetNetclass("Power", power)

    nets = {}
    for name in sorted(set(nets_by_pin.values())):
        if name.startswith("unconnected-"):
            continue  # single-pad nets are assigned after routing (DSN cannot carry their names)
        nets[name] = p.NETINFO_ITEM(b, name)
        b.Add(nets[name])
    for name in ("+5V", "+5VA", "+5VJ"):  # GND is carried by both pours and the stitching vias
        ns.SetNetclassPatternAssignment("/" + name, "Power")
        nets["/" + name].SetNetClass(power)

    corners = [(LEFT, TOP), (RIGHT, TOP), (RIGHT, BOTTOM), (LEFT, BOTTOM)]
    for i in range(4):
        add_segment(b, *corners[i], *corners[(i + 1) % 4])

    place = dict(PLACE)
    ax, ay = kxy(D.J1_ROW_X_IN["A"], D.j1_y_in(1))
    cx, cy = kxy(D.J2_ROW_X_IN["C"], D.j2_y_in(0))
    place["CN2"], place["CN1"] = (ax, ay, 0), (cx, cy, 0)
    for i, (hx, hy) in enumerate(D.HOLES_IN):
        place["H%d" % (i + 1)] = kxy(hx, hy) + (0,)
    missing = [r for r in A.PARTS if r not in place]
    if missing:
        raise SystemExit("no position for %s" % missing)

    for ref, part in A.PARTS.items():
        name = fp_of(ref)
        fp = p.FootprintLoad(LIB, name)
        if fp is None:
            raise SystemExit("footprint not found: " + name)
        fp.SetFPID(p.LIB_ID("retro104", name))
        fp.SetReference(ref)
        fp.SetValue(part["value"])
        fp.SetPath(p.KIID_PATH("/" + uid(PRJ_NAME + ":sym:" + ref)))
        fp.SetSheetname("/")
        fp.SetSheetfile(PRJ_NAME + ".kicad_sch")
        x, y, rot = place[ref]
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        r = fp.Reference()
        r.SetTextSize(p.VECTOR2I(mm(1.0), mm(1.0)))
        r.SetTextThickness(mm(0.15))
        if ref in REF_AT:
            r.SetPosition(V(*REF_AT[ref]))
            r.SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
            if ref.startswith("CN"):
                r.SetTextSize(p.VECTOR2I(mm(1.5), mm(1.5)))
                r.SetTextThickness(mm(0.2))
        if ref not in SILK_REFS:
            r.SetLayer(p.F_Fab)
            r.SetTextSize(p.VECTOR2I(mm(0.6), mm(0.6)))
            r.SetTextThickness(mm(0.1))
            r.SetPosition(V(x, y))
            r.SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
        fp.Value().SetVisible(False)
        fp.SetExcludedFromBOM(part["sym"] in NOT_IN_BOM)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if not num:
                continue
            name = nets_by_pin.get((ref, num))
            if name is None:
                raise SystemExit("pad %s.%s not in netlist" % (ref, num))
            if name in nets:
                pad.SetNet(nets[name])
        b.Add(fp)

    os.makedirs(BUILD, exist_ok=True)
    out = os.path.join(BUILD, "placed.kicad_pcb")
    b.SetFileName(out)
    p.SaveBoard(out, b)  # also writes placed.kicad_pro with the net classes
    # KiCad 9.0.2 ExportSpecctraDSN hangs on footprints that contain fp_arc graphics (crystal, DIP
    # socket); export from a copy without footprint arcs. Routing does not depend on silk/fab graphics.
    tree = parse(open(out, encoding="utf-8").read())
    for fpn in find(tree, "footprint"):
        fpn[:] = [x for x in fpn if not (isinstance(x, list) and x and x[0] == "fp_arc")]
    tmp = os.path.join(BUILD, "placed_dsn.kicad_pcb")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(dump(tree))
    shutil.copyfile(os.path.join(BUILD, "placed.kicad_pro"), tmp.replace(".kicad_pcb", ".kicad_pro"))  # net classes
    if not p.ExportSpecctraDSN(p.LoadBoard(tmp), os.path.join(BUILD, "placed.dsn")):
        raise SystemExit("DSN export failed")
    print("placed %d footprints, %d nets -> %s" % (len(A.PARTS), len(nets), out))


if __name__ == "__main__":
    main()
