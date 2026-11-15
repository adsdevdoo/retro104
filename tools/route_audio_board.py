"""Finish pc104-audio after FreeRouting (KiCad 9 Python).

  "C:/Program Files/KiCad/9.0/bin/python.exe" tools/route_audio_board.py build/audio/pc104-audio.net

Imports build/audio/placed.ses into build/audio/placed.kicad_pcb, assigns the single-pad
"unconnected-*" nets (schematic parity), pours GND on both layers and stitches them, adds the
silkscreen and saves hardware/pc104-audio/pc104-audio.kicad_pcb. Net classes and rules that pcbnew
wrote next to the placed board are merged into hardware/pc104-audio/pc104-audio.kicad_pro.
"""

import json
import math
import os
import sys

import pcbnew as p

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_audio_board as B  # noqa: E402

REPO = B.REPO
BUILD = B.BUILD
PRJ = os.path.join(REPO, "hardware", B.PRJ_NAME)
OUT = os.path.join(PRJ, B.PRJ_NAME + ".kicad_pcb")
PRO = os.path.join(PRJ, B.PRJ_NAME + ".kicad_pro")
mm, V = B.mm, B.V


def text(b, s, x, y, size=1.0, layer=p.F_SilkS, thick=0.15, justify="center", angle=0):
    t = p.PCB_TEXT(b)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetTextSize(p.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick))
    t.SetHorizJustify({"center": p.GR_TEXT_H_ALIGN_CENTER, "left": p.GR_TEXT_H_ALIGN_LEFT,
                       "right": p.GR_TEXT_H_ALIGN_RIGHT}[justify])
    t.SetMirrored(layer == p.B_SilkS)
    t.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T))
    t.SetPosition(V(x, y))
    b.Add(t)
    return t


def gnd_zone(b, layer, net):
    z = p.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetLocalClearance(mm(0.25))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(p.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.3))
    z.SetThermalReliefSpokeWidth(mm(0.4))
    z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetZoneName("GND_" + ("top" if layer == p.F_Cu else "bottom"))
    o = z.Outline()
    o.NewOutline()
    for x, y in ((B.LEFT, B.TOP), (B.RIGHT, B.TOP), (B.RIGHT, B.BOTTOM), (B.LEFT, B.BOTTOM)):
        o.Append(V(x, y))
    b.Add(z)
    return z


def stitch_gnd(b, net, pitch=3.0, via_d=0.8, drill=0.4, clearance=0.3):
    """Drop GND vias on a grid where they clear all other copper; keep those inside fill on both layers."""
    obstacles = []
    for t in b.GetTracks():
        if t.GetClass() != "PCB_VIA" and t.GetNetname() == net.GetNetname():
            continue  # same-net tracks are fine; every via counts (hole-to-hole spacing)
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            obstacles.append(("disc", p.ToMM(c.x), p.ToMM(c.y), p.ToMM(t.GetWidth(p.F_Cu)) / 2))
        else:
            s, e = t.GetStart(), t.GetEnd()
            obstacles.append(("seg", p.ToMM(s.x), p.ToMM(s.y), p.ToMM(e.x), p.ToMM(e.y), p.ToMM(t.GetWidth()) / 2))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            obstacles.append(("box", p.ToMM(bb.GetLeft()), p.ToMM(bb.GetTop()), p.ToMM(bb.GetRight()),
                              p.ToMM(bb.GetBottom()), pad.GetNetname() == net.GetNetname()))
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(p.F_CrtYd).BBox()
        if fp.GetReference().startswith(("U", "J", "Y", "CN")):
            obstacles.append(("box", p.ToMM(cy.GetLeft()), p.ToMM(cy.GetTop()), p.ToMM(cy.GetRight()),
                              p.ToMM(cy.GetBottom()), False))
    reach = via_d / 2 + clearance

    def free(x, y):
        for o in obstacles:
            if o[0] == "disc":
                if math.hypot(x - o[1], y - o[2]) < reach + o[3]:
                    return False
            elif o[0] == "seg":
                _, x1, y1, x2, y2, w = o
                dx, dy = x2 - x1, y2 - y1
                L2 = dx * dx + dy * dy
                t = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
                if math.hypot(x - x1 - t * dx, y - y1 - t * dy) < reach + w:
                    return False
            else:
                _, x0, y0, x1, y1, same = o
                if x0 - reach < x < x1 + reach and y0 - reach < y < y1 + reach:
                    return False
        return True

    added = []
    y = B.TOP + 2.0
    while y < B.BOTTOM - 1.5:
        x = B.LEFT + 2.0
        while x < B.RIGHT - 1.5:
            if free(x, y):
                v = p.PCB_VIA(b)
                v.SetPosition(V(x, y))
                v.SetWidth(p.F_Cu, mm(via_d))
                v.SetDrill(mm(drill))
                v.SetNet(net)
                b.Add(v)
                added.append(v)
                obstacles.append(("disc", x, y, via_d / 2))
            x += pitch
        y += pitch
    p.ZONE_FILLER(b).Fill(b.Zones())
    zones = {z.GetLayer(): z for z in b.Zones()}
    kept = 0
    for v in added:
        pos = v.GetPosition()
        if all(zones[layer].HitTestFilledArea(layer, pos) for layer in (p.F_Cu, p.B_Cu)):
            kept += 1
        else:
            b.Remove(v)
    p.ZONE_FILLER(b).Fill(b.Zones())
    print("GND stitching: %d candidates, %d kept" % (len(added), kept))


