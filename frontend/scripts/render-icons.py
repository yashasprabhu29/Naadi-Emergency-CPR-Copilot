"""Render PNG icons from public/favicon.svg. Run: python scripts/render-icons.py (needs PyMuPDF)."""
from pathlib import Path

import fitz  # PyMuPDF

public = Path(__file__).resolve().parent.parent / "public"
svg = (public / "favicon.svg").read_bytes()
square = svg.replace(b'rx="7"', b'rx="0"')  # iOS rounds touch icons itself

for data, size, name, alpha in [
    (svg, 32, "favicon-32.png", True),
    (svg, 512, "icon-512.png", True),
    (square, 180, "apple-touch-icon.png", False),
]:
    page = fitz.open("svg", data)[0]
    zoom = size / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=alpha)
    pix.save(public / name)
    print(name, pix.width, pix.height)
