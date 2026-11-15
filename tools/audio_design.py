"""pc104-audio rev A: parts and connections (single source for schematic, board and checks).

Circuit = ESS ES1868 data sheet, Appendix B (Fig. 28 ES1868 schematic, Fig. 29 PC interface,
Fig. 31 line out), with the owner's decisions of 2026-11-15 (docs/audio-options.md):
  * line output only (no LM1877/TEA2025 amplifier), line in + mic, no CD-in, no IDE, no wavetable,
    no modem, no hardware volume buttons;
  * VDDA from bus +5 V through a ferrite bead and capacitors instead of the 78L05 from +12 V;
  * game/MIDI on a right-angle 2x8 IDC header (pinout: National AN-1130 p. 1 / standard
    ribbon-to-DB15 game cable), IRQ/DMA wiring exactly as the ESS reference
    (IRQA..F = 9, 5, 7, 10, 11, 12; DRQA..D = 0, 1, 3, 5), which is also what the PnP EEPROM of
    generic ES1868 cards declares (header A5 59 A7 CB 10 53, data sheet Appendix A).
Net names are plain ASCII (DSN/SES safe): active-low bus signals end in _N.
"""

import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pc104_data as D  # noqa: E402

PARTS = OrderedDict()  # ref -> dict(sym, value, fp, mpn, note)
NETS = OrderedDict()  # net -> [(ref, pin)]
NC = []  # (ref, pin) intentionally unconnected

FP = "retro104:"
R0805 = FP + "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"
C0805 = FP + "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder"


def part(ref, sym, value, fp=None, mpn="", note=""):
    PARTS[ref] = dict(sym=sym, value=value, fp=fp, mpn=mpn, note=note)


def c(net, *pins):
    for p in pins:
        ref, pin = p.split(".", 1)
        NETS.setdefault(net, []).append((ref, pin))


def two(ref, sym, value, net1, net2, fp=None, mpn="", note=""):
    part(ref, sym, value, fp, mpn, note)
    c(net1, ref + ".1")
    c(net2, ref + ".2")


# ------------------------------------------------------------------ PC/104 bus (CN2 = J1, CN1 = J2)
BUS_SIGNALS = {"SD%d" % i for i in range(8)} | {"SA%d" % i for i in range(16)} | {
    "AEN", "RESET", "IOR*", "IOW*", "IRQ5", "IRQ7", "IRQ9", "IRQ10", "IRQ11", "IRQ12",
    "DRQ0", "DRQ1", "DRQ3", "DRQ5", "DACK0*", "DACK1*", "DACK3*", "DACK5*", "+5V", "GND"}


def bus_net(spec_name):
    return spec_name.replace("*", "_N")


part("CN2", "PC104_J1P1", "ESQ-132-39-G-D", mpn="Samtec ESQ-132-39-G-D",
     note="PC/104 J1/P1 stackthrough; Advantech name CN2")
part("CN1", "PC104_J2P2", "ESQ-120-39-G-D", mpn="Samtec ESQ-120-39-G-D",
     note="PC/104 J2/P2 stackthrough; Advantech name CN1")
for pad, row, n, _x, _y, name in D.pad_list("ABCD"):
    ref = "CN2" if row in "AB" else "CN1"
    if name in BUS_SIGNALS:
        c(bus_net(name), "%s.%s" % (ref, pad))
    else:
        NC.append((ref, pad))

