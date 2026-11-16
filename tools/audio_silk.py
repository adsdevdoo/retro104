"""Silkscreen of pc104-audio (KiCad 9 Python), applied to the routed board in place.

  "C:/Program Files/KiCad/9.0/bin/python.exe" tools/audio_silk.py

Top: every reference designator on F.Silkscreen (1.0 mm text, 0.15 mm stroke = JLCPCB minimum),
values of the ICs, crystal and electrolytic capacitors, jack, header and bus labels. Label positions
are searched around each part: a label keeps PAD_GAP from pads, SILK_GAP from other silkscreen,
stays off the courtyards of other parts and EDGE_GAP inside the board edge.
Bottom: title block, IRQ/DRQ and resource tables, jumper and jack notes, J4 game/MIDI pin names.

Copper is not touched, so the routing stays. Board-level silkscreen is removed and drawn again and the
footprint fields are re-placed, so the script can run any number of times with the same result
(UUIDs of board-level graphics are derived from their order). Exit code 1 if a label finds no free
place or any two silkscreen items / a silkscreen item and a pad end up too close.
"""

import math
import os
import re
import sys

import pcbnew as p

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio_design as A  # noqa: E402
import build_audio_board as B  # noqa: E402
from sexpr import uid  # noqa: E402

PCB = os.path.join(B.REPO, "hardware", B.PRJ_NAME, B.PRJ_NAME + ".kicad_pcb")
mm, V = B.mm, B.V
TXT, STROKE = 1.0, 0.15  # JLCPCB: text height >= 1.0 mm, stroke >= 0.15 mm
PAD_GAP, SILK_GAP, EDGE_GAP = 0.2, 0.2, 0.5
FAIL = []

# ------------------------------------------------------------------ top side content
# fixed labels: (ref or None, extra text, centre x, centre y, size)
TOP_FIXED = [
    ("J1", "LINE OUT", B.PLACE["J1"][0], B.TOP + 12.9, TXT),
    ("J2", "LINE IN", B.PLACE["J2"][0], B.TOP + 12.9, TXT),
    ("J3", "MIC", B.PLACE["J3"][0], B.TOP + 12.9, TXT),
    ("CN2", None, 124.5, 80.0, 1.5),
    (None, "J1/P1 A,B", 124.5, 82.4, TXT),
    ("CN1", None, 141.6, 119.6, 1.5),
    (None, "J2 C,D", 141.6, 121.9, TXT),
    ("J4", "GAME/MIDI", 76.5, 127.6, TXT),
    (None, "pc104-audio rev A", 121.0, 66.0, 1.2),
    (None, "retro104", 121.0, 68.6, TXT),
]


def value_label(ref):
    """Short value printed next to the reference: ICs, crystal, electrolytics."""
    part = A.PARTS[ref]
    if ref.startswith("U"):
        return part["value"]
    if ref == "Y1":
        return "14.318MHz"
    if part["sym"] == "CP":
        return part["value"].split()[0].replace("uF", "u")
    return None


# Forced label sides. The VDDA/filter row C9-C16 has a 2.5 mm pitch: labels alternate above/below;
# U1 then reads vertically on its right between C2 and C1; JP1/JP2 labels to the right; R3 below
# (above it would stack under "J3 MIC"), so C10 moves to its right.
SIDE = {"C16": "above", "C15": "below", "C14": "above", "C13": "below", "C9": "above", "C12": "below",
        "C11": "right", "U1": "right90", "JP1": "right", "JP2": "right", "R3": "below", "C10": "right"}

# J4 pin names, DB-15 game port convention (National AN-1130): B = button, X/Y = axis
J4_NAMES = {1: "+5V", 2: "+5V", 3: "B1", 4: "B3", 5: "X1", 6: "X2", 7: "GND", 8: "MOUT", 9: "GND",
            10: "Y2", 11: "Y1", 12: "B4", 13: "B2", 14: "MIN", 15: "+5V", 16: "KEY"}


# ------------------------------------------------------------------ geometry helpers
def box_of(item):
    if isinstance(item, p.EDA_TEXT) or item.GetClass() in ("PCB_TEXT", "PCB_FIELD"):
        bb = item.GetEffectiveTextShape().BBox()
    else:
        bb = item.GetBoundingBox()
    return (p.ToMM(bb.GetLeft()), p.ToMM(bb.GetTop()), p.ToMM(bb.GetRight()), p.ToMM(bb.GetBottom()))


