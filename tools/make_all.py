#!/usr/bin/env python3
"""Rebuild the retro104 boards: library, schematics, ERC, boards, DRC, renders, Gerber/drill, checks.

Usage: python tools/make_all.py [--force] [--route-audio]
  --force         also overwrite the .kicad_pro files (rules) from the generators.
  --route-audio   re-place and re-route pc104-audio (FreeRouting). Without it the committed audio
                  board is kept and only checked/exported: FreeRouting results may differ per run.

pc104-blank is fully generated, so rebuilding it is safe. Hand edits made in KiCad are lost on
regeneration: compare with git first (AGENTS.md). KiCad CLI runs strictly one after another.
FreeRouting 2.5.0 is not part of the repository: FREEROUTING_JAR (default ../tools/freerouting-2.5.0.jar).
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
JAR = os.environ.get("FREEROUTING_JAR", os.path.join(os.path.dirname(REPO), "tools", "freerouting-2.5.0.jar"))
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts"


def run(*args, cwd=REPO):
    print(">", " ".join(str(a) for a in args))
    r = subprocess.run([str(a) for a in args], cwd=cwd)
    if r.returncode != 0:
        raise SystemExit("failed (%d): %s" % (r.returncode, args[0]))


def render(out, pcb, *opts):
    run(CLI, "pcb", "render", "--quality", "high", "--background", "opaque", *opts, "-o", out, pcb)


def fabrication(name, pcb, fab):
    gerbers = os.path.join(fab, "gerbers")
    shutil.rmtree(os.path.join(REPO, gerbers), ignore_errors=True)
    os.makedirs(os.path.join(REPO, gerbers))
    run(CLI, "pcb", "export", "gerbers", "--layers", LAYERS, "--use-drill-file-origin", "--subtract-soldermask",
        "-o", gerbers, pcb)
    run(CLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "--excellon-units", "mm",
        "--drill-origin", "plot", "--generate-map", "--map-format", "pdf", "-o", gerbers + os.sep, pcb)
    gdir = os.path.join(REPO, gerbers)
    names = sorted(n for n in os.listdir(gdir) if not n.endswith(".pdf") and not n.endswith(".gbrjob"))
    with zipfile.ZipFile(os.path.join(REPO, fab, "%s-revA-jlcpcb.zip" % name), "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.write(os.path.join(gdir, n), n)
    sums = []
    for root in (gdir, os.path.join(REPO, fab)):
        for n in sorted(os.listdir(root)):
            p = os.path.join(root, n)
            if os.path.isfile(p) and n != "SHA256SUMS":
                rel = os.path.relpath(p, os.path.join(REPO, fab)).replace(os.sep, "/")
                sums.append("%s  %s" % (hashlib.sha256(open(p, "rb").read()).hexdigest(), rel))
    with open(os.path.join(REPO, fab, "SHA256SUMS"), "w", newline="\n") as f:
        f.write("\n".join(sums) + "\n")


def blank(force):
    prj = os.path.join("hardware", "pc104-blank")
    sch, pcb = os.path.join(prj, "pc104-blank.kicad_sch"), os.path.join(prj, "pc104-blank.kicad_pcb")
    mating = os.path.join(prj, "pc104-blank-mating.kicad_pcb")
    reports, net = os.path.join(prj, "reports"), os.path.join("build", "pc104-blank.net")
    os.makedirs(os.path.join(REPO, reports), exist_ok=True)
    run(sys.executable, "-P", "tools/generate.py", *(["--force"] if force else []))
    run(CLI, "sch", "erc", "--format", "report", "--severity-all", "-o", os.path.join(reports, "erc.rpt"), sch)
    run(CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch)
    run(CLI, "sch", "export", "pdf", "-o", os.path.join("docs", "pc104-blank-schematic.pdf"), sch)
    run(KPY, "tools/build_board.py", net)
    run(CLI, "pcb", "drc", "--schematic-parity", "--severity-all", "--format", "report",
        "-o", os.path.join(reports, "drc.rpt"), pcb)
    render("images/pc104-blank-top.png", pcb, "--side", "top", "-w", "1600", "-h", "1500")
    render("images/pc104-blank-bottom.png", pcb, "--side", "bottom", "-w", "1600", "-h", "1500")
    render("images/pc104-blank-angle.png", pcb, "--perspective", "--rotate", " -55,0,-30", "--zoom", "0.9",
           "-w", "1600", "-h", "1200")
    render("images/pc104-blank-mating-side.png", mating, "--perspective", "--rotate", " -85,0,-90",
           "--zoom", "0.8", "-w", "1600", "-h", "1000")
    render("images/pc104-blank-mating-angle.png", mating, "--perspective", "--rotate", " -105,0,-35",
           "--zoom", "0.8", "-w", "1600", "-h", "1200")
    fabrication("pc104-blank", pcb, os.path.join(prj, "fabrication"))
    run(sys.executable, "-P", "tools/check_board.py")
    for leftover in (mating, mating.replace(".kicad_pcb", ".kicad_pro")):
        p = os.path.join(REPO, leftover)
        if os.path.exists(p):
            os.remove(p)


def audio(force, route):
    prj = os.path.join("hardware", "pc104-audio")
    sch, pcb = os.path.join(prj, "pc104-audio.kicad_sch"), os.path.join(prj, "pc104-audio.kicad_pcb")
    reports, build = os.path.join(prj, "reports"), os.path.join("build", "audio")
    net = os.path.join(build, "pc104-audio.net")
    os.makedirs(os.path.join(REPO, reports), exist_ok=True)
    os.makedirs(os.path.join(REPO, build), exist_ok=True)
    run(sys.executable, "-P", "tools/gen_audio.py", *(["--force"] if force else []))
    run(CLI, "sch", "erc", "--format", "report", "--severity-all", "-o", os.path.join(reports, "erc.rpt"), sch)
    run(CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch)
    run(sys.executable, "-P", "tools/check_audio_netlist.py", net)
    run(CLI, "sch", "export", "pdf", "-o", os.path.join("docs", "pc104-audio-schematic.pdf"), sch)
    if route or not os.path.exists(os.path.join(REPO, pcb)):
        run(KPY, "tools/build_audio_board.py", net)
        ses = os.path.join(REPO, build, "placed.ses")
        if os.path.exists(ses):
            os.remove(ses)
        run("java", "-jar", JAR, "-de", "placed.dsn", "-do", "placed.ses", "-mp", "100", "--gui.enabled=false",
            "--router.optimizer.enabled=false", cwd=os.path.join(REPO, build))
        run(KPY, "tools/route_audio_board.py", net)
    run(CLI, "pcb", "drc", "--schematic-parity", "--severity-all", "--format", "report",
        "-o", os.path.join(reports, "drc.rpt"), pcb)
    render("images/pc104-audio-top.png", pcb, "--side", "top", "-w", "1600", "-h", "1500")
    render("images/pc104-audio-bottom.png", pcb, "--side", "bottom", "-w", "1600", "-h", "1500")
    render("images/pc104-audio-angle.png", pcb, "--perspective", "--rotate", " -55,0,-30", "--zoom", "0.9",
           "-w", "1600", "-h", "1200")
    run(CLI, "pcb", "export", "pdf", "--layers", "F.Fab,F.Silkscreen,Edge.Cuts", "--include-border-title",
        "-o", os.path.join("docs", "pc104-audio-assembly.pdf"), pcb)
    fabrication("pc104-audio", pcb, os.path.join(prj, "fabrication"))
    run(sys.executable, "-P", "tools/check_audio_board.py")


def main():
    force = "--force" in sys.argv
    os.makedirs(os.path.join(REPO, "build"), exist_ok=True)
    blank(force)
    audio(force, "--route-audio" in sys.argv)
    print("done")


if __name__ == "__main__":
    main()
