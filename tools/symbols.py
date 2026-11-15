"""Schematic symbols of the shared retro104 library (KiCad 9 S-expressions).

Each symbol is described by data: pins = [(number, name, type, x, y, angle)] in symbol coordinates
(mm, y up; angle 0 = pin points right, i.e. connection point on the left). The same data is used
by the schematic generators to attach wire stubs and net labels, so pin positions cannot drift
from the drawn symbols.
"""

from sexpr import Q

P = 2.54
FONT = ["effects", ["font", ["size", 1.27, 1.27]]]


def prop(name, value, x, y, hide=False, justify=None):
    eff = ["effects", ["font", ["size", 1.27, 1.27]]]
    if justify:
        eff.append(["justify", justify])
    if hide:
        eff.append(["hide", "yes"])
    return ["property", Q(name), Q(value), ["at", x, y, 0], eff]


class Sym:
    def __init__(self, name, ref, value, footprint, datasheet="", description="", in_bom=True,
                 power=False, keywords=""):
        self.name, self.ref, self.value, self.footprint = name, ref, value, footprint
        self.datasheet, self.description, self.in_bom, self.power = datasheet, description, in_bom, power
        self.keywords = keywords
        self.pins = []  # (number, name, type, x, y, angle, length)
        self.graphics = []
        self.ref_at = (0, 0)
        self.value_at = (0, 0)
        self.hide_pin_numbers = False
        self.hide_pin_names = False

    def pin(self, number, name, ptype, x, y, angle, length=P):
        self.pins.append((str(number), name, ptype, x, y, angle, length))

    def node(self, prefix=""):
        n = ["symbol", Q(prefix + self.name)]
        if self.power:
            n.append(["power"])
        if self.hide_pin_numbers:
            n.append(["pin_numbers", ["hide", "yes"]])
        pn = ["pin_names", ["offset", 0.508]]
        if self.hide_pin_names:
            pn.append(["hide", "yes"])
        n.append(pn)
        n += [["exclude_from_sim", "no"], ["in_bom", "yes" if self.in_bom else "no"], ["on_board", "no" if self.power else "yes"],
              prop("Reference", self.ref, *self.ref_at, hide=self.power),
              prop("Value", self.value, *self.value_at),
              prop("Footprint", self.footprint, 0, 0, True),
              prop("Datasheet", self.datasheet, 0, 0, True),
              prop("Description", self.description, 0, 0, True)]
        if self.keywords:
            n.append(prop("ki_keywords", self.keywords, 0, 0, True))
        n.append(["symbol", Q(self.name + "_0_1")] + self.graphics)
        unit = ["symbol", Q(self.name + "_1_1")]
        for num, name, ptype, x, y, angle, length in self.pins:
            unit.append(["pin", ptype, "line", ["at", x, y, angle], ["length", length],
                         ["name", Q(name), FONT], ["number", Q(num), FONT]])
        n.append(unit)
        n.append(["embedded_fonts", "no"])
        return n


def rect(x0, y0, x1, y1, fill="background", width=0.254):
    return ["rectangle", ["start", x0, y0], ["end", x1, y1], ["stroke", ["width", width], ["type", "default"]],
            ["fill", ["type", fill]]]


def poly(points, width=0.254, fill="none"):
    return ["polyline", ["pts"] + [["xy", x, y] for x, y in points],
            ["stroke", ["width", width], ["type", "default"]], ["fill", ["type", fill]]]