def seg_dist(a0, a1, b0, b1):
    """Shortest distance between segments a0-a1 and b0-b1 (mm tuples); a point is a zero-length segment."""
    def pt_seg(pt, s0, s1):
        dx, dy = s1[0] - s0[0], s1[1] - s0[1]
        L = dx * dx + dy * dy
        u = 0.0 if L == 0 else max(0.0, min(1.0, ((pt[0] - s0[0]) * dx + (pt[1] - s0[1]) * dy) / L))
        return math.hypot(pt[0] - s0[0] - u * dx, pt[1] - s0[1] - u * dy)

    def cross(o, a, c):
        return (a[0] - o[0]) * (c[1] - o[1]) - (a[1] - o[1]) * (c[0] - o[0])

    d1, d2 = cross(a0, a1, b0), cross(a0, a1, b1)
    d3, d4 = cross(b0, b1, a0), cross(b0, b1, a1)
    if d1 * d2 < 0 and d3 * d4 < 0:
        return 0.0
    return min(pt_seg(a0, b0, b1), pt_seg(a1, b0, b1), pt_seg(b0, a0, a1), pt_seg(b1, a0, a1))


def fix_clearance(b, clearance=0.2, margin=0.002):
    """Router rounding and the widened neck-downs leave a few objects microns short of 0.2 mm: shrink the
    wider object of such a pair by the shortfall (idea from isa-flash-disk fix_clearance)."""
    power = {"/+5V", "/+5VA", "/+5VJ", "/GND"}
    items = []
    for t in b.GetTracks():
        s, e = t.GetStart(), t.GetEnd()
        if t.GetClass() == "PCB_VIA":
            items.append((t, None, t.GetNetCode(), (p.ToMM(s.x), p.ToMM(s.y)), (p.ToMM(s.x), p.ToMM(s.y)), True))
        else:
            items.append((t, t.GetLayer(), t.GetNetCode(), (p.ToMM(s.x), p.ToMM(s.y)), (p.ToMM(e.x), p.ToMM(e.y)), False))
    fixed = 0
    for i, (t1, l1, n1, a0, a1, v1) in enumerate(items):
        for t2, l2, n2, b0, b1, v2 in items[i + 1:]:
            if n1 == n2 or (v1 and v2) or (not v1 and not v2 and l1 != l2):
                continue
            w1 = p.ToMM(t1.GetWidth(p.F_Cu) if v1 else t1.GetWidth())
            w2 = p.ToMM(t2.GetWidth(p.F_Cu) if v2 else t2.GetWidth())
            reach = (w1 + w2) / 2 + clearance
            if min(b0[0], b1[0]) - reach > max(a0[0], a1[0]) or min(a0[0], a1[0]) - reach > max(b0[0], b1[0]):
                continue
            if min(b0[1], b1[1]) - reach > max(a0[1], a1[1]) or min(a0[1], a1[1]) - reach > max(b0[1], b1[1]):
                continue
            gap = seg_dist(a0, a1, b0, b1) - (w1 + w2) / 2
            if gap >= clearance:
                continue
            short = clearance - gap + margin
            # Shrink the wider object by the shortfall: a signal track not below 0.2 mm, a power track not
            # below 0.3 mm, a via not below 0.6 mm (annular ring stays >= 0.15 mm with a 0.3 mm drill).
            for t, w, via in sorted(((t1, w1, v1), (t2, w2, v2)), key=lambda x: -x[1]):
                floor = 0.6 if via else 0.3 if t.GetNetname() in power else 0.2
                if w - 2 * short < floor:
                    continue
                if via:
                    t.SetWidth(p.F_Cu, p.FromMM(w - 2 * short))
                else:
                    t.SetWidth(p.FromMM(w - 2 * short))
                fixed += 1
                break
            else:
                print("clearance %.4f mm between %s and %s not fixable" % (gap, t1.GetNetname(), t2.GetNetname()))
    print("shrunk %d tracks/vias by a few microns for clearance" % fixed)


