"""PC/104 16-bit bus: mechanical geometry and signal tables.

Every number here is taken from a document stored in docs/datasheets/ (page given in comments).
Nothing in this file may be "adjusted" to make a check pass: fix the generator, not the data.

Coordinate system = PC/104 Specification v2.6, Figure 3 (p. A-3), top (component) side view:
origin in the corner next to J1 pin 1, X grows away from the bus-connector edge, Y grows along
the connectors from pin 1 towards pin 32. Units: inches, as in the drawing.
"""

IN = 25.4  # mm per inch

# --- Module outline and mounting holes (PC/104 v2.6 Fig. 3, p. A-3) -------------------------------
BOARD_X_IN = 3.775  # 95.89 mm, perpendicular to the bus connectors
BOARD_Y_IN = 3.550  # 90.17 mm, along the bus connectors
BOARD_THICKNESS_MM = 1.57  # .062 (1.57) in Fig. 3 side view; JLCPCB 1.6 mm is used
# 4 holes: ".250 (6.35) DIA PAD, .12 (3.18) DIA HOLE, TYP 4 PLACES"
HOLES_IN = [
    (0.200, 0.200),  # next to J1 pin 1 end
    (0.200, 3.350),  # next to J1 pin 32 end
    (3.575, 0.350),  # far side; NOTE: Y differs from the near pair (0.350 vs 0.200)
    (3.575, 3.250),  # far side; Y 3.250 vs 3.350
]
HOLE_DRILL_MM = 3.18
HOLE_PAD_MM = 6.35
STANDOFF_MM = 15.24  # .600 +/- .005 (PC/104 v2.6 Fig. 1 p. 3 and Fig. 7 p. D-2)

# --- Bus connectors (Fig. 3 p. A-3 and Fig. 4 p. A-4) --------------------------------------------
# J1/P1: rows A (X .400) and B (X .500), pins 1..32, pin 1 at Y .250, pitch .100.
# J2/P2: rows C and D at .100 pitch next to J1 towards the edge (Fig. 3: B A C D, D at X .200).
# Fig. 4: J2 first pin is .800 from J1 first pin, J2 last pin .400 from J1 last pin -> C0/D0 at
# Y .250 + .800 = 1.050, C19/D19 at 2.950. Fig. 3 marks the J2 pin-1 end near J1 pin 1.
J1_ROW_X_IN = {"A": 0.400, "B": 0.500}
J2_ROW_X_IN = {"C": 0.300, "D": 0.200}
J1_PINS = range(1, 33)
J2_PINS = range(0, 20)


def j1_y_in(n):
    return 0.250 + 0.100 * (n - 1)


def j2_y_in(n):
    return 1.050 + 0.100 * n


# Connector bodies (Fig. 4): 2-row body .195 wide, J1 3.220 long, pins .06 from the body ends,
# height above board .435 (11.05); stackthrough tail .480 (12.19), .025 (0.64) square.
BODY_W_IN = 0.195
BODY_END_IN = 0.060
BODY_H_MM = 11.05
TAIL_MM = 12.19
TAIL_SQ_MM = 0.64

# Samtec ESQ recommended PC board layout (ESQ-SDT): .040 [1.02] DIA (TYP).
CONNECTOR_DRILL_MM = 1.02
CONNECTOR_PAD_MM = 1.70  # annular ring 0.34 mm; 0.84 mm copper gap at 2.54 mm pitch

# Key locations (v2.6 Table 2 note 2, Section 2.3): omitted pins on P1/P2, plugged holes on J1/J2.
KEY_PADS = ("B10", "C19")

# --- Signal names: PC/104 Specification v2.6, Table 2 (p. B-2) -----------------------------------
SPEC = {
    "A": ["IOCHK*", "SD7", "SD6", "SD5", "SD4", "SD3", "SD2", "SD1", "SD0", "IOCHRDY", "AEN",
          "SA19", "SA18", "SA17", "SA16", "SA15", "SA14", "SA13", "SA12", "SA11", "SA10", "SA9",
          "SA8", "SA7", "SA6", "SA5", "SA4", "SA3", "SA2", "SA1", "SA0", "GND"],
    "B": ["GND", "RESET", "+5V", "IRQ9", "-5V", "DRQ2", "-12V", "SRDY*", "+12V", "KEY", "SMEMW*",
          "SMEMR*", "IOW*", "IOR*", "DACK3*", "DRQ3", "DACK1*", "DRQ1", "REFRESH*", "BCLK", "IRQ7",
          "IRQ6", "IRQ5", "IRQ4", "IRQ3", "DACK2*", "TC", "BALE", "+5V", "OSC", "GND", "GND"],
    "C": ["GND", "SBHE*", "LA23", "LA22", "LA21", "LA20", "LA19", "LA18", "LA17", "MEMR*", "MEMW*",
          "SD8", "SD9", "SD10", "SD11", "SD12", "SD13", "SD14", "SD15", "KEY"],
    "D": ["GND", "MEMCS16*", "IOCS16*", "IRQ10", "IRQ11", "IRQ12", "IRQ15", "IRQ14", "DACK0*", "DRQ0",
          "DACK5*", "DRQ5", "DACK6*", "DRQ6", "DACK7*", "DRQ7", "+5V", "MASTER16*", "GND", "GND"],
}