def hit(a, b, gap):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


class Side:
    """Obstacles of one board side: pads, silkscreen boxes, courtyards (top only)."""

    def __init__(self, b, cu, silk, crtyd):
        self.silk, self.items = silk, []  # (box, gap, tag)
        self.courts = []  # (box, ref)
        for fp in b.GetFootprints():
            ref = fp.GetReference()
            for pad in fp.Pads():
                if pad.IsOnLayer(cu):
                    self.items.append((box_of(pad), PAD_GAP, "pad %s.%s" % (ref, pad.GetNumber())))
            for g in fp.GraphicalItems():
                if g.GetLayer() != silk:
                    continue
                if g.GetClass() == "PCB_SHAPE":
                    for bx in shape_boxes(g):
                        self.items.append((bx, SILK_GAP, "silk of %s" % ref))
                elif g.GetClass() == "PCB_TEXT" and g.IsVisible():
                    self.items.append((box_of(g), SILK_GAP, "silk text of %s" % ref))
            if crtyd is not None:
                fp.BuildCourtyardCaches()
                poly = fp.GetCourtyard(crtyd)
                if poly.OutlineCount():
                    bb = poly.BBox()
                    self.courts.append(((p.ToMM(bb.GetLeft()), p.ToMM(bb.GetTop()), p.ToMM(bb.GetRight()),
                                         p.ToMM(bb.GetBottom())), ref))
        self.edge = (B.LEFT + EDGE_GAP, B.TOP + EDGE_GAP, B.RIGHT - EDGE_GAP, B.BOTTOM - EDGE_GAP)

    def blocked(self, bx, own=None):
        if not (self.edge[0] <= bx[0] and bx[2] <= self.edge[2] and self.edge[1] <= bx[1] and bx[3] <= self.edge[3]):
            return "board edge"
        for ob, gap, tag in self.items:
            if hit(bx, ob, gap):
                return tag
        for cb, ref in self.courts:
            if ref != own and hit(bx, cb, 0.0):
                return "courtyard of %s" % ref
        return None

    def add(self, bx, tag):
        self.items.append((bx, SILK_GAP, tag))


def shape_boxes(g):
    """Boxes of a silkscreen shape; a rectangle outline is split into its four sides."""
    w = p.ToMM(g.GetWidth()) / 2
    if g.GetShape() == p.SHAPE_T_RECT and not g.IsFilled():
        s, e = g.GetStart(), g.GetEnd()
        x0, y0, x1, y1 = (p.ToMM(min(s.x, e.x)), p.ToMM(min(s.y, e.y)), p.ToMM(max(s.x, e.x)), p.ToMM(max(s.y, e.y)))
        return [(x0 - w, y0 - w, x1 + w, y0 + w), (x0 - w, y1 - w, x1 + w, y1 + w),
                (x0 - w, y0 - w, x0 + w, y1 + w), (x1 - w, y0 - w, x1 + w, y1 + w)]
    return [box_of(g)]


def style(t, layer, size=TXT, thick=STROKE, angle=0):
    t.SetLayer(layer)
    t.SetTextSize(p.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(thick))
    t.SetHorizJustify(p.GR_TEXT_H_ALIGN_CENTER)
    t.SetVertJustify(p.GR_TEXT_V_ALIGN_CENTER)
    t.SetMirrored(layer == p.B_SilkS)
    t.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T))
    t.SetVisible(True)


def new_text(b, s, layer, size=TXT, thick=STROKE, angle=0):
    t = p.PCB_TEXT(b)
    t.SetText(s)
    style(t, layer, size, thick, angle)
    b.Add(t)
    return t


def extent(t):
    """(length along the reading direction, height) of a text at angle 0."""
    a = t.GetTextAngle()
    t.SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
    t.SetPosition(V(0, 0))
    x0, y0, x1, y1 = box_of(t)
    t.SetTextAngle(a)
    return x1 - x0, y1 - y0