def silkscreen(b):
    S, BS = p.F_SilkS, p.B_SilkS
    y = B.TOP + 12.9  # just below the jack bodies (courtyard ends at 61.5)
    for ref, label in (("J1", "LINE OUT"), ("J2", "LINE IN"), ("J3", "MIC")):
        x = B.PLACE[ref][0]
        text(b, label, x, y)
        text(b, label, x, y, layer=BS)
    # bus connector names (same convention as pc104-blank)
    text(b, "J1/P1 A,B", 124.5, 82.4)
    text(b, "J2 C,D", 141.6, 121.9)
    text(b, "pc104-audio A", 121.0, 66.0, size=1.2, thick=0.18)
    text(b, "ES1868F", 121.0, 68.6)
    # bottom side: title, header pinout, jumpers, resources
    mid = 80.0  # free of THT pads on the bottom side (jacks above, Y1/U3 below)
    lines = [
        ("retro104 pc104-audio rev A  -  ESS ES1868F", 1.4, 0.2),
        ("PC/104 16-bit, CN2 = J1/P1 (A,B), CN1 = J2/P2 (C,D)", 1.0, 0.15),
        ("SB Pro + ESFM (OPL3) + MPU-401 + game port", 1.0, 0.15),
        ("IRQ A..F = 9,5,7,10,11,12   DRQ A..D = 0,1,3,5", 1.0, 0.15),
        ("JP1/JP2 1-2 (H): PnP data from 93C66 U3", 1.0, 0.15),
        ("JP1/JP2 2-3 (L): ES1868 internal ROM", 1.0, 0.15),
        ("J4 GAME/MIDI: std 16-pin bracket cable,", 1.0, 0.15),
        ("pin 1 = +5V, 8 = MIDI OUT, 14 = MIDI IN, 16 = key", 1.0, 0.15),
        ("not tested in hardware", 1.0, 0.15),
    ]
    for i, (s, size, th) in enumerate(lines):
        text(b, s, mid, 66.0 + i * 2.6, size=size, layer=BS, thick=th)


def merge_project_rules():
    src = json.load(open(os.path.join(BUILD, "placed.kicad_pro"), encoding="utf-8"))
    dst = json.load(open(PRO, encoding="utf-8"))
    rules = dst["board"]["design_settings"]["rules"]
    dst["board"]["design_settings"] = src["board"]["design_settings"]
    dst["board"]["design_settings"]["rules"].update(rules)
    dst["net_settings"] = src["net_settings"]
    dst["meta"]["filename"] = os.path.basename(PRO)
    with open(PRO, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(dst, indent=2) + "\n")


def main():
    nets_by_pin = B.read_netlist(sys.argv[1] if len(sys.argv) > 1 else os.path.join(BUILD, B.PRJ_NAME + ".net"))
    b = p.LoadBoard(os.path.join(BUILD, "placed.kicad_pcb"))
    if not p.ImportSpecctraSES(b, os.path.join(BUILD, "placed.ses")):
        raise SystemExit("SES import failed")
    # single-pad nets for unused pins (parity with the schematic netlist)
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            num = pad.GetNumber()
            name = nets_by_pin.get((ref, num)) if num else None
            if name and name.startswith("unconnected-"):
                net = b.FindNet(name)
                if net is None:
                    net = p.NETINFO_ITEM(b, name)
                    b.Add(net)
                pad.SetNet(net)
    # bus GND pins: solid connection (thermal spokes between bus traces end up starved)
    for fp in b.GetFootprints():
        if fp.GetReference() in ("CN1", "CN2"):
            for pad in fp.Pads():
                if pad.GetNetname() == "/GND":
                    pad.SetLocalZoneConnection(p.ZONE_CONNECTION_FULL)
    # FreeRouting necks tracks down to 75 % of the class width at pins (0.25 -> 0.187 mm); the rule and
    # JLCPCB minimum is 0.2 mm. Same fix as isa-flash-disk; DRC afterwards checks the clearances.
    narrow = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(0.2)]
    for t in narrow:
        t.SetWidth(mm(0.2))
    print("widened %d neck-down segments to 0.2 mm" % len(narrow))
    fix_clearance(b)
    gnd = b.FindNet("/GND")
    for layer in (p.F_Cu, p.B_Cu):
        gnd_zone(b, layer, gnd)
    p.ZONE_FILLER(b).Fill(b.Zones())
    stitch_gnd(b, gnd)
    silkscreen(b)
    tb = b.GetTitleBlock()
    tb.SetTitle("retro104 pc104-audio: PC/104 sound card, ESS ES1868F")
    tb.SetRevision("A")
    tb.SetDate("2026-11-15")
    tb.SetCompany("retro104")
    tb.SetComment(0, "ESS ES1868 reference circuit (data sheet App. B), line out / line in / mic, game+MIDI 2x8")
    tb.SetComment(1, "PC/104 v2.6 16-bit module, CN2 = J1/P1, CN1 = J2/P2 (Advantech PCM-3864 names)")
    tb.SetComment(2, "Not tested in hardware")
    b.SetFileName(OUT)
    p.SaveBoard(OUT, b, True)
    merge_project_rules()
    tracks = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK"]
    vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    print("saved %s: %d tracks, %d vias" % (os.path.relpath(OUT, REPO), len(tracks), len(vias)))


if __name__ == "__main__":
    main()