# ------------------------------------------------------------------ ES1868 (U1)
part("U1", "ES1868", "ES1868F", mpn="ESS ES1868F", note="from donor BTC 1853L")
U1 = {
    # ISA (Fig. 28): A[11:0], D[7:0], AEN via 74x138 (full 16-bit I/O decode), strobes, reset
    99: "SA0", 100: "SA1", 1: "SA2", 2: "SA3", 4: "SA4", 5: "SA5", 6: "SA6", 8: "SA7", 9: "SA8", 10: "SA9",
    97: "SA10", 98: "SA11", 12: "SD0", 13: "SD1", 14: "SD2", 15: "SD3", 16: "SD4", 17: "SD5", 18: "SD6",
    19: "SD7", 11: "ES_AEN", 75: "IOR_N", 76: "IOW_N", 81: "RESET",
    # IRQ/DMA (Fig. 28/29)
    74: "IRQ9", 73: "IRQ5", 72: "IRQ7", 71: "IRQ10", 70: "IRQ11", 69: "IRQ12",
    67: "DRQ0", 68: "DACK0_N", 65: "DRQ1", 66: "DACK1_N", 63: "DRQ3", 64: "DACK3_N", 61: "DRQ5", 62: "DACK5_N",
    # power
    3: "+5V", 26: "+5V", 57: "+5V", 80: "+5V", 43: "+5VA",
    7: "GND", 24: "GND", 52: "GND", 60: "GND", 77: "GND", 41: "GND",
    # analog
    39: "CMR", 42: "VREF", 40: "MIC_IN", 48: "LINE_L", 49: "LINE_R", 45: "FOUT_L", 46: "CIN_L",
    44: "FOUT_R", 47: "CIN_R", 50: "AOUT_L", 51: "AOUT_R",
    # game port and MIDI
    30: "TA", 29: "TB", 28: "TC", 27: "TD", 31: "SWA", 32: "SWB", 33: "SWC", 34: "SWD",
    58: "MSO", 59: "MSI",
    # PnP EEPROM (Fig. 15/28)
    20: "EE_CS", 23: "EE_CLK", 22: "EE_DI", 21: "EE_DO", 25: "PSEL1",
    # crystal, unused inputs with pull-downs as in Fig. 28
    78: "XI", 79: "XO", 92: "GPI", 93: "CDIRQ",
}
for pin, net in U1.items():
    c(net, "U1.%d" % pin)
# Not used (left open in ESS Fig. 28 as well): AUX inputs (internal pull-ups to CMR), modem pins,
# DSP serial interface and wavetable inputs (internal pull-downs), CD-ROM chip selects, GPO0/GPO1, RSTB.
for pin in (35, 36, 37, 38, 53, 54, 55, 56, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 94, 95, 96):
    NC.append(("U1", str(pin)))
assert len(U1) + 21 == 100

# ------------------------------------------------------------------ address decode, EEPROM, crystal
part("U2", "74HCT138", "74HCT138", mpn="TI SN74HCT138D", note="donor has 74LS138, either works")
for pin, net in {1: "SA15", 2: "SA14", 3: "SA13", 4: "SA12", 5: "AEN", 6: "+5V", 15: "ES_AEN",
                 16: "+5V", 8: "GND"}.items():
    c(net, "U2.%d" % pin)
for pin in (14, 13, 12, 11, 10, 9, 7):
    NC.append(("U2", str(pin)))

part("U3", "93C66", "93C66", mpn="Atmel AT93C66 (donor) in DIP-8 socket", note="PnP resource EEPROM, ORG=GND (x8)")
for pin, net in {1: "EE_CS", 2: "EE_CLK", 3: "EE_DI", 4: "EE_DO", 5: "GND", 6: "GND", 8: "+5V"}.items():
    c(net, "U3.%d" % pin)
NC.append(("U3", "7"))

part("JP1", "SolderJumper_3_Bridged12", "PSEL1", note="1-2 = H = 93C66, 2-3 = L = internal ROM")
c("+5V", "JP1.1"), c("PSEL1", "JP1.2"), c("GND", "JP1.3")
part("JP2", "SolderJumper_3_Bridged12", "PSEL0", note="1-2 = H = 93C66, 2-3 = L = internal ROM")
c("+5V", "JP2.1"), c("PSEL0_SEL", "JP2.2"), c("GND", "JP2.3")
two("R1", "R", "1k", "PSEL0_SEL", "EE_CS", note="Fig. 28 R14")