def two_pin(name, ref, value, footprint, body, description="", datasheet="", polarized=False):
    """Horizontal 2-pin part: pin 1 on the left (x=-5.08), pin 2 on the right (x=+5.08)."""
    s = Sym(name, ref, value, footprint, datasheet, description)
    s.hide_pin_names = True
    s.hide_pin_numbers = True
    s.ref_at, s.value_at = (0, 2.54), (0, -2.54)
    s.pin(1, "~" if not polarized else "+", "passive", -5.08, 0, 0, 2.54)
    s.pin(2, "~" if not polarized else "-", "passive", 5.08, 0, 180, 2.54)
    if body == "R":
        s.graphics = [rect(-2.54, -0.889, 2.54, 0.889, fill="none")]
    elif body == "C":
        s.graphics = [poly([(-0.635, -1.524), (-0.635, 1.524)], 0.508), poly([(0.635, -1.524), (0.635, 1.524)], 0.508),
                      poly([(-2.54, 0), (-0.635, 0)]), poly([(0.635, 0), (2.54, 0)])]
    elif body == "CP":
        s.graphics = [rect(-1.016, -1.778, -0.508, 1.778, fill="none"), rect(0.508, -1.778, 1.016, 1.778, fill="outline"),
                      poly([(-2.54, 0), (-1.016, 0)]), poly([(1.016, 0), (2.54, 0)]),
                      poly([(-2.286, 1.27), (-1.778, 1.27)]), poly([(-2.032, 1.524), (-2.032, 1.016)])]
    elif body == "FB":
        s.graphics = [poly([(-2.54, 0), (-1.27, 0)]), poly([(1.27, 0), (2.54, 0)]),
                      poly([(-1.778, -0.762), (-0.762, 1.016), (1.778, 0.762), (0.762, -1.016), (-1.778, -0.762)])]
    elif body == "XTAL":
        s.graphics = [rect(-0.762, -1.524, 0.762, 1.524, fill="none"), poly([(-1.524, -1.016), (-1.524, 1.016)], 0.508),
                      poly([(1.524, -1.016), (1.524, 1.016)], 0.508), poly([(-2.54, 0), (-1.524, 0)]),
                      poly([(1.524, 0), (2.54, 0)])]
    return s


def box(name, ref, value, footprint, left=(), right=(), top=(), bottom=(), width=None, description="",
        datasheet="", keywords="", pin_len=P):
    """Rectangular IC/connector symbol. Side lists hold (number, name, type) or None for a gap."""
    rows = max(len(left), len(right), 1)
    cols = max(len(top), len(bottom), 0)
    w = width or max(15.24, (cols + 1) * P)
    w = round(w / (2 * P) + 0.4999) * 2 * P  # keep pin ends on the 2.54 grid
    h = (rows + 1) * P
    x0, x1 = -w / 2, w / 2
    ytop = (rows - 1) / 2 * P
    ytop = round(ytop / P) * P
    y0, y1 = ytop + P, ytop - rows * P
    s = Sym(name, ref, value, footprint, datasheet, description, keywords=keywords)
    s.graphics = [rect(x0, y0, x1, y1)]
    s.ref_at = (0, y0 + (len(top) and pin_len) + 1.27)
    s.value_at = (0, y1 - (len(bottom) and pin_len) - 1.27)
    for i, p in enumerate(left):
        if p:
            s.pin(p[0], p[1], p[2], x0 - pin_len, ytop - i * P, 0, pin_len)
    for i, p in enumerate(right):
        if p:
            s.pin(p[0], p[1], p[2], x1 + pin_len, ytop - i * P, 180, pin_len)
    for side, lst, yy, ang in (("top", top, y0 + pin_len, 270), ("bottom", bottom, y1 - pin_len, 90)):
        n = len(lst)
        start = -((n - 1) / 2) * P
        start = round(start / P) * P
        for i, p in enumerate(lst):
            if p:
                s.pin(p[0], p[1], p[2], start + i * P, yy, ang, pin_len)
    return s


# ------------------------------------------------------------------------------------------------
FP = "retro104:"
DS = "${KIPRJMOD}/../../docs/datasheets/"


