#!/usr/bin/env python3
"""
Rebuild all LaTeX documentation: run pdflatex on each .tex file,
with ctcc_full_documentation.tex last (run twice for TOC and cross-refs).
Run from the documentation folder or project root.
"""
import os
import subprocess
import sys

DOC_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_TEX = "ctcc_full_documentation.tex"


def main():
    os.chdir(DOC_DIR)
    tex_files = [f for f in os.listdir(".") if f.endswith(".tex")]
    # Build main document last; others in alphabetical order
    others = sorted(f for f in tex_files if f != MAIN_TEX)
    order = others + [MAIN_TEX]

    for i, name in enumerate(order):
        is_main = name == MAIN_TEX
        runs = 3 if is_main else 1  # 3 runs for TOC, cross-refs, and hyperref bookmarks
        for run in range(runs):
            suffix = f" (run {run + 1}/{runs})" if is_main and runs > 1 else ""
            print(f"Building {name}{suffix} ...")
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", name],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                print(result.stdout, file=sys.stderr)
                print(result.stderr, file=sys.stderr)
                sys.exit(1)
    print("Done. Full PDF: ctcc_full_documentation.pdf")


if __name__ == "__main__":
    main()
