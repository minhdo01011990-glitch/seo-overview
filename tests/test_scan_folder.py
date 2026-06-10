"""Tests cho scan_seo_folder (chạy offline — dùng local folder)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.session_store import save_data_type
from src.tools.input_tools import scan_seo_folder


@pytest.fixture
def sid(tmp_path, monkeypatch):
    import src.core.session_store as ss

    monkeypatch.setattr(ss, "SESSION_DIR", tmp_path)
    return ss.new_session()


def _make_folder(tmp_path, filenames: list[str]):
    folder = tmp_path / "data_folder"
    folder.mkdir()
    for name in filenames:
        (folder / name).write_bytes(b"dummy")
    return str(folder)


def test_scan_clean_folder_no_issues(tmp_path, sid):
    folder = _make_folder(
        tmp_path,
        ["keywords.csv", "monthly_traffic.xlsx", "seo_audit.csv", "rankings.xlsx"],
    )
    result = scan_seo_folder(sid, folder)

    assert result["status"] == "ok"
    assert result["total_files"] == 4
    assert result["has_issues"] is False
    statuses = {f["name"]: f["status"] for f in result["files"]}
    assert statuses["keywords.csv"] == "ok"
    assert statuses["monthly_traffic.xlsx"] == "ok"


def test_scan_detects_duplicates(tmp_path, sid):
    folder = _make_folder(
        tmp_path,
        ["keywords_june.csv", "keywords_may.csv", "seo_audit.xlsx"],
    )
    result = scan_seo_folder(sid, folder)

    assert result["has_issues"] is True
    keyword_files = [f for f in result["files"] if f["detected_type"] == "keywords"]
    assert all(f["status"] == "duplicate" for f in keyword_files)
    assert any("Trùng lặp" in issue for issue in result["issues"])


def test_scan_detects_unknown_files(tmp_path, sid):
    folder = _make_folder(tmp_path, ["keywords.csv", "report_final_v3.xlsx"])
    result = scan_seo_folder(sid, folder)

    assert result["has_issues"] is True
    unknown = [f for f in result["files"] if f["status"] == "unknown"]
    assert len(unknown) == 1
    assert unknown[0]["name"] == "report_final_v3.xlsx"


def test_scan_detects_unsupported_files(tmp_path, sid):
    folder = _make_folder(tmp_path, ["keywords.csv", "dashboard.png", "archive.zip"])
    result = scan_seo_folder(sid, folder)

    assert result["has_issues"] is True
    unsupported = [f for f in result["files"] if f["status"] == "unsupported"]
    names = {f["name"] for f in unsupported}
    assert {"dashboard.png", "archive.zip"} == names


def test_scan_empty_folder(tmp_path, sid):
    folder = tmp_path / "empty"
    folder.mkdir()
    result = scan_seo_folder(sid, str(folder))

    assert result["status"] == "ok"
    assert result["total_files"] == 0
    assert result["has_issues"] is True


def test_scan_invalid_session(tmp_path):
    result = scan_seo_folder("nonexistent_session", str(tmp_path))
    assert result["status"] == "error"
    assert "không tồn tại" in result["error"]


def test_scan_nonexistent_folder(tmp_path, sid):
    result = scan_seo_folder(sid, "/nonexistent/folder/path")
    assert result["status"] == "error"


def test_scan_files_have_correct_urls(tmp_path, sid):
    folder = _make_folder(tmp_path, ["keywords.csv"])
    result = scan_seo_folder(sid, folder)

    f = result["files"][0]
    # url phải là path tuyệt đối trỏ đúng file
    assert f["url"].endswith("keywords.csv")
    assert f["detected_type"] == "keywords"