def es1868():
    I, O, B, Pw, Pa = "input", "output", "bidirectional", "power_in", "passive"
    T = "tri_state"
    left = [(99, "A0", I), (100, "A1", I), (1, "A2", I), (2, "A3", I), (4, "A4", I), (5, "A5", I), (6, "A6", I),
            (8, "A7", I), (9, "A8", I), (10, "A9", I), (97, "A10", I), (98, "A11", I), None,
            (12, "D0", B), (13, "D1", B), (14, "D2", B), (15, "D3", B), (16, "D4", B), (17, "D5", B),
            (18, "D6", B), (19, "D7", B), None,
            (11, "AEN", I), (75, "~{IORB}", I), (76, "~{IOWB}", I), (81, "RESET", I), None,
            (74, "IRQA", T), (73, "IRQB", T), (72, "IRQC", T), (71, "IRQD", T), (70, "IRQE", T), (69, "IRQF", T), None,
            (67, "DRQA", T), (68, "~{DACKBA}", I), (65, "DRQB", T), (66, "~{DACKBB}", I),
            (63, "DRQC", T), (64, "~{DACKBC}", I), (61, "DRQD", T), (62, "~{DACKBD}", I)]
    right = [(50, "AOUT_L", Pa), (51, "AOUT_R", Pa), None, (48, "LINE_L", Pa), (49, "LINE_R", Pa), (40, "MIC", Pa),
             (37, "AUXA_L", Pa), (38, "AUXA_R", Pa), (35, "AUXB_L/FDXI", Pa), (36, "AUXB_R/FDXO", Pa), None,
             (45, "FOUT_L", Pa), (46, "CIN_L", Pa), (44, "FOUT_R", Pa), (47, "CIN_R", Pa), (39, "CMR", Pa),
             (42, "VREF", Pa), None,
             (30, "TA", B), (29, "TB", B), (28, "TC", B), (27, "TD", B), (31, "~{SWA}", I), (32, "~{SWB}", I),
             (33, "~{SWC}", I), (34, "~{SWD}", I), (58, "MSO", O), (59, "MSI", I), None,
             (20, "SECS/PSEL0", B), (23, "SECLK/~{MUTE}", B), (22, "SEDI/~{VOLUP}", B), (21, "SEDO/~{VOLDN}", I),
             (25, "PSEL1", I), None, (78, "XI", I), (79, "XO", O)]
    top = [(3, "VDDD", Pw), (26, "VDDD", Pw), (57, "VDDD", Pw), (80, "VDDD", Pw), None, (43, "VDDA", Pw)]
    bottom = [(7, "GNDD", Pw), (24, "GNDD", Pw), (52, "GNDD", Pw), (60, "GNDD", Pw), (77, "GNDD", Pw), None,
              (41, "GNDA", Pw), None,
              (53, "~{MMIEB}", I), (54, "MMIRQ", I), (55, "~{MMCSB}", O), (56, "GPO0/GPCS", O),
              (91, "GPO1/GPDACK", O), (92, "GPI/GPDRQ", I), (93, "CDIRQ", I), (94, "~{CDCSB0}", O),
              (95, "~{CDCSB1}", O), (96, "CDENBL", O), (90, "RSTB", O),
              (82, "FSR", I), (83, "FSX", I), (84, "DCLK", I), (85, "DR", I), (86, "DX", T),
              (87, "MSD", I), (88, "MCLK", I), (89, "SE", I)]
    s = box("ES1868", "U", "ES1868F", FP + "PQFP-100_14x20mm_P0.65mm", left, right, top, bottom, width=78.74,
            description="ESS ES1868 AudioDrive: SB Pro, ESFM (OPL3), MPU-401, game port, ISA PnP. "
                        "Pins: ES1868 data sheet Table 1/2, p. 5-8. SEDI (22) typed bidirectional: Table 2 says input, but in EEPROM mode it drives the EEPROM DI pin (Fig. 15, Fig. 28)", datasheet=DS + "ess-es1868-datasheet.pdf",
            keywords="ESS AudioDrive sound ISA")
    return s


def hct138():
    I, O, Pw = "input", "output", "power_in"
    left = [(1, "A", I), (2, "B", I), (3, "C", I), None, (6, "G1", I), (4, "~{G2A}", I), (5, "~{G2B}", I)]
    right = [(15, "~{Y0}", O), (14, "~{Y1}", O), (13, "~{Y2}", O), (12, "~{Y3}", O), (11, "~{Y4}", O),
             (10, "~{Y5}", O), (9, "~{Y6}", O), (7, "~{Y7}", O)]
    return box("74HCT138", "U", "74HCT138", FP + "SOIC-16_3.9x9.9mm_P1.27mm", left, right,
               top=[(16, "VCC", Pw)], bottom=[(8, "GND", Pw)], width=15.24,
               description="3-to-8 decoder; ES1868 reference design U2 (74LS138). TI SN74HCT138",
               datasheet=DS + "ti-sn74hct138.pdf")