part("Y1", "Crystal", "14.31818MHz", mpn="HC-49/S 14.31818 MHz, CL 18-20 pF",
     note="donor crystal is HC-49/U (13.5 mm tall): too high for PC/104 standing, lay it flat")
c("XI", "Y1.1"), c("XO", "Y1.2")
two("C23", "C", "10pF", "XI", "GND", note="Fig. 28 C15")
two("C24", "C", "10pF", "XO", "GND", note="Fig. 28 C16")
two("R4", "R", "10k", "GPI", "GND", note="Fig. 28 R7")
two("R5", "R", "10k", "CDIRQ", "GND", note="CD-ROM IRQ input held inactive (no IDE on this board)")

# ------------------------------------------------------------------ power
for ref in ("C1", "C2", "C3", "C4"):
    two(ref, "C", "0.1uF", "+5V", "GND", note="VDDD decoupling")
two("C5", "C", "0.1uF", "+5V", "GND", note="U2 decoupling")
two("C6", "C", "0.1uF", "+5V", "GND", note="U3 decoupling")
two("C7", "CP", "10uF 16V", "+5V", "GND", fp=FP + "CP_Elec_4x5.4", note="bulk +5V")
two("FB1", "FerriteBead", "600R@100MHz", "+5V", "+5VA", note="VDDA filter (replaces 78L05 from +12 V)")
two("C8", "CP", "10uF 16V", "+5VA", "GND", fp=FP + "CP_Elec_4x5.4", note="Fig. 28 C12")
two("C9", "C", "0.1uF", "+5VA", "GND", note="Fig. 28 C5")

# ------------------------------------------------------------------ analog (Fig. 28, Fig. 31, p. 28)
two("C10", "CP", "47uF 16V", "CMR", "GND", fp=FP + "CP_Elec_6.3x5.4", note="Fig. 28 C14 (CMR 47 uF)")
two("C11", "C", "0.1uF", "CMR", "GND", note="Fig. 28 C7")
two("C12", "C", "0.1uF", "VREF", "GND", note="Fig. 28 C11")
two("C13", "C", "0.22uF", "FOUT_L", "CIN_L", note="Fig. 28 C8")
two("C14", "C", "1nF", "CIN_L", "GND", note="Fig. 28 C33")
two("C15", "C", "0.22uF", "FOUT_R", "CIN_R", note="Fig. 28 C9")
two("C16", "C", "1nF", "CIN_R", "GND", note="Fig. 28 C10")
two("C17", "C", "0.22uF", "LI_L", "LINE_L", note="Fig. 28 C27")
two("C18", "C", "0.22uF", "LI_R", "LINE_R", note="Fig. 28 C28")
two("R2", "R", "7.5k", "+5VA", "MIC_BIAS", note="Fig. 28 R1")
two("C19", "CP", "10uF 16V", "MIC_BIAS", "GND", fp=FP + "CP_Elec_4x5.4", note="Fig. 28 C13")
two("R3", "R", "7.5k", "MIC_BIAS", "MIC_JACK", note="Fig. 28 R2")
two("C20", "C", "0.1uF", "MIC_JACK", "MIC_IN", note="Fig. 28 C6")
two("C21", "CP", "10uF 16V", "AOUT_L", "LO_L", fp=FP + "CP_Elec_4x5.4", note="Fig. 31 C37")
two("C22", "CP", "10uF 16V", "AOUT_R", "LO_R", fp=FP + "CP_Elec_4x5.4", note="Fig. 31 C36")

part("J1", "Jack_TRS", "SJ1-3523N", mpn="CUI/Same Sky SJ1-3523N", note="LINE OUT")
c("LO_L", "J1.T"), c("LO_R", "J1.R"), c("GND", "J1.S")
part("J2", "Jack_TRS", "SJ1-3523N", mpn="CUI/Same Sky SJ1-3523N", note="LINE IN")
c("LI_L", "J2.T"), c("LI_R", "J2.R"), c("GND", "J2.S")
part("J3", "Jack_TRS", "SJ1-3523N", mpn="CUI/Same Sky SJ1-3523N", note="MIC (ring grounded as in Fig. 28 J2)")
c("MIC_JACK", "J3.T"), c("GND", "J3.R"), c("GND", "J3.S")

