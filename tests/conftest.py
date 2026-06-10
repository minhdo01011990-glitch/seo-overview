"""Shared pytest fixtures cho toàn bộ test suite."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def session_id(tmp_path, monkeypatch):
    """Session sạch trong tmp_path — không đụng ~/.seo-overview."""
    import src.core.session_store as ss
    monkeypatch.setattr(ss, "SESSION_DIR", tmp_path)
    return ss.new_session()


@pytest.fixture
def keywords_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "keyword": ["seo tool", "backlink checker", "rank tracker", "keyword research"],
            "volume": [12000, 8500, 4200, 22000],
            "intent": ["commercial", "commercial", "commercial", "informational"],
        }
    )


@pytest.fixture
def monthly_traffic_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "month": ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"],
            "sessions": [3100, 3400, 3800, 4200, 5100, 4700],
            "organic": [2800, 3100, 3500, 3900, 4800, 4400],
        }
    )


@pytest.fixture
def session_with_keywords(session_id, keywords_df, monkeypatch, tmp_path):
    """Session đã load data type 'keywords'."""
    import src.core.session_store as ss
    monkeypatch.setattr(ss, "SESSION_DIR", tmp_path)
    ss.save_data_type(session_id, "keywords", keywords_df)
    return session_id