def row_layout(texts, cx, cy, angle, gap=0.9):
    """Place texts in one row centred on (cx, cy): angle 0 reads left to right, 90 bottom to top."""
    ext = [extent(t) for t in texts]
    total = sum(e[0] for e in ext) + gap * (len(texts) - 1)
    pos = -total / 2
    for t, (w, _) in zip(texts, ext):
        c = pos + w / 2
        t.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T))
        t.SetPosition(V(cx + c, cy) if angle == 0 else V(cx, cy - c))
        pos += w + gap
    boxes = [box_of(t) for t in texts]
    return (min(bx[0] for bx in boxes), min(bx[1] for bx in boxes), max(bx[2] for bx in boxes),
            max(bx[3] for bx in boxes))


def row_size(texts, angle, gap=0.9):
    ext = [extent(t) for t in texts]
    length = sum(e[0] for e in ext) + gap * (len(texts) - 1)
    height = max(e[1] for e in ext)
    return (length, height) if angle == 0 else (height, length)


# ------------------------------------------------------------------ top side
def place_top(b, side):
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    done = set()
    for ref, extra, x, y, size in TOP_FIXED:
        texts = []
        if ref:
            r = fps[ref].Reference()
            style(r, p.F_SilkS, size, 0.2 if size > 1.2 else STROKE)
            texts.append(r)
            done.add(ref)
        if extra:
            texts.append(new_text(b, extra, p.F_SilkS, size, 0.18 if size > 1.0 else STROKE))
        bx = row_layout(texts, x, y, 0)
        why = side.blocked(bx, own=ref)
        if why:
            FAIL.append("top label %s/%s: %s" % (ref, extra, why))
        side.add(bx, "label %s" % (ref or extra))
    for fp in fps.values():
        if fp.GetReference().startswith("H"):
            fp.Reference().SetVisible(False)
            done.add(fp.GetReference())
    order = sorted((f for r, f in fps.items() if r not in done),
                   key=lambda f: (-f.GetCourtyard(p.F_CrtYd).BBox().GetArea(), f.GetPosition().y, f.GetPosition().x))
    for fp in order:
        ref = fp.GetReference()
        r = fp.Reference()
        style(r, p.F_SilkS)
        texts = [r]
        val = value_label(ref)
        if val:
            texts.append(new_text(b, val, p.F_SilkS))
        bb = fp.GetCourtyard(p.F_CrtYd).BBox()
        court = (p.ToMM(bb.GetLeft()), p.ToMM(bb.GetTop()), p.ToMM(bb.GetRight()), p.ToMM(bb.GetBottom()))
        vertical = (court[3] - court[1]) > (court[2] - court[0])
        placed = None
        for cx, cy, angle in candidates(court, texts, vertical, SIDE.get(ref)):
            bx = row_layout(texts, cx, cy, angle)
            if not side.blocked(bx, own=ref):
                placed = bx
                break
        if placed is None:
            FAIL.append("no place for the label of %s" % ref)
            continue
        side.add(placed, "label %s" % ref)


def candidates(court, texts, vertical, only=None):
    """Label positions around a courtyard, nearest first; `only` = one side from SIDE."""
    x0, y0, x1, y1 = court
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for angle in (0, 90):
        w, h = row_size(texts, angle)
        for g in (0.05, 0.3, 0.6, 1.0, 1.5):
            pos = {"above": (cx, y0 - g - h / 2), "below": (cx, y1 + g + h / 2),
                   "left": (x0 - g - w / 2, cy), "right": (x1 + g + w / 2, cy)}
            if only:
                name, a = (only[:-2], 90) if only.endswith("90") else (only, 0)
                if a == angle:
                    yield pos[name] + (angle,)
                continue
            order = ["left", "right", "above", "below"] if vertical else ["above", "below", "left", "right"]
            for name in (["left", "right"] if angle == 90 else order):
                yield pos[name] + (angle,)
            # along the long side, shifted towards either end
            if angle == 0 and not vertical:
                for dx in (-(x1 - x0 - w) / 2, (x1 - x0 - w) / 2):
                    yield cx + dx, pos["above"][1], 0
                    yield cx + dx, pos["below"][1], 0