# --- Advantech PCM-3864/3860 User's Manual ed.1, Appendix C p. 67 "PC/104 connectors (CN1, CN2)" ---
# Advantech CN2 = 64-pin connector (PC/104 J1, rows A/B 1..32).
# Advantech CN1 = 40-pin connector, its "Row A / Row B" are PC/104 rows C / D (pins 0..19).
ADVANTECH = {
    "A": ["IOCHCHK", "SD7", "SD6", "SD5", "SD4", "SD3", "SD2", "SD1", "SD0", "IOCHRDY", "AEN",
          "SA19", "SA18", "SA17", "SA16", "SA15", "SA14", "SA13", "SA12", "SA11", "SA10", "SA9",
          "SA8", "SA7", "SA6", "SA5", "SA4", "SA3", "SA2", "SA1", "SA0", "0 V"],
    "B": ["0 V", "RESETDRV", "+5 V", "IRQ9", "-5 V", "DRQ2", "-12 V", "ENDXFR", "+12 V", "GND", "SMEMW",
          "SMEMR", "IOW", "IOR", "DACK3", "DRQ3", "DACK1", "DRQ1", "REFRESH", "SYSCLK", "IRQ7",
          "IRQ6", "IRQ5", "IRQ4", "IRQ3", "DACK2", "TC", "BALE", "+5 V", "OSC", "0 V", "0 V"],
    "C": ["0 V", "SBHE", "LA23", "LA22", "LA21", "LA20", "LA19", "LA18", "LA17", "MEMR", "MEMW",
          "SD8", "SD9", "SD10", "SD11", "SD12", "SD13", "SD14", "SD15", "N/C"],
    "D": ["0 V", "MEMCS16", "IOCS16", "IRQ10", "IRQ11", "IRQ12", "IRQ15", "IRQ14", "DACK0", "DRQ0",
          "DACK5", "DRQ5", "DACK6", "DRQ6", "DACK7", "DRQ7", "+5 V", "MASTER", "0 V", "0 V"],
}
ADVANTECH_CN = {"A": "CN2", "B": "CN2", "C": "CN1", "D": "CN1"}
ADVANTECH_ROW = {"A": "Row A", "B": "Row B", "C": "Row A", "D": "Row B"}

# Renames listed in PC/104 v2.5 revision history (v2.6 p. ii, item b): same signal, new name.
RENAMED = {"IOCHCHK": "IOCHK", "RESETDRV": "RESET", "ENDXFR": "SRDY", "SYSCLK": "BCLK",
           "MASTER": "MASTER16"}

# Where the PC/104 J1/J2 sit on the Advantech board (CN numbering differs from J numbering).
CN_OF_J = {"J1": "CN2", "J2": "CN1"}


def first_pin(row):
    return 1 if row in "AB" else 0


def pad_list(rows):
    """[(pad, row, n, x_in, y_in, spec_name)] for the given rows."""
    out = []
    for row in rows:
        names = SPEC[row]
        for i, name in enumerate(names):
            n = i + first_pin(row)
            if row in "AB":
                x, y = J1_ROW_X_IN[row], j1_y_in(n)
            else:
                x, y = J2_ROW_X_IN[row], j2_y_in(n)
            out.append(("%s%d" % (row, n), row, n, x, y, name))
    return out


def normalize(name):
    """Compare names across documents: drop active-low marks, spaces, map 0 V -> GND, renames."""
    s = name.replace("*", "").replace(" ", "").upper()
    if s == "0V":
        s = "GND"
    return RENAMED.get(s, s)


def kicad_pin_name(name):
    """PC/104 'NAME*' (active low) -> KiCad overbar '~{NAME}'."""
    return "~{%s}" % name[:-1] if name.endswith("*") else name
