"""Tests cho src/core/report_generator.py."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_chart_b64() -> str:
    """Tạo PNG nhỏ dưới dạng base64 (không cần matplotlib)."""
    import struct, zlib

    def _chunk(name: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + name + data
        return c + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

    w, h = 2, 2
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    # 2x2 RGB image: all white
    raw = b"\x00" + b"\xff\xff\xff" * w
    idat = _chunk(b"IDAT", zlib.compress(raw * h))
    iend = _chunk(b"IEND", b"")
    png_bytes = sig + ihdr + idat + iend
    return base64.b64encode(png_bytes).decode()


def _minimal_context(*, with_charts: bool = False) -> dict:
    chart = {"title": "Test Chart", "image_b64": _make_chart_b64()}
    return {
        "title": "SEO Report Test",
        "my_domain": "example.com",
        "generated_at": "2024-01-01",
        "sections": [
            {
                "id": "organic_traffic",
                "title": "Organic Traffic",
                "key_insights": ["Traffic tăng 50%"],
                "content_html": "<p>Test content</p>",
                "charts": [chart] if with_charts else [],
            }
        ],
        "missing_sections": [],
    }


_TEMPLATES_DIR = str(Path(__file__).parent.parent / "templates")


# ── generate_html ──────────────────────────────────────────────────────────────

def test_generate_html_file_exists_and_not_empty(tmp_path):
    from src.core.report_generator import generate_html

    out = str(tmp_path / "report.html")
    generate_html(_minimal_context(), out, _TEMPLATES_DIR)

    p = Path(out)
    assert p.exists()
    assert p.stat().st_size > 0


def test_generate_html_contains_my_domain(tmp_path):
    from src.core.report_generator import generate_html

    out = str(tmp_path / "report.html")
    generate_html(_minimal_context(), out, _TEMPLATES_DIR)

    content = Path(out).read_text(encoding="utf-8")
    assert "example.com" in content


# ── generate_docx ─────────────────────────────────────────────────────────────

def test_generate_docx_opens_with_python_docx(tmp_path):
    from docx import Document
    from src.core.report_generator import generate_docx

    out = str(tmp_path / "report.docx")
    generate_docx(_minimal_context(), out)

    doc = Document(out)
    assert len(doc.paragraphs) > 0


# ── generate_png ──────────────────────────────────────────────────────────────

def test_generate_png_returns_png_paths(tmp_path):
    from src.core.report_generator import generate_png

    paths = generate_png(_minimal_context(with_charts=True), str(tmp_path))

    assert len(paths) > 0
    for p in paths:
        assert p.endswith(".png")
        assert Path(p).exists()
