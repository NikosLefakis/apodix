"""Build docs/demo.svg: an animated replay of the real `apodix verify demo/cart` output.

Run from the project root:  python tools/make_demo_svg.py
The text is captured from the tool itself, so the picture cannot drift from the behavior.
"""

import os
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "demo.svg"

CMD = ["apodix", "verify", "demo/cart"]
LOOP = 18.0          # seconds for one full replay
LINE_H = 22
LEFT = 24
TOP = 62
WIDTH = 920

COLORS = {"ok": "#46D6A0", "bad": "#FF6B88", "warn": "#F2B84B", "dim": "#8F9CC4", "plain": "#D5DCF2", "bold": "#FFFFFF"}


def capture() -> list[str]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    done = subprocess.run(
        [sys.executable, "-m", "apodix", "verify", "demo/cart", "--no-color", "--quiet"],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
    )
    if done.returncode not in (0, 1):
        raise SystemExit(done.stderr)
    return done.stdout.rstrip("\n").splitlines()


def kind(line: str) -> str:
    if line.startswith("✓"):
        return "ok"
    if line.startswith("✗"):
        return "bad"
    if line.startswith("!"):
        return "warn"
    if line.startswith("    "):
        return "dim"
    if line and line[0].isdigit():
        return "bold"
    if line.startswith(("Read ", "Ran ")):
        return "dim"
    return "plain"


def main() -> None:
    lines = [f"$ {' '.join(CMD)}", ""] + capture()
    start = 0.6                      # seconds before the first line appears
    reveal = 9.0                     # seconds over which the output appears
    step = reveal / max(1, len(lines) - 1)

    styles, texts = [], []
    for i, line in enumerate(lines):
        if not line:
            continue
        t = start + i * step + (0.5 if i >= 2 else 0)  # a beat after the command
        a = t / LOOP * 100
        b = a + 0.8
        styles.append(
            f"@keyframes k{i}{{0%,{a:.2f}%{{opacity:0}}{b:.2f}%,93%{{opacity:1}}97%,100%{{opacity:0}}}}"
            f".l{i}{{animation:k{i} {LOOP}s infinite}}"
        )
        cls = "cmd" if i == 0 else kind(line)
        y = TOP + i * LINE_H
        body = escape(line)
        if i == 0:
            body = f'<tspan fill="#7F93FF">$</tspan> {escape(" ".join(CMD))}'
        texts.append(f'<text class="l{i} {cls}" x="{LEFT}" y="{y}" xml:space="preserve">{body}</text>')

    height = TOP + len(lines) * LINE_H + 22
    css = (
        "text{font-family:'JetBrains Mono',ui-monospace,SFMono-Regular,Consolas,Menlo,monospace;font-size:13.5px;opacity:0}"
        + "".join(f".{k}{{fill:{v}}}" for k, v in COLORS.items())
        + ".cmd{fill:#FFFFFF;font-weight:600}"
        + "".join(styles)
        + "@media (prefers-reduced-motion:reduce){text{animation:none!important;opacity:1!important}}"
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" height="{height}" '
        f'role="img" aria-label="Terminal replay: apodix verify demo/cart reports 1 of 3 criteria proven, so the work is not done yet.">'
        f"<style>{css}</style>"
        f'<rect width="{WIDTH}" height="{height}" rx="12" fill="#101A33"/>'
        f'<rect width="{WIDTH}" height="38" rx="12" fill="#1A2750"/><rect y="20" width="{WIDTH}" height="18" fill="#1A2750"/>'
        '<circle cx="24" cy="19" r="5.5" fill="#4A5A8C"/><circle cx="43" cy="19" r="5.5" fill="#4A5A8C"/><circle cx="62" cy="19" r="5.5" fill="#4A5A8C"/>'
        + "".join(texts)
        + "</svg>\n"
    )
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(lines)} lines, {len(svg)} bytes)")


if __name__ == "__main__":
    main()