# ------------------------------------------------------------------ bottom side (view coordinates)
def U(u):
    """Bottom view, seen from below: u runs left to right = KiCad x from the right edge."""
    return B.RIGHT - u


class Bottom:
    def __init__(self, b, side):
        self.b, self.side = b, side

    def text(self, s, u, y, size=TXT, thick=STROKE, align="center", angle=0):
        """align: left/center/right in the bottom view for horizontal text; for vertical text (angle 90)
        'top'/'bottom' means that y is the top/bottom end of the text."""
        t = new_text(self.b, s, p.B_SilkS, size, thick, angle)
        w, _ = extent(t)
        t.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T))
        if angle == 0:
            du = {"center": 0.0, "left": w / 2, "right": -w / 2}[align]
            t.SetPosition(V(U(u + du), y))
        else:
            t.SetPosition(V(U(u), y + {"center": 0.0, "top": w / 2, "bottom": -w / 2}[align]))
        bx = box_of(t)
        why = self.side.blocked(bx)
        if why:
            FAIL.append("bottom text '%s': %s" % (s, why))
        self.side.add(bx, "bottom text '%s'" % s)
        return B.RIGHT - bx[0]  # right end in view coordinates

    def line(self, u0, y0, u1, y1, width=STROKE):
        s = p.PCB_SHAPE(self.b)
        s.SetShape(p.SHAPE_T_SEGMENT)
        s.SetStart(V(U(u0), y0))
        s.SetEnd(V(U(u1), y1))
        s.SetLayer(p.B_SilkS)
        s.SetWidth(mm(width))
        self.b.Add(s)
        bx = box_of(s)
        # lines may meet other lines (frames, grids, the wave); they must clear pads, texts and the edge
        for ob, gap, tag in self.side.items:
            if not tag.startswith("bottom line") and hit(bx, ob, gap):
                FAIL.append("bottom line at %.1f,%.1f: %s" % (u0, y0, tag))
        e = self.side.edge
        if not (e[0] <= bx[0] and bx[2] <= e[2] and e[1] <= bx[1] and bx[3] <= e[3]):
            FAIL.append("bottom line at %.1f,%.1f: board edge" % (u0, y0))
        self.side.items.append((bx, 0.15, "bottom line"))

    def rect(self, u0, y0, u1, y1, width=STROKE):
        for a, b_ in (((u0, y0), (u1, y0)), ((u1, y0), (u1, y1)), ((u1, y1), (u0, y1)), ((u0, y1), (u0, y0))):
            self.line(*a, *b_, width=width)


