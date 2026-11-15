#!/usr/bin/env python3
"""Rebuild pc104-blank end to end: library, schematic, ERC, board, DRC, renders, Gerber/drill, checks.

Usage: python tools/make_all.py [--force]
  --force   also overwrite hardware/pc104-blank/pc104-blank.kicad_pro (rules) from the generator.

The board is fully generated (no manual routing), so rebuilding it is safe. If the PCB or schematic
was edited by hand in KiCad, those edits are lost: compare with git first (see AGENTS.md).
KiCad CLI runs strictly one after another: several kicad-cli processes on one project may race on
settings files.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KICAD_BIN = os.environ.get("KICAD_BIN", r"C:/Program Files/KiCad/9.0/bin")
CLI = os.path.join(KICAD_BIN, "kicad-cli.exe" if os.name == "nt" else "kicad-cli")
KPY = os.path.join(KICAD_BIN, "python.exe" if os.name == "nt" else "python3")
PRJ = os.path.join("hardware", "pc104-blank")
SCH = os.path.join(PRJ, "pc104-blank.kicad_sch")
PCB = os.path.join(PRJ, "pc104-blank.kicad_pcb")
MATING = os.path.join(PRJ, "pc104-blank-mating.kicad_pcb")
REPORTS = os.path.join(PRJ, "reports")
FAB = os.path.join(PRJ, "fabrication")
GERBERS = os.path.join(FAB, "gerbers")
NET = os.path.join("build", "pc104-blank.net")
ZIP = os.path.join(FAB, "pc104-blank-revA-jlcpcb.zip")
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"


def run(*args):
    print(">", " ".join(str(a) for a in args))
    r = subprocess.run([str(a) for a in args], cwd=REPO)
    if r.returncode != 0:
        raise SystemExit("failed (%d): %s" % (r.returncode, args[0]))


def render(out, pcb, *opts):
    run(CLI, "pcb", "render", "--quality", "high", "--background", "opaque", *opts, "-o", out, pcb)


def main():
    os.makedirs(os.path.join(REPO, "build"), exist_ok=True)
    os.makedirs(os.path.join(REPO, REPORTS), exist_ok=True)
    run(sys.executable, "-P", "tools/generate.py", *(["--force"] if "--force" in sys.argv else []))
    run(CLI, "sch", "erc", "--format", "report", "--severity-all", "-o", os.path.join(REPORTS, "erc.rpt"), SCH)
    run(CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", NET, SCH)
    run(CLI, "sch", "export", "pdf", "-o", os.path.join("docs", "pc104-blank-schematic.pdf"), SCH)
    run(KPY, "tools/build_board.py", NET)
    run(CLI, "pcb", "drc", "--schematic-parity", "--severity-all", "--format", "report",
        "-o", os.path.join(REPORTS, "drc.rpt"), PCB)
    render("images/pc104-blank-top.png", PCB, "--side", "top", "-w", "1600", "-h", "1500")
    render("images/pc104-blank-bottom.png", PCB, "--side", "bottom", "-w", "1600", "-h", "1500")
    render("images/pc104-blank-angle.png", PCB, "--perspective", "--rotate", " -55,0,-30", "--zoom", "0.9",
           "-w", "1600", "-h", "1200")
    render("images/pc104-blank-mating-side.png", MATING, "--perspective", "--rotate", " -85,0,-90",
           "--zoom", "0.8", "-w", "1600", "-h", "1000")
    render("images/pc104-blank-mating-angle.png", MATING, "--perspective", "--rotate", " -105,0,-35",
           "--zoom", "0.8", "-w", "1600", "-h", "1200")
    shutil.rmtree(os.path.join(REPO, GERBERS), ignore_errors=True)
    os.makedirs(os.path.join(REPO, GERBERS))
    run(CLI, "pcb", "export", "gerbers", "--layers", LAYERS, "--use-drill-file-origin", "--subtract-soldermask",
        "-o", GERBERS, PCB)
    run(CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--excellon-units", "mm",
        "--drill-origin", "plot", "--generate-map", "--map-format", "pdf", "-o", GERBERS + os.sep, PCB)
    gdir = os.path.join(REPO, GERBERS)
    names = sorted(n for n in os.listdir(gdir) if not n.endswith(".pdf") and not n.endswith(".gbrjob"))
    with zipfile.ZipFile(os.path.join(REPO, ZIP), "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.write(os.path.join(gdir, n), n)
    sums = []
    for root in (gdir, os.path.join(REPO, FAB)):
        for n in sorted(os.listdir(root)):
            p = os.path.join(root, n)
            if os.path.isfile(p) and n != "SHA256SUMS":
                rel = os.path.relpath(p, os.path.join(REPO, FAB)).replace(os.sep, "/")
                sums.append("%s  %s" % (hashlib.sha256(open(p, "rb").read()).hexdigest(), rel))
    with open(os.path.join(REPO, FAB, "SHA256SUMS"), "w", newline="\n") as f:
        f.write("\n".join(sums) + "\n")
    run(sys.executable, "-P", "tools/check_board.py")
    for leftover in (MATING, MATING.replace(".kicad_pcb", ".kicad_pro")):
        p = os.path.join(REPO, leftover)
        if os.path.exists(p):
            os.remove(p)
    print("done")


if __name__ == "__main__":
    main()
