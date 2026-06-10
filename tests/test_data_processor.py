"""Tests cho src/core/data_processor.py."""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.data_processor import (
    get_available_sections,
    process_organic_traffic,
    process_ranking_analysis,
    SECTION_REQUIREMENTS,
)


# ── get_available_sections ────────────────────────────────────────────────────

def test_no_loaded_types_returns_empty():
    assert get_available_sections([]) == []


def test_keywords_only_no_search_behavior():
    sections = get_available_sections(["keywords"])
    assert "search_behavior" not in sections


def test_keywords_and_aio_domains_gives_search_behavior():
    sections = get_available_sections(["keywords", "aio_domains"])
    assert "search_behavior" in sections


def test_all_required_types_gives_8_sections():
    all_required = list({dt for types in SECTION_REQUIREMENTS.values() for dt in types})
    sections = get_available_sections(all_required)
    assert len(sections) == 8


# ── process_organic_traffic ───────────────────────────────────────────────────

def test_organic_traffic_has_required_keys(monthly_traffic_df):
    result = process_organic_traffic(monthly_traffic_df)
    assert "months" in result
    assert "peak_month" in result
    assert "trend_direction" in result


def test_organic_traffic_peak_month(monthly_traffic_df):
    # sessions: [3100, 3400, 3800, 4200, 5100, 4700] — max là 5100 tháng 2024-05
    result = process_organic_traffic(monthly_traffic_df)
    assert result["peak_month"] == "2024-05"


def test_organic_traffic_empty_raises():
    with pytest.raises(ValueError, match="Không có dữ liệu"):
        process_organic_traffic(pd.DataFrame())


# ── process_ranking_analysis ──────────────────────────────────────────────────

def test_ranking_analysis_top3_and_top10_counts():
    df = pd.DataFrame({
        "keyword": [f"kw{i}" for i in range(10)],
        "position": [1, 2, 3, 5, 7, 8, 10, 15, 18, 25],
    })
    result = process_ranking_analysis(df)
    assert result["top3_count"] == 3
    assert result["top10_count"] == 7
