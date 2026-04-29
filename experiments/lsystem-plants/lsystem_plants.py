#!/usr/bin/env python3
"""
L-System Plant Generator
Generates organic plant-like structures using Lindenmayer systems.
Each axiom + rule produces a unique branching pattern — some look like
ferns, some like trees, some like coral. Export to SVG for viewing.
"""

import argparse
import math
import random
import sys
from dataclasses import dataclass, field
from typing import Callable

try:
    import cairo as c
    CAIRO_AVAILABLE = True
except ImportError:
    CAIRO_AVAILABLE = False


@dataclass
class LSystem:
    axiom: str
    rules: dict[str, str]
    angle: float = 25.0
    scale: float = 1.0
    iterations: int = 5
    step_length: float = 5.0
    width: int = 1200
    height: int = 900
    bg_color: tuple[float, float, float] = (0.05, 0.07, 0.1)
    stroke_color: tuple[float, float, float] = (0.2, 0.55, 0.3)
    stroke_width: float = 1.5
    decay: float = 0.7
    title: str = "L-System Plant"


@dataclass
class PlantPreset:
    name: str
    ls: LSystem
    description: str


PRESETS: list[PlantPreset] = []


def preset(
    name: str,
    axiom: str,
    rules: dict[str, str],
    angle: float = 25.0,
    iterations: int = 5,
    decay: float = 0.7,
    title: str = "",
):
    ls = LSystem(
        axiom=axiom,
        rules=rules,
        angle=angle,
        iterations=iterations,
        decay=decay,
        title=title or name,
    )
    p = PlantPreset(name=name, ls=ls, description=name)
    globals()[name] = p
    PRESETS.append(p)


# ── Presets ────────────────────────────────────────────────────────────────

preset(
    "Fern",
    axiom="X",
    rules={"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"},
    angle=25.0,
    iterations=6,
    decay=0.5,
    title="Fern (Barnsley-style)",
)

preset(
    "Bush",
    axiom="F",
    rules={"F": "FF-[-F+F+F]+[+F-F-F]"},
    angle=22.0,
    iterations=5,
    decay=0.6,
    title="Organic Bush",
)

preset(
    "DragonTree",
    axiom="F",
    rules={"F": "F[+F]F[-F][F]"},
    angle=20.0,
    iterations=6,
    decay=0.65,
    title="Dragon Tree",
)

preset(
    "Seaweed",
    axiom="X",
    rules={"X": "F[-X][X]F[-X]+X", "F": "FF"},
    angle=30.0,
    iterations=6,
    decay=0.55,
    title="Seaweed",
)

preset(
    "Weed",
    axiom="X",
    rules={"X": "F[+X][-X]FX", "F": "FF"},
    angle=37.0,
    iterations=7,
    decay=0.5,
    title="Wild Weed",
)

preset(
    "Coral",
    axiom="F",
    rules={"F": "F[+F][-F-F][++F][--F]"},
    angle=15.0,
    iterations=5,
    decay=0.6,
    title="Coral",
)

preset(
    "Pine",
    axiom="Y",
    rules={"X": "X[-FFF][+FFF]FX", "Y": "YFX[+Y][-Y]"},
    angle=25.0,
    iterations=5,
    decay=0.7,
    title="Pine-Like Tree",
)

preset(
    "StochasticFern",
    axiom="X",
    rules={
        "X": "F[+X]F[-X]+X",
        "F": "FF",
    },
    angle=25.0,
    iterations=6,
    decay=0.5,
    title="Stochastic Fern",
)


# ── Core ──────────────────────────────────────────────────────────────────────

def expand(s: str, rules: dict[str, str], iterations: int) -> str:
    for _ in range(iterations):
        buf = []
        for ch in s:
            buf.append(rules.get(ch, ch))
        s = "".join(buf)
    return s


def generate_stochastic(s: str, rules: dict[str, str], rng: random.Random) -> str:
    """Apply stochastic rules: pick randomly among alternatives separated by |"""
    buf = []
    for ch in s:
        rule = rules.get(ch)
        if rule and "|" in rule:
            options = rule.split("|")
            buf.append(rng.choice(options))
        else:
            buf.append(rule if rule else ch)
    return "".join(buf)


def stochastic_expand(
    axiom: str, rules: dict[str, str], iterations: int, seed: int
) -> str:
    rng = random.Random(seed)
    s = axiom
    for _ in range(iterations):
        s = generate_stochastic(s, rules, rng)
    return s


