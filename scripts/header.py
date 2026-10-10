# /// script
# requires-python = ">=3.11"
# dependencies = ["fonttools"]
# ///
"""Render the profile header, a man page heading, as light and dark SVGs.

GitHub serves README images without web fonts, so the text is drawn as glyph
outlines from Maple Mono, the terminal font. Run from the repo root:

    uv run scripts/header.py [--fonts DIR]
"""

import argparse
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path.home() / "Library/Fonts"
WEIGHTS = {"regular": "MapleMono-NF-CN-Regular.ttf", "bold": "MapleMono-NF-CN-SemiBold.ttf"}

THEMES = {
    "light": {"ink": "#1f2328", "muted": "#656d76", "accent": "#b5402b"},
    "dark": {"ink": "#e6edf3", "muted": "#8b949e", "accent": "#e36a4f"},
}

WIDTH, HEIGHT = 660, 196
SIZE, INDENT = 18, " " * 7

# Each line is a baseline and runs of (text, weight, color, underlined), like `man` output.
LINES = [
    (72, [("NAME", "bold", "ink", False)]),
    (102, [(INDENT, "regular", "ink", False), ("suny", "bold", "accent", False),
           (" — backend engineer in Chengdu, China", "regular", "ink", False)]),
    (146, [("SYNOPSIS", "bold", "ink", False)]),
    (176, [(INDENT, "regular", "ink", False), ("suny", "bold", "accent", False),
           (" [-l ", "regular", "ink", False), ("rust", "regular", "ink", True),
           (" | ", "regular", "ink", False), ("swift", "regular", "ink", True),
           (" | ", "regular", "ink", False), ("python", "regular", "ink", True),
           ("] [-t ", "regular", "ink", False), ("macos", "regular", "ink", True),
           (" | ", "regular", "ink", False), ("ios", "regular", "ink", True),
           ("]", "regular", "ink", False)]),
]
TITLE, SECTION = "SUNY(1)", "General Commands Manual"


class Pen:
    """Draws strings as SVG path data from one font at a fixed pixel size."""

    def __init__(self, path: Path, size: float):
        self.font = TTFont(path)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.scale = size / self.font["head"].unitsPerEm

    def advance(self, text: str) -> float:
        return sum(self.glyphs[self.cmap[ord(char)]].width for char in text) * self.scale

    def draw(self, text: str, x: float, baseline: float) -> str:
        commands = []
        for char in text:
            name = self.cmap[ord(char)]
            pen = SVGPathPen(self.glyphs, ntos=lambda value: f"{value:.2f}".rstrip("0").rstrip("."))
            self.glyphs[name].draw(TransformPen(pen, (self.scale, 0, 0, -self.scale, x, baseline)))
            commands.append(pen.getCommands())
            x += self.glyphs[name].width * self.scale
        return "".join(commands)


def render(colors: dict, pens: dict, small: Pen) -> str:
    paths = {role: [] for role in colors}
    underlines = []

    # The running head: title at both margins, section name centred.
    paths["muted"].append(small.draw(TITLE, 0, 24))
    paths["muted"].append(small.draw(SECTION, (WIDTH - small.advance(SECTION)) / 2, 24))
    paths["muted"].append(small.draw(TITLE, WIDTH - small.advance(TITLE), 24))

    for baseline, runs in LINES:
        x = 0
        for text, weight, role, underlined in runs:
            pen = pens[weight]
            paths[role].append(pen.draw(text, x, baseline))
            width = pen.advance(text)
            if underlined:
                underlines.append(f'<rect x="{x:.2f}" y="{baseline + 4}" width="{width:.2f}" height="1.2"/>')
            x += width

    body = "\n".join(f'  <path fill="{colors[role]}" d="{"".join(parts)}"/>'
                     for role, parts in paths.items() if parts)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="suny — backend engineer in Chengdu, China">
{body}
  <g fill="{colors['muted']}">{''.join(underlines)}</g>
</svg>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fonts", type=Path, default=FONTS, help="directory holding the Maple Mono NF CN TTFs")
    args = parser.parse_args()

    pens = {weight: Pen(args.fonts / file, SIZE) for weight, file in WEIGHTS.items()}
    small = Pen(args.fonts / WEIGHTS["regular"], 14)

    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    for theme, colors in THEMES.items():
        (assets / f"header-{theme}.svg").write_text(render(colors, pens, small))
        print(f"wrote assets/header-{theme}.svg")


if __name__ == "__main__":
    main()