# ------------------------------------------------------------------ game port / MIDI (Fig. 28 J3)
AXIS = [("TA", "J_TA"), ("TB", "J_TB"), ("TC", "J_TC"), ("TD", "J_TD")]
for i, (chip, ext) in enumerate(AXIS):
    two("R%d" % (6 + i), "R", "2.2k", ext, chip, note="Fig. 28 R8-R11")
    two("R%d" % (10 + i), "R", "1M", chip, "GND", note="Fig. 28 R34-R37")
    two("C%d" % (25 + i), "C", "0.01uF", chip, "GND", note="Fig. 28 C23-C26")
for i, sw in enumerate(("SWA", "SWB", "SWC", "SWD")):
    two("R%d" % (14 + i), "R", "2.2k", "+5V", sw, note="Fig. 28 R3-R6")
    two("C%d" % (29 + i), "C", "0.01uF", sw, "GND", note="Fig. 28 C18-C21")
two("R18", "R", "2.2k", "MSO", "MIDI_OUT", note="Fig. 28 R12")
two("R19", "R", "2.2k", "MIDI_IN", "MSI", note="Fig. 28 R13")
two("FB2", "FerriteBead", "600R@100MHz", "+5V", "+5VJ", note="Fig. 28 L1")
two("C33", "C", "150pF", "+5VJ", "GND", note="Fig. 28 C22")

# 2x8 header = standard motherboard game/MIDI header (AN-1130 p. 1): header pin n -> DB15 pin via the
# usual ribbon cable 1-1, 2-9, 3-2, 4-10, 5-3, 6-11, 7-4, 8-12, 9-5, 10-13, 11-6, 12-14, 13-7, 14-15, 15-8.
GAME_HEADER = {1: "+5VJ", 2: "+5VJ", 3: "SWA", 4: "SWC", 5: "J_TA", 6: "J_TC", 7: "GND", 8: "MIDI_OUT",
               9: "GND", 10: "J_TD", 11: "J_TB", 12: "SWD", 13: "SWB", 14: "MIDI_IN", 15: "+5VJ"}
HEADER_TO_DB15 = {1: 1, 2: 9, 3: 2, 4: 10, 5: 3, 6: 11, 7: 4, 8: 12, 9: 5, 10: 13, 11: 6, 12: 14, 13: 7,
                  14: 15, 15: 8}
part("J4", "Conn_02x08_Odd_Even", "GAME/MIDI 2x8", mpn="2x8 IDC box header, right angle, 2.54 mm",
     note="standard 16-pin game port bracket cable")
for pin, net in GAME_HEADER.items():
    c(net, "J4.%d" % pin)
NC.append(("J4", "16"))

for i in range(4):
    part("H%d" % (i + 1), "MountingHole_PC104", "MountingHole_3.18mm")

POWER_NETS = ("+5V", "GND", "+5VA", "+5VJ")
FLAGGED_NETS = ("+5V", "GND", "+5VA")  # nets with power_in pins and no power_out source

# DB15 game connector as drawn in ESS Fig. 28 (for the documentation/check only)
DB15_ESS = {1: "+5VJ", 2: "SWA", 3: "J_TA", 4: "GND", 5: "GND", 6: "J_TB", 7: "SWB", 8: "+5VJ", 9: "+5VJ",
            10: "SWC", 11: "J_TC", 12: "MIDI_OUT", 13: "J_TD", 14: "SWD", 15: "MIDI_IN"}
for hp, db in HEADER_TO_DB15.items():
    assert GAME_HEADER[hp] == DB15_ESS[db], (hp, db)
