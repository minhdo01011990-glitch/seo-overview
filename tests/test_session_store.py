"""Tests cho src/core/session_store.py."""

from __future__ import annotations

import pandas as pd
import pytest
import src.core.session_store as ss


def test_new_session_returns_12_char_id_and_creates_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "SESSION_DIR", tmp_path)
    sid = ss.new_session()
    assert len(sid) == 12
    assert (tmp_path / sid / "meta.json").exists()


def test_two_sessions_have_different_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "SESSION_DIR", tmp_path)
    assert ss.new_session() != ss.new_session()


def test_save_and_load_roundtrip(session_id, keywords_df):
    ss.save_data_type(session_id, "keywords", keywords_df)
    loaded = ss.load_data_type(session_id, "keywords")
    assert list(loaded.columns) == list(keywords_df.columns)
    assert len(loaded) == len(keywords_df)


def test_load_unloaded_type_raises(session_id):
    with pytest.raises(FileNotFoundError):
        ss.load_data_type(session_id, "rankings")


def test_list_loaded_types(session_id, keywords_df, monthly_traffic_df):
    assert ss.list_loaded_types(session_id) == {}
    ss.save_data_type(session_id, "keywords", keywords_df)
    ss.save_data_type(session_id, "monthly_traffic", monthly_traffic_df)
    loaded = ss.list_loaded_types(session_id)
    assert set(loaded.keys()) == {"keywords", "monthly_traffic"}
    assert loaded["keywords"]["rows"] == len(keywords_df)
    assert loaded["monthly_traffic"]["rows"] == len(monthly_traffic_df)