def interpret(
    s: str,
    angle: float,
    step_length: float,
    decay: float,
    renderer: Callable[..., None],
):
    a = math.radians(angle)
    x, y = 0.0, 0.0
    heading = math.pi / 2  # start pointing up
    stack: list[tuple[float, float, float, float]] = []
    current_width = 1.0

    for ch in s:
        if ch == "F":
            x2 = x + step_length * math.cos(heading)
            y2 = y + step_length * math.sin(heading)
            renderer(x, y, x2, y2, current_width)
            x, y = x2, y2
            step_length *= decay
            current_width *= 0.95
        elif ch == "f":
            x = x + step_length * math.cos(heading)
            y = y + step_length * math.sin(heading)
            step_length *= decay
        elif ch == "+":
            heading += a
        elif ch == "-":
            heading -= a
        elif ch == "[":
            stack.append((x, y, heading, step_length))
        elif ch == "]":
            x, y, heading, step_length = stack.pop()
        elif ch == "X" or ch == "Y":
            pass  # no drawing action


def color_for_depth(depth: int, max_depth: int) -> tuple[float, float, float]:
    """Gradient from deep green at base to lighter tips"""
    t = depth / max(max_depth, 1)
    return (0.15 + t * 0.4, 0.45 + t * 0.35, 0.2 + t * 0.3)


