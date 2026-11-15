"""Copy standard KiCad 9 footprints and their STEP models into the project library.

The copies make the repository self-contained (as in retro535/isa-flash-disk). Model paths are
rewritten to ${KIPRJMOD}/../lib/3d/. Footprints that disagree with the part's own data sheet are
corrected here, with the reason recorded in the footprint description.
"""

import os
import re
import shutil

KICAD = os.environ.get("KICAD9_SHARE", r"C:/Program Files/KiCad/9.0/share/kicad")
FP_DIR = os.path.join(KICAD, "footprints")
MODEL_DIR = os.path.join(KICAD, "3dmodels")

# (library, footprint, new name or None)
STOCK = [
    ("Package_QFP", "PQFP-100_14x20mm_P0.65mm", None),
    ("Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm", None),
    ("Package_DIP", "DIP-8_W7.62mm_Socket_LongPads", None),
    ("Crystal", "Crystal_HC49-4H_Vertical", None),
    ("Capacitor_SMD", "CP_Elec_4x5.4", None),
    ("Capacitor_SMD", "CP_Elec_6.3x5.4", None),
    ("Capacitor_SMD", "C_0805_2012Metric_Pad1.18x1.45mm_HandSolder", None),
    ("Resistor_SMD", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder", None),
    ("Inductor_SMD", "L_0805_2012Metric_Pad1.15x1.40mm_HandSolder", None),
    ("Connector_IDC", "IDC-Header_2x08_P2.54mm_Horizontal", None),
    ("Jumper", "SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm", None),
    ("Connector_Audio", "Jack_3.5mm_CUI_SJ1-3523N_Horizontal", "Jack_3.5mm_CUI_SJ1-3523N_Horizontal_Slots"),
]

JACK_NOTE = (" | retro104: terminal slots changed from 0.4x1.4 mm to 0.8x1.5 mm (pads 1.6x2.3 mm) per the "
             "Same Sky SJ1-352XN data sheet 09/12/2024, p. 2 'Recommended PCB Layout' (5-1.5x0.8); "
             "0.4 mm is also below the JLCPCB plated-slot width. Edge.Cuts notch of the stock footprint removed: "
             "the body front (data sheet 'Connector Edge') is placed on the board edge, so the 6 mm bushing is "
             "entirely outside the board and needs no cut-out.")


def fix_jack(text):
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sexpr import parse, dump, first
    # pads R, S, T: drill oval 0.4 1.4 / 1.4 0.4 -> 0.8 1.5 / 1.5 0.8, pad 1.2x2.2 -> 1.6x2.3
    text = text.replace("(drill oval 0.4 1.4)", "(drill oval 0.8 1.5)").replace("(drill oval 1.4 0.4)", "(drill oval 1.5 0.8)")
    text = re.sub(r"\(size 1\.2 2\.2\)", "(size 1.6 2.3)", text)
    text = re.sub(r"\(size 2\.2 1\.2\)", "(size 2.3 1.6)", text)
    text = re.sub(r'\(descr "([^"]*)"\)', lambda m: '(descr "%s%s")' % (m.group(1), JACK_NOTE), text, count=1)
    tree = parse(text)
    tree[:] = [x for x in tree if not (isinstance(x, list) and x and x[0] in ("fp_line", "fp_arc")
                                       and first(x, "layer") and first(x, "layer")[1] == "Edge.Cuts")]

    def beyond_front(x):
        # silkscreen of the bushing / body front: everything at or past the connector edge (local y >= 3.2)
        if not (isinstance(x, list) and x and x[0] == "fp_line" and first(x, "layer")[1] == "F.SilkS"):
            return False
        return float(first(x, "start")[2]) >= 3.2 or float(first(x, "end")[2]) >= 3.2
    tree[:] = [x for x in tree if not beyond_front(x)]
    return dump(tree)


def copy_stock(lib_dir, model_out):
    os.makedirs(lib_dir, exist_ok=True)
    os.makedirs(model_out, exist_ok=True)
    written = []
    for lib, name, new in STOCK:
        src = os.path.join(FP_DIR, lib + ".pretty", name + ".kicad_mod")
        text = open(src, encoding="utf-8").read()
        out_name = new or name
        if new:
            text = text.replace('(footprint "%s"' % name, '(footprint "%s"' % new, 1)
        if name.startswith("Jack_3.5mm_CUI_SJ1-3523N"):
            text = fix_jack(text)

        def repl(m):
            path = m.group(1)
            rel = path.replace("${KICAD9_3DMODEL_DIR}/", "")
            src_model = os.path.join(MODEL_DIR, rel)
            if not os.path.exists(src_model):
                raise SystemExit("missing 3D model " + src_model)
            fname = os.path.basename(rel)
            shutil.copyfile(src_model, os.path.join(model_out, fname))
            return '(model "${KIPRJMOD}/../lib/3d/%s"' % fname

        text = re.sub(r'\(model "([^"]+)"', repl, text)
        with open(os.path.join(lib_dir, out_name + ".kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        written.append(out_name)
    return written