def eeprom93c66():
    I, O, Pw = "input", "output", "power_in"
    left = [(1, "CS", I), (2, "CLK", I), (3, "DI", I), (4, "DO", "tri_state")]
    right = [(6, "ORG", I), (7, "NC", "no_connect")]
    return box("93C66", "U", "93C66", FP + "DIP-8_W7.62mm_Socket_LongPads", left, right,
               top=[(8, "VCC", Pw)], bottom=[(5, "GND", Pw)], width=15.24,
               description="4 Kbit Microwire EEPROM, ORG=GND -> 512 x 8 (ES1868 data sheet Fig. 15). "
                           "Donor: Atmel AT93C66 from BTC 1853L", datasheet=DS + "microchip-93aa66-93lc66-93c66.pdf")


def jack_trs(name="Jack_TRS"):
    s = box(name, "J", "SJ1-3523N", FP + "Jack_3.5mm_CUI_SJ1-3523N_Horizontal_Slots",
            left=[("T", "TIP", "passive"), ("R", "RING", "passive"), ("S", "SLEEVE", "passive")], width=10.16,
            description="3.5 mm TRS jack, CUI/Same Sky SJ1-3523N (1 sleeve, 2 tip, 3 ring)",
            datasheet=DS + "cui-sj1-352xn.pdf")
    return s


def header_2x8():
    left = [(n, "", "passive") for n in range(1, 16, 2)]
    right = [(n, "", "passive") for n in range(2, 17, 2)]
    s = box("Conn_02x08_Odd_Even", "J", "Conn_02x08", FP + "IDC-Header_2x08_P2.54mm_Horizontal", left, right,
            width=10.16, description="2x8 IDC box header, right angle, 2.54 mm")
    s.hide_pin_names = True
    return s


def solder_jumper3():
    s = box("SolderJumper_3_Bridged12", "JP", "SolderJumper_3", FP + "SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm",
            left=[(1, "1", "passive")], right=[(3, "3", "passive")], bottom=[(2, "2", "passive")], width=10.16,
            description="3-pad solder jumper, pads 1-2 bridged by copper")
    s.in_bom = False
    return s


def pwr_flag():
    s = Sym("PWR_FLAG", "#FLG", "PWR_FLAG", "", description="Marks a net as driven by a power source", power=True)
    s.hide_pin_numbers = True
    s.hide_pin_names = True
    s.ref_at, s.value_at = (0, 1.905), (0, 3.81)
    s.pin(1, "~", "power_out", 0, 0, 90, 0)
    s.graphics = [poly([(0, 0), (0, 1.27), (-1.016, 1.905), (0, 2.54), (1.016, 1.905), (0, 1.27)])]
    return s


def generic_parts():
    return [
        two_pin("R", "R", "R", FP + "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", "R", "Resistor 0805"),
        two_pin("C", "C", "C", FP + "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", "C", "Ceramic capacitor 0805"),
        two_pin("CP", "C", "CP", FP + "CP_Elec_4x5.4", "CP", "Aluminium electrolytic, SMD", polarized=True),
        two_pin("FerriteBead", "FB", "FerriteBead", FP + "L_0805_2012Metric_Pad1.15x1.40mm_HandSolder", "FB",
                "Ferrite bead 0805"),
        two_pin("Crystal", "Y", "14.31818MHz", FP + "Crystal_HC49-4H_Vertical", "XTAL", "Quartz crystal"),
    ]


def audio_symbols():
    return generic_parts() + [es1868(), hct138(), eeprom93c66(), jack_trs(), header_2x8(), solder_jumper3(),
                              pwr_flag()]