def draw_cairo(ls: LSystem, path: str, seed: int = None):
    import cairo

    surface = cairo.SVGSurface(path, ls.width, ls.height)
    ctx = cairo.Context(surface)

    # background
    ctx.set_source_rgb(*ls.bg_color)
    ctx.paint()

    depth_counter = [0]
    max_depth = [0]

    def render(x1, y1, x2, y2, width):
        depth_counter[0] += 1
        max_depth[0] = max(max_depth[0], depth_counter[0])

    # first pass: just count depth
    if seed is not None:
        expanded = stochastic_expand(ls.axiom, ls.rules, ls.iterations, seed)
    else:
        expanded = expand(ls.axiom, ls.rules, ls.iterations)

    interpret(expanded, ls.angle, ls.step_length, ls.decay, render)

    # center the drawing
    def renderer(x1, y1, x2, y2, width):
        ctx.set_source_rgb(*ls.stroke_color)
        ctx.set_line_width(max(0.3, width * ls.stroke_width))
        ctx.move_to(x1 + ls.width // 2, y1 + ls.height - 40)
        ctx.line_to(x2 + ls.width // 2, y2 + ls.height - 40)
        ctx.stroke()
        depth_counter[0] -= 1

    ctx.set_line_cap = cairo.LINE_CAP_ROUND
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    interpret(expanded, ls.angle, ls.step_length, ls.decay, renderer)

    surface.finish()
    print(f"Saved: {path}")


def draw_ascii(ls: LSystem, seed: int = None):
    lines = [[" "] * 120 for _ in range(50)]
    x, y = 60, 48
    heading = 0
    stack: list[tuple[int, int, int]] = []
    step = 1

    if seed is not None:
        expanded = stochastic_expand(ls.axiom, ls.rules, ls.iterations, seed)
    else:
        expanded = expand(ls.axiom, ls.rules, ls.iterations)

    a = math.radians(ls.angle)

    for ch in expanded:
        if ch == "F":
            dx = int(round(step * math.cos(heading)))
            dy = int(round(step * math.sin(heading)))
            nx, ny = x + dx, y - dy
            if 0 <= nx < 120 and 0 <= ny < 50:
                lines[ny][nx] = "*"
            x, y = nx, ny
        elif ch == "+":
            heading += a
        elif ch == "-":
            heading -= a
        elif ch == "[":
            stack.append((x, y, heading))
        elif ch == "]":
            x, y, heading = stack.pop()

    print(f"\n# {ls.title}")
    print("-" * 60)
    for row in lines:
        print("".join(row))


def draw_html(ls: LSystem, path: str, seed: int = None):
    """Generate an HTML canvas animation of the plant growing"""
    if seed is not None:
        expanded = stochastic_expand(ls.axiom, ls.rules, ls.iterations, seed)
    else:
        expanded = expand(ls.axiom, ls.rules, ls.iterations)

    # Build SVG path
    x, y = 0.0, 0.0
    heading = math.pi / 2
    stack: list[tuple[float, float, float]] = []
    step = ls.step_length
    cx, cy = ls.width // 2, ls.height - 40

    a = math.radians(ls.angle)
    paths: list[str] = []
    colors: list[str] = []
    widths: list[float] = []
    depth = 0
    max_depth = [0]
    depth_stack: list[int] = []

    def get_color(d, mx):
        t = d / max(mx, 1)
        r = int(40 + t * 200)
        g = int(80 + t * 140)
        b = int(30 + t * 100)
        return f"#{r:02x}{g:02x}{b:02x}"

    first = True
    current_path = ""
    current_width = ls.stroke_width
    current_color = get_color(0, 1)
    depth_counts: list[int] = []

    for ch in expanded:
        if ch == "F":
            x2 = x + step * math.cos(heading)
            y2 = y + step * math.sin(heading)
            if not first:
                current_path += f" L {cx+x2:.1f},{cy-y2:.1f}"
            else:
                current_path = f"M {cx+x:.1f},{cy-y:.1f} L {cx+x2:.1f},{cy-y2:.1f}"
                first = False
            x, y = x2, y2
            step *= ls.decay
            current_width *= 0.97
        elif ch == "+":
            heading += a
        elif ch == "-":
            heading -= a
        elif ch == "[":
            stack.append((x, y, heading))
            depth_stack.append(depth)
            depth += 1
            max_depth[0] = max(max_depth[0], depth)
            current_color = get_color(depth, max_depth[0])
            paths.append(current_path)
            colors.append(current_color)
            widths.append(current_width)
            current_path = ""
            first = True
        elif ch == "]":
            x, y, heading = stack.pop()
            depth = depth_stack.pop()
            current_color = get_color(depth, max_depth[0])

    if current_path:
        paths.append(current_path)
        colors.append(current_color)
        widths.append(current_width)

    svg_paths = "\n".join(
        f'<path d="{p}" stroke="{c}" stroke-width="{w:.1f}" fill="none" stroke-linecap="round"/>'
        for p, c, w in zip(paths, colors, widths)
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<title>{ls.title}</title>
<style>
  body {{ margin:0; background:#0a0e10; display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100vh; }}
  h2 {{ color:#8fcf8f; font-family:Georgia,serif; font-weight:400; letter-spacing:0.05em; margin-bottom:0.3em; }}
  svg {{ max-width:900px; width:95vw; height:auto; }}
</style>
</head>
<body>
<h2>{ls.title}</h2>
<svg viewBox="0 0 {ls.width} {ls.height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{ls.width}" height="{ls.height}" fill="#0a0e10"/>
{svg_paths}
</svg>
</body>
</html>"""

    with open(path, "w") as f:
        f.write(html)
    print(f"Saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="L-System Plant Generator")
    parser.add_argument("--preset", "-p", choices=[p.name for p in PRESETS],
                        default="Fern", help="Plant preset to generate")
    parser.add_argument("--iterations", "-i", type=int, default=None,
                        help="Override iteration count")
    parser.add_argument("--seed", "-s", type=int, default=None,
                        help="Random seed (for stochastic presets)")
    parser.add_argument("--angle", "-a", type=float, default=None,
                        help="Override branch angle in degrees")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file (SVG or HTML based on extension)")
    parser.add_argument("--ascii", action="store_true",
                        help="ASCII art output")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List all presets")
    args = parser.parse_args()

    if args.list:
        print("Available presets:")
        for p in PRESETS:
            print(f"  {p.name}")
        return

    ps = next(p for p in PRESETS if p.name == args.preset)
    ls = ps.ls

    if args.iterations is not None:
        ls.iterations = args.iterations
    if args.angle is not None:
        ls.angle = args.angle

    if args.output:
        ext = args.output.rsplit(".", 1)[-1].lower()
        if ext == "html":
            draw_html(ls, args.output, seed=args.seed)
        elif ext == "svg":
            if not CAIRO_AVAILABLE:
                print("cairo not available, falling back to HTML/SVG")
                draw_html(ls, args.output.replace(".svg", ".html"), seed=args.seed)
            else:
                draw_cairo(ls, args.output, seed=args.seed)
        else:
            print(f"Unknown extension: {ext}")
            sys.exit(1)
    else:
        if CAIRO_AVAILABLE:
            out = f"/tmp/{ps.name.lower()}.html"
            draw_html(ls, out, seed=args.seed)
        else:
            draw_ascii(ls, seed=args.seed)


if __name__ == "__main__":
    main()
