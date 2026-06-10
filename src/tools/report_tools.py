"""MCP tool wrapper cho generate_seo_report."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.data_processor import build_report_context
from src.core.report_generator import (
    generate_docx,
    generate_html,
    generate_png,
    generate_pptx,
    upload_to_drive,
)
from src.core.session_store import session_exists

_VALID_FORMATS = {"docx", "html", "pptx", "png"}


def generate_seo_report(
    session_id: str,
    formats: list[str],
    output_dir: str,
    upload_drive_url: Optional[str] = None,
) -> dict:
    """
    Tạo báo cáo SEO ở các định dạng được chọn, tuỳ chọn upload lên Google Drive.
    formats: subset của ["docx", "html", "pptx", "png"]
    output_dir: thư mục lưu file (expanduser được áp dụng)
    upload_drive_url: Google Drive folder URL (tuỳ chọn)
    """
    if not formats:
        return {
            "status": "error",
            "files": [],
            "drive_urls": [],
            "skipped_sections": [],
            "errors": [{"format": "validation", "error": "formats không được rỗng. Chọn từ: " + ", ".join(sorted(_VALID_FORMATS))}],
        }

    invalid = [f for f in formats if f not in _VALID_FORMATS]
    if invalid:
        return {
            "status": "error",
            "files": [],
            "drive_urls": [],
            "skipped_sections": [],
            "errors": [{"format": "validation", "error": f"Format không hợp lệ: {invalid}. Chọn từ: {sorted(_VALID_FORMATS)}"}],
        }

    if not session_exists(session_id):
        return {
            "status": "error",
            "files": [],
            "drive_urls": [],
            "skipped_sections": [],
            "errors": [
                {"format": "all", "error": f"Session '{session_id}' không tồn tại"}
            ],
        }

    try:
        context = build_report_context(session_id)
    except Exception as exc:
        return {
            "status": "error",
            "files": [],
            "drive_urls": [],
            "skipped_sections": [],
            "errors": [{"format": "all", "error": str(exc)}],
        }

    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    domain_slug = re.sub(r"[^\w.-]", "_", context["my_domain"]).strip("_") or "unknown"
    date_str = datetime.now().strftime("%Y%m%d")
    base_name = f"seo-report_{domain_slug}_{date_str}"

    files: list[dict] = []
    errors: list[dict] = []

    _generators = {
        "html":  lambda: (generate_html(context, str(out_dir / f"{base_name}.html")), "html"),
        "docx":  lambda: (generate_docx(context, str(out_dir / f"{base_name}.docx")), "docx"),
        "pptx":  lambda: (generate_pptx(context, str(out_dir / f"{base_name}.pptx")), "pptx"),
    }

    for fmt in formats:
        if fmt == "png":
            try:
                png_paths = generate_png(context, str(out_dir / "png"))
                for pp in png_paths:
                    files.append({
                        "format": "png",
                        "path": pp,
                        "size_kb": round(Path(pp).stat().st_size / 1024, 1),
                    })
            except Exception as exc:
                errors.append({"format": "png", "error": str(exc)})
        elif fmt in _generators:
            try:
                path, label = _generators[fmt]()
                files.append({
                    "format": label,
                    "path": path,
                    "size_kb": round(Path(path).stat().st_size / 1024, 1),
                })
            except Exception as exc:
                errors.append({"format": fmt, "error": str(exc)})

    drive_urls: list[dict] = []
    if upload_drive_url and files:
        try:
            upload_paths = [f["path"] for f in files]
            drive_results = upload_to_drive(upload_paths, upload_drive_url)
            drive_urls = [
                {
                    "format": Path(r["file"]).suffix.lstrip("."),
                    "url": r.get("url"),
                    "drive_id": r.get("drive_id"),
                }
                for r in drive_results
                if r.get("url")
            ]
        except Exception as exc:
            errors.append({"format": "upload", "error": str(exc)})

    skipped = [ms["title"] for ms in context.get("missing_sections", [])]
    status = "ok" if not errors else ("partial" if files else "error")

    return {
        "status": status,
        "files": files,
        "drive_urls": drive_urls,
        "skipped_sections": skipped,
        "errors": errors,
    }
