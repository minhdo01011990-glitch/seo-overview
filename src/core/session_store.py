"""Session-based checkpoint cho SEO data types."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


SESSION_DIR = Path.home() / ".seo-overview"

VALID_DATA_TYPES = {
    "my_domain", "competitor_domains", "keywords", "keyword_aio", "ranking_aio",
    "rankings", "url_traffic", "monthly_traffic", "referral_domains", "seo_audit",
    "chatgpt_prompts", "chatgpt_mentions", "chatgpt_citations", "analysis_comments",
    "img_overview",
}


def _session_path(session_id: str) -> Path:
    return SESSION_DIR / session_id


def new_session() -> str:
    session_id = uuid.uuid4().hex[:12]
    path = _session_path(session_id)
    path.mkdir(parents=True, exist_ok=True)
    meta = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "loaded_types": {},
    }
    (path / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return session_id


def _load_meta(session_id: str) -> dict:
    path = _session_path(session_id) / "meta.json"
    if not path.exists():
        raise FileNotFoundError(f"Session '{session_id}' không tồn tại")
    return json.loads(path.read_text())


def _save_meta(session_id: str, meta: dict) -> None:
    (_session_path(session_id) / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False)
    )


def save_data_type(session_id: str, data_type: str, df) -> Path:
    """Lưu DataFrame parquet cho data_type, cập nhật meta."""
    if data_type not in VALID_DATA_TYPES:
        raise ValueError(
            f"data_type không hợp lệ: '{data_type}'. Hợp lệ: {sorted(VALID_DATA_TYPES)}"
        )

    meta = _load_meta(session_id)  # validate session tồn tại trước khi ghi file
    path = _session_path(session_id) / f"{data_type}.parquet"
    df.to_parquet(path, compression="gzip", index=False)
    meta["loaded_types"][data_type] = {
        "rows": len(df),
        "columns": list(df.columns),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_meta(session_id, meta)
    return path


def load_data_type(session_id: str, data_type: str):
    """Đọc parquet checkpoint cho data_type."""
    import pandas as pd

    path = _session_path(session_id) / f"{data_type}.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"data_type '{data_type}' chưa được load cho session {session_id}"
        )
    return pd.read_parquet(path)


def list_loaded_types(session_id: str) -> dict[str, dict]:
    """Trả về {data_type: {rows, columns, loaded_at}} của các types đã load."""
    return _load_meta(session_id).get("loaded_types", {})


def session_exists(session_id: str) -> bool:
    return (_session_path(session_id) / "meta.json").exists()