def place_bottom(b, side):
    bt = Bottom(b, side)
    # jack labels under the jack pads (bottom view is mirrored: LINE OUT is on the right)
    for ref, label in (("J1", "LINE OUT"), ("J2", "LINE IN"), ("J3", "MIC")):
        bt.text(label, B.RIGHT - B.PLACE[ref][0], B.TOP + 12.9)

    # title block
    u0, u1, y0, y1 = 19.0, 93.0, 65.6, 78.0
    bt.rect(u0, y0, u1, y1, 0.2)
    end = bt.text("retro104", u0 + 2.0, y0 + 3.2, size=2.2, thick=0.33, align="left")
    bt.text("pc104-audio rev A", end + 2.0, y0 + 3.5, size=1.5, thick=0.22, align="left")
    bt.text("PC/104 16-bit ISA sound card, ESS ES1868F", u0 + 2.0, y0 + 7.0, size=1.1, thick=0.16, align="left")
    bt.text("SB Pro + ESFM (OPL3) + MPU-401 + game port", u0 + 2.0, y0 + 9.9, align="left")
    # sine wave, right side of the title block
    su0, su1, sy, amp = 74.0, 91.0, (y0 + y1) / 2, 3.2
    pts = [(su0 + (su1 - su0) * i / 48, sy - amp * math.sin(4 * math.pi * i / 48) * (0.35 + 0.65 * math.sin(math.pi * i / 48)))
           for i in range(49)]
    for a, c in zip(pts, pts[1:]):
        bt.line(a[0], a[1], c[0], c[1], 0.25)

    # IRQ / DRQ wiring table
    tu0, ty = 19.0, 80.2
    bt.text("ES1868 lines -> ISA", tu0, ty + 0.8, align="left")
    cw, lw, rh = 4.4, 7.0, 2.3
    for k, (name, lines_, isa) in enumerate((("IRQ", "ABCDEF", (9, 5, 7, 10, 11, 12)), ("DRQ", "ABCD", (0, 1, 3, 5)))):
        top = ty + 2.4 + k * (2 * rh + 1.2)
        right = tu0 + lw + cw * len(lines_)
        bt.rect(tu0, top, right, top + 2 * rh)
        bt.line(tu0, top + rh, right, top + rh)
        bt.line(tu0 + lw, top, tu0 + lw, top + 2 * rh)
        bt.text(name, tu0 + lw / 2, top + rh / 2)
        bt.text("ISA", tu0 + lw / 2, top + rh * 1.5)
        for i, (ln, n) in enumerate(zip(lines_, isa)):
            cu = tu0 + lw + cw * (i + 0.5)
            if i:
                bt.line(tu0 + lw + cw * i, top, tu0 + lw + cw * i, top + 2 * rh)
            bt.text(ln, cu, top + rh / 2)
            bt.text(str(n), cu, top + rh * 1.5)

    # typical PnP resources (README / docs/pc104-audio.md)
    ru0, ry = 56.0, 80.2
    bt.text("Typical resources", ru0, ry + 0.8, align="left")
    cols = (13.5, 7.0, 6.5, 6.5)
    rows = (("", "I/O", "IRQ", "DMA"), ("SB Pro", "220", "5", "1"), ("FM OPL3", "388", "-", "-"),
            ("MPU-401", "330", "-", "-"), ("Game", "201", "-", "-"))
    top = ry + 2.4
    right = ru0 + sum(cols)
    bt.rect(ru0, top, right, top + rh * len(rows))
    for j in range(1, len(rows)):
        bt.line(ru0, top + rh * j, right, top + rh * j)
    acc = ru0
    for c in cols[:-1]:
        acc += c
        bt.line(acc, top, acc, top + rh * len(rows))
    for j, row in enumerate(rows):
        acc = ru0
        for c, cell in zip(cols, row):
            if cell:
                bt.text(cell, acc + c / 2, top + rh * (j + 0.5))
            acc += c

    # jumpers (on the top side next to CN1) and jacks
    ju = 38.5
    bt.text("JP1, JP2 (top): PnP data", ju, 101.0, align="left")
    bt.text("1-2  93C66 U3 (default)", ju, 103.4, align="left")
    bt.text("2-3  ES1868 internal ROM", ju, 105.8, align="left")
    au = 70.5
    bt.text("3.5 mm jacks:", au, 101.0, align="left")
    bt.text("OUT, IN  stereo line", au, 103.4, align="left")
    bt.text("MIC  mono, bias 7.5k", au, 105.8, align="left")
    bt.text("no amplifier, +5 V only", au, 108.2, align="left")

    # bus connector names next to their rows
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    bt.text("CN2 = J1/P1", 17.6, 122.0, angle=-90)
    bt.text("CN1 = J2/P2", 4.6, 123.0, angle=-90)

    # J4 game/MIDI: pin names at the pads, odd row above, even row below (bottom view)
    pads = {int(pd.GetNumber()): pd for pd in fps["J4"].Pads()}
    for n, pd in pads.items():
        u = B.RIGHT - p.ToMM(pd.GetPosition().x)
        y = p.ToMM(pd.GetPosition().y)
        half = p.ToMM(pd.GetSize().y) / 2
        if n % 2:
            bt.text(J4_NAMES[n], u, y - half - 0.35, align="bottom", angle=-90)
        else:
            bt.text(J4_NAMES[n], u, y + half + 0.35, align="top", angle=-90)
    u_pin1 = B.RIGHT - p.ToMM(pads[1].GetPosition().x)
    u_pin15 = B.RIGHT - p.ToMM(pads[15].GetPosition().x)
    y1, y2 = p.ToMM(pads[1].GetPosition().y), p.ToMM(pads[2].GetPosition().y)
    bt.text("1", u_pin1 - 2.2, y1)
    bt.text("2", u_pin1 - 2.2, y2)
    bt.text("15", u_pin15 + 2.6, y1)
    bt.text("16", u_pin15 + 2.6, y2)
    iu = 66.0
    bt.text("J4 GAME / MIDI", iu, 123.2, size=1.2, thick=0.18, align="left")
    bt.text("IDC-16 to DB-15 bracket", iu, 125.6, align="left")
    bt.text("pinout: National AN-1130", iu, 128.0, align="left")
    bt.text("MIN/MOUT = MIDI in/out", iu, 130.4, align="left")
    bt.text("github.com/adsdevdoo/retro104", 51.5, 137.8)


