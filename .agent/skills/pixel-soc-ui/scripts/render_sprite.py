#!/usr/bin/env python3
"""Render crisp pixel-art sprites from ASCII matrix + palette JSON specs.

Uses Pillow (Image.Resampling.NEAREST) to produce transparent RGBA PNGs.
If Pillow is unavailable (or --format svg is passed), automatically falls back
to generating an integer-grid <rect>-only SVG with shape-rendering="crispEdges".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

RGBA = Tuple[int, int, int, int]
HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def parse_color(value: Optional[str], key: str) -> Optional[RGBA]:
    """Convert a palette value into an (R, G, B, A) tuple or None for transparent."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Palet anahtarı '{key}' için geçersiz renk tipi: {type(value).__name__}")

    cleaned = value.strip()
    if cleaned == "" or cleaned.lower() == "transparent":
        return None

    match = HEX_RE.match(cleaned)
    if not match:
        raise ValueError(
            f"Palet anahtarı '{key}' geçersiz hex rengi içeriyor: '{value}'. "
            "Beklenen format: #RGB, #RRGGBB, #RRGGBBAA veya null."
        )

    hex_str = match.group(1)
    if len(hex_str) == 3:
        r, g, b = (int(c * 2, 16) for c in hex_str)
        a = 255
    elif len(hex_str) == 6:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        a = 255
    else:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        a = int(hex_str[6:8], 16)

    return (r, g, b, a)


def load_sprite_spec(input_path: Path) -> Tuple[List[str], Dict[str, Optional[RGBA]], int, int, str]:
    """Load and validate a JSON sprite definition."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Girdi dosyası bulunamadı: {input_path}")

    with input_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError("JSON kökü bir nesne (object) olmalıdır.")

    raw_palette = data.get("palette")
    raw_grid = data.get("grid")
    sprite_name = str(data.get("name") or input_path.stem)

    if not isinstance(raw_palette, dict):
        raise ValueError("'palette' alanı bir JSON nesnesi olmalıdır.")
    if not isinstance(raw_grid, list) or len(raw_grid) == 0:
        raise ValueError("'grid' alanı boş olmayan bir satır dizisi olmalıdır.")

    palette: Dict[str, Optional[RGBA]] = {".": None, " ": None}
    for key, raw_color in raw_palette.items():
        if not isinstance(key, str) or len(key) != 1:
            raise ValueError(f"Palet anahtarı tek bir ASCII karakteri olmalıdır: '{key}'")
        palette[key] = parse_color(raw_color, key)

    height = len(raw_grid)
    first_row = raw_grid[0]
    if not isinstance(first_row, str) or len(first_row) == 0:
        raise ValueError("Grid satırları boş olmayan string olmalıdır.")
    width = len(first_row)

    for y, row in enumerate(raw_grid):
        if not isinstance(row, str):
            raise ValueError(f"Satır {y} string değil.")
        if len(row) != width:
            raise ValueError(
                f"Satır {y} uzunluğu ({len(row)}) beklenen genişlikle ({width}) uyuşmuyor."
            )
        for x, ch in enumerate(row):
            if ch not in palette:
                raise ValueError(
                    f"Tanımsız palet karakteri '{ch}' (satır {y}, sütun {x})."
                )

    return raw_grid, palette, width, height, sprite_name


def render_svg(
    grid: List[str],
    palette: Dict[str, Optional[RGBA]],
    width: int,
    height: int,
    scale: int,
    output_path: Path,
    sprite_name: str,
) -> Path:
    """Render the sprite as an integer-grid <rect>-only SVG with crispEdges."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" '
            f'width="{width * scale}" height="{height * scale}" '
            f'shape-rendering="crispEdges" role="img" '
            f'aria-label="{escape(sprite_name)}">'
        ),
    ]

    for y, row in enumerate(grid):
        x = 0
        while x < width:
            rgba = palette[row[x]]
            if rgba is None or rgba[3] == 0:
                x += 1
                continue
            run_end = x + 1
            while run_end < width and palette[row[run_end]] == rgba:
                run_end += 1

            r, g, b, a = rgba
            hex_fill = f"#{r:02x}{g:02x}{b:02x}"
            opacity_attr = f' fill-opacity="{a / 255:.4f}"' if a < 255 else ""
            lines.append(
                f'  <rect x="{x}" y="{y}" width="{run_end - x}" height="1" '
                f'fill="{hex_fill}"{opacity_attr}/>'
            )
            x = run_end

    lines.append("</svg>")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def render_png(
    grid: List[str],
    palette: Dict[str, Optional[RGBA]],
    width: int,
    height: int,
    scale: int,
    output_path: Path,
) -> Path:
    """Render the sprite as a NEAREST-upscaled transparent RGBA PNG via Pillow."""
    from PIL import Image  # Imported lazily to support SVG fallback when missing

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = img.load()
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            rgba = palette[ch]
            if rgba is not None:
                pixels[x, y] = rgba

    resampling_enum = getattr(Image, "Resampling", Image)
    scaled = img.resize((width * scale, height * scale), resample=resampling_enum.NEAREST)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scaled.save(output_path, format="PNG")
    return output_path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="16x16 (veya NxM) ASCII renk matrisinden NEAREST PNG veya crispEdges SVG sprite üretir."
    )
    parser.add_argument(
        "--input", "-i", required=True, type=Path, help="Palette ve grid içeren JSON dosyası."
    )
    parser.add_argument(
        "--output", "-o", required=True, type=Path, help="Çıktı dosya yolu (.png veya .svg)."
    )
    parser.add_argument(
        "--scale", "-s", type=int, default=8, help="Tam sayı ölçek çarpanı (varsayılan: 8)."
    )
    parser.add_argument(
        "--format",
        choices=["auto", "png", "svg"],
        default="auto",
        help="Çıktı formatı (varsayılan: auto - dosya uzantısından çıkarılır).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.scale < 1:
        print("Hata: --scale değeri 1 veya daha büyük bir tam sayı olmalıdır.", file=sys.stderr)
        return 1

    try:
        grid, palette, width, height, sprite_name = load_sprite_spec(args.input)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Girdi hatası: {exc}", file=sys.stderr)
        return 1

    fmt = args.format
    if fmt == "auto":
        fmt = "svg" if args.output.suffix.lower() == ".svg" else "png"

    if fmt == "svg":
        out = render_svg(grid, palette, width, height, args.scale, args.output, sprite_name)
        print(f"[SVG] {out} ({width}x{height} -> {width * args.scale}x{height * args.scale})")
        return 0

    try:
        out = render_png(grid, palette, width, height, args.scale, args.output)
        print(f"[PNG] {out} ({width}x{height} -> {width * args.scale}x{height * args.scale}, NEAREST)")
        return 0
    except ImportError as exc:
        fallback_path = (
            args.output if args.output.suffix.lower() == ".svg" else args.output.with_suffix(".svg")
        )
        print(
            f"Uyarı: Pillow kütüphanesi yüklü değil ({exc}). "
            "PNG üretimi için 'pip install Pillow' çalıştırın. "
            f"crispEdges <rect> SVG fallback moduna geçiliyor -> {fallback_path}",
            file=sys.stderr,
        )
        out = render_svg(grid, palette, width, height, args.scale, fallback_path, sprite_name)
        print(f"[SVG-FALLBACK] {out} ({width}x{height} -> {width * args.scale}x{height * args.scale})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
