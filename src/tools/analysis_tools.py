"""MCP tool wrapper cho generate_analysis_outline."""

from __future__ import annotations

from src.core.data_processor import (
    SECTION_ORDER,
    SECTION_REQUIREMENTS,
    SECTION_TITLES,
    build_report_context,
    get_available_sections,
)
from src.core.session_store import list_loaded_types, session_exists


def generate_analysis_outline(session_id: str) -> dict:
    """
    Phân tích session và trả về outline báo cáo với key insights của từng section.
    Không gọi external API — chỉ đọc session state + chạy data_processor.
    """
    if not session_exists(session_id):
        return {
            "available_sections": [],
            "skipped_sections": [],
            "recommendation": (
                f"Session '{session_id}' không tồn tại. "
                "Gọi create_seo_session() trước."
            ),
        }

    loaded = list_loaded_types(session_id)
    loaded_keys = set(loaded.keys())
    available_ids = get_available_sections(loaded_keys)

    if not available_ids:
        skipped = [
            {
                "id": s,
                "title": SECTION_TITLES[s],
                "missing": SECTION_REQUIREMENTS[s],
            }
            for s in SECTION_ORDER
        ]
        return {
            "available_sections": [],
            "skipped_sections": skipped,
            "recommendation": (
                "Chưa có đủ dữ liệu để tạo báo cáo. "
                "Load ít nhất 1 data type cần thiết."
            ),
        }

    context = build_report_context(session_id)

    available_sections = [
        {
            "id": sec["id"],
            "title": sec["title"],
            "key_insights": sec.get("key_insights", []),
        }
        for sec in context["sections"]
    ]

    skipped_sections = [
        {
            "id": ms["id"],
            "title": ms["title"],
            "missing": [r for r in SECTION_REQUIREMENTS[ms["id"]] if r not in loaded_keys],
        }
        for ms in context["missing_sections"]
    ]

    n_avail = len(available_sections)
    n_total = len(SECTION_ORDER)

    if n_avail == n_total:
        recommendation = "Đủ dữ liệu cho báo cáo đầy đủ."
    else:
        missing_dt = sorted({
            dt
            for s in skipped_sections
            for dt in s["missing"]
        })
        recommendation = (
            f"Có thể tạo {n_avail}/{n_total} sections. "
            f"Thiếu {n_total - n_avail} sections — load thêm: "
            + ", ".join(missing_dt)
        )

    return {
        "available_sections": available_sections,
        "skipped_sections": skipped_sections,
        "recommendation": recommendation,
    }
