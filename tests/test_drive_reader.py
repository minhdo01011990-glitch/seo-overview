"""Tests cho src/core/drive_reader.py (chạy offline — không cần Google API)."""

from __future__ import annotations

import pytest
from src.core.drive_reader import (
    detect_data_type_from_filename,
    list_local_folder,
    load_seo_source,
    load_text_source,
)


def test_load_text_source_single_line():
    df = load_text_source("example.com", "my_domain")
    assert list(df.columns) == ["value"]
    assert len(df) == 1
    assert df["value"].iloc[0] == "example.com"


def test_load_text_source_multiline():
    df = load_text_source("a.com\nb.com\nc.com", "competitor_domains")
    assert list(df.columns) == ["value"]
    assert len(df) == 3
    assert list(df["value"]) == ["a.com", "b.com", "c.com"]


def test_load_seo_source_invalid_data_type():
    with pytest.raises(ValueError, match="data_type không hợp lệ"):
        load_seo_source("example.com", "invalid_type")


def test_load_seo_source_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        load_seo_source("/nonexistent/path/data.csv", "keywords")


@pytest.mark.parametrize("filename,expected", [
    ("keywords_hugevn.xlsx",         "keywords"),
    ("monthly-traffic-2026.csv",     "monthly_traffic"),
    ("seo_audit_results.xlsx",       "seo_audit"),
    ("url_traffic_groups.xlsx",      "url_traffic"),
    ("chatgpt_mentions.csv",         "chatgpt_mentions"),
    ("chatgpt_citations_june.xlsx",  "chatgpt_citations"),
    ("referral_domains.xlsx",        "referral_domains"),
    ("backlink-report.csv",          "referral_domains"),
    ("rankings_top100.csv",          "rankings"),
    ("aio_domains.xlsx",             "aio_domains"),
    ("competitor_list.xlsx",         "competitor_domains"),
    ("analysis_comments.txt",        "analysis_comments"),
    ("image_assets.zip",             None),
    ("README.md",                    None),
])
def test_detect_data_type_from_filename(filename, expected):
    assert detect_data_type_from_filename(filename) == expected


def test_list_local_folder(tmp_path):
    (tmp_path / "keywords.csv").write_text("keyword,volume\nseo,1000")
    (tmp_path / "audit.xlsx").write_bytes(b"dummy")
    (tmp_path / "image.png").write_bytes(b"dummy")

    files = list_local_folder(str(tmp_path))
    names = [f["name"] for f in files]
    # CSV và xlsx được liệt kê, png cũng được (filter ở scan_seo_folder)
    assert "keywords.csv" in names
    assert "audit.xlsx" in names
    assert all(f["url"] for f in files)  # url là path tuyệt đối


def test_list_local_folder_nonexistent():
    with pytest.raises(FileNotFoundError):
        list_local_folder("/nonexistent/folder")


def test_list_local_folder_not_a_dir(tmp_path):
    f = tmp_path / "file.csv"
    f.write_text("data")
    with pytest.raises(ValueError, match="không phải folder"):
        list_local_folder(str(f))