# ------------------------------------------------------------------ final check and save
def final_check(b):
    """All silkscreen texts against each other (both sides) and against pads, independent of placement."""
    for layer, cu in ((p.F_SilkS, p.F_Cu), (p.B_SilkS, p.B_Cu)):
        texts = []
        for d in b.GetDrawings():
            if d.GetLayer() == layer and d.GetClass() == "PCB_TEXT":
                texts.append((box_of(d), "'%s'" % d.GetText()))
        for fp in b.GetFootprints():
            for f in (fp.Reference(), fp.Value()):
                if f.IsVisible() and f.GetLayer() == layer:
                    texts.append((box_of(f), "%s field '%s'" % (fp.GetReference(), f.GetText())))
            for g in fp.GraphicalItems():
                if g.GetClass() == "PCB_TEXT" and g.GetLayer() == layer and g.IsVisible():
                    texts.append((box_of(g), "%s text '%s'" % (fp.GetReference(), g.GetText())))
        pads = [(box_of(pd), "%s.%s" % (fp.GetReference(), pd.GetNumber()))
                for fp in b.GetFootprints() for pd in fp.Pads() if pd.IsOnLayer(cu)]
        for i, (a, ta) in enumerate(texts):
            for c, tc in texts[i + 1:]:
                if hit(a, c, 0.15):
                    FAIL.append("%s overlaps %s" % (ta, tc))
            for c, tc in pads:
                if hit(a, c, 0.15):
                    FAIL.append("%s on pad %s" % (ta, tc))


def stable_uuids(path):
    """Make reruns give the same file. KiCad orders board graphics with the (random) UUID as a tie
    breaker, so the top-level gr_* blocks are sorted by their content and then numbered."""
    lines = open(path, encoding="utf-8").read().split("\n")
    blocks, i, first, last = [], 0, None, None
    while i < len(lines):
        if re.match(r"^\t\(gr_\w+", lines[i]):
            j = i
            while lines[j] != "\t)":
                j += 1
            if last is not None and i != last + 1:
                raise SystemExit("board graphics are not contiguous in %s" % path)
            first = i if first is None else first
            blocks.append(lines[i:j + 1])
            last, i = j, j + 1
            continue
        i += 1
    if not blocks:
        return
    key = [("\n".join(x for x in blk if not x.startswith("\t\t(uuid ")), blk) for blk in blocks]
    out = []
    for n, (_, blk) in enumerate(sorted(key, key=lambda kv: kv[0])):
        out += ['\t\t(uuid "%s")' % uid("pc104-audio:gr:%d" % n) if x.startswith("\t\t(uuid ") else x for x in blk]
    lines[first:last + 1] = out
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def main():
    b = p.LoadBoard(PCB)
    for d in list(b.GetDrawings()):
        if d.GetLayer() in (p.F_SilkS, p.B_SilkS):
            b.Delete(d)
    for fp in b.GetFootprints():
        fp.Value().SetVisible(False)
    place_top(b, Side(b, p.F_Cu, p.F_SilkS, p.F_CrtYd))
    place_bottom(b, Side(b, p.B_Cu, p.B_SilkS, None))
    final_check(b)
    p.SaveBoard(PCB, b, True)  # True: keep the .kicad_pro as it is
    stable_uuids(PCB)
    n_top = sum(1 for f in b.GetFootprints() if f.Reference().IsVisible() and f.Reference().GetLayer() == p.F_SilkS)
    print("silkscreen: %d references on top, %d board texts" % (
        n_top, sum(1 for d in b.GetDrawings() if d.GetClass() == "PCB_TEXT")))
    if FAIL:
        print("SILKSCREEN PROBLEMS:\n  " + "\n  ".join(FAIL))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
