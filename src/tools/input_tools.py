"""MCP tool wrappers cho session management và data loading."""

from __future__ import annotations

import base64
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src.core.data_processor import (
    SECTION_REQUIREMENTS,
    SECTION_TITLES,
    get_available_sections,
)
import pandas as pd

from src.core.drive_reader import (
    DRIVE_FOLDER_URL_RE,
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_MIME_TYPES,
    detect_data_type_from_filename,
    detect_domain_from_filename,
    list_drive_folder,
    list_local_folder,
    load_seo_source,
)
from src.core.session_store import (
    VALID_DATA_TYPES,
    list_loaded_types,
    load_data_type,
    new_session,
    save_data_type,
    session_exists,
)


def create_seo_session() -> dict:
    """Tạo session mới cho quy trình phân tích SEO."""
    session_id = new_session()
    return {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def load_seo_input(
    session_id: str,
    data_type: str,
    source: str,
    domain: str | None = None,
) -> dict:
    """Đọc một data type từ Google Sheets / file / text và lưu vào session.

    domain: tên domain nếu file thuộc về 1 domain cụ thể (per-domain files).
      - Nếu domain được cung cấp, thêm cột 'domain' vào DataFrame và ghép (append)
        với data cùng type đã load trước đó thay vì ghi đè.
      - Nếu domain=None (global files), ghi đè data_type cũ.
    """
    if not session_exists(session_id):
        return {
            "status": "error",
            "data_type": data_type,
            "rows": 0,
            "columns": [],
            "preview": [],
            "error": f"Session '{session_id}' không tồn tại. Gọi create_seo_session() trước.",
        }

    if data_type not in VALID_DATA_TYPES:
        return {
            "status": "error",
            "data_type": data_type,
            "rows": 0,
            "columns": [],
            "preview": [],
            "error": (
                f"data_type '{data_type}' không hợp lệ. "
                f"Hợp lệ: {sorted(VALID_DATA_TYPES)}"
            ),
        }

    try:
        df = load_seo_source(source, data_type)

        if domain:
            if "domain" not in df.columns:
                df = df.copy()
                df["domain"] = domain
            try:
                existing = load_data_type(session_id, data_type)
                df = pd.concat([existing, df], ignore_index=True)
            except FileNotFoundError:
                pass

        save_data_type(session_id, data_type, df)
        result: dict = {
            "status": "ok",
            "data_type": data_type,
            "rows": len(df),
            "columns": list(df.columns),
            "preview": df.head(3).astype(str).to_dict(orient="records"),
            "error": None,
        }

        # Nếu là ảnh chưa extract → đính kèm base64 để Claude dùng visualize đọc
        if (
            data_type == "img_overview"
            and "status" in df.columns
            and (df["status"] == "pending_extraction").any()
        ):
            img_path_str = df["file_path"].iloc[0] if "file_path" in df.columns else None
            if img_path_str:
                img_path = Path(img_path_str)
                if img_path.exists() and img_path.suffix.lower() in IMAGE_EXTENSIONS:
                    suffix = img_path.suffix.lower()
                    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
                    result["image_b64"] = base64.b64encode(img_path.read_bytes()).decode()
                    result["image_mime"] = mime_map.get(suffix, "image/png")
                    result["image_instruction"] = (
                        "Dùng visualize để hiển thị ảnh này và đọc thông tin SEO từ ảnh. "
                        "Sau đó gọi load_seo_input với data_type='img_overview' và source là text "
                        "dạng 'Metric: value' mỗi dòng để lưu dữ liệu đã extract."
                    )

        return result
    except Exception as exc:
        return {
            "status": "error",
            "data_type": data_type,
            "rows": 0,
            "columns": [],
            "preview": [],
            "error": str(exc),
        }


def scan_seo_folder(session_id: str, folder_url: str) -> dict:
    """
    Quét một folder (Google Drive hoặc đường dẫn local) để phát hiện và phân loại data files.

    Với mỗi file, heuristic đoán data_type từ tên file rồi gán status:
      ok          — nhận dạng được, không trùng lặp
      duplicate   — nhiều files cùng data_type
      unknown     — không nhận dạng được data_type từ tên file
      unsupported — định dạng không hỗ trợ (không phải Sheet/CSV/Excel)

    Trả về danh sách files để agent trình bày cho user xác nhận trước khi gọi load_seo_input.
    """
    if not session_exists(session_id):
        return {
            "status": "error",
            "error": f"Session '{session_id}' không tồn tại. Gọi create_seo_session() trước.",
            "files": [],
            "issues": [],
            "has_issues": False,
        }

    is_drive = bool(DRIVE_FOLDER_URL_RE.search(folder_url))
    try:
        if is_drive:
            raw_files = list_drive_folder(folder_url)
        else:
            raw_files = list_local_folder(folder_url)
    except (PermissionError, FileNotFoundError, ValueError, EnvironmentError) as exc:
        return {
            "status": "error",
            "error": str(exc),
            "files": [],
            "issues": [],
            "has_issues": False,
        }

    if not raw_files:
        return {
            "status": "ok",
            "folder_url": folder_url,
            "total_files": 0,
            "files": [],
            "issues": ["Folder trống — không tìm thấy file nào."],
            "has_issues": True,
        }

    # Đọc danh sách domains đã load trong session để hỗ trợ detect_domain
    known_domains: list[str] = []
    for dtype, col in (("my_domain", "value"), ("competitor_domains", "value")):
        try:
            d = load_data_type(session_id, dtype)
            if col in d.columns:
                known_domains.extend(d[col].dropna().tolist())
        except (FileNotFoundError, KeyError):
            pass

    # Pass 1: phát hiện data_type, domain và kiểm tra định dạng từng file
    enriched: list[dict] = []
    for f in raw_files:
        mime = f.get("mime_type", "")
        ext = Path(f["name"]).suffix.lower()
        is_supported = mime in SUPPORTED_MIME_TYPES or ext in SUPPORTED_EXTENSIONS or (
            not mime and ext in SUPPORTED_EXTENSIONS
        )
        detected_type = detect_data_type_from_filename(f["name"])
        # Ảnh không match pattern nào → auto-gán img_overview
        if detected_type is None and ext in IMAGE_EXTENSIONS:
            detected_type = "img_overview"
        enriched.append({
            **f,
            "detected_type": detected_type,
            "detected_domain": detect_domain_from_filename(f["name"], known_domains),
            "supported": is_supported,
        })

    # Pass 2: tìm trùng lặp theo tên file (exact same filename)
    name_counts: dict[str, int] = defaultdict(int)
    for f in enriched:
        name_counts[f["name"]] += 1

    result_files: list[dict] = []
    for idx, f in enumerate(enriched, 1):
        dtype = f["detected_type"]
        if not f["supported"]:
            ext = Path(f["name"]).suffix
            status = "unsupported"
            reason = f"Định dạng '{ext}' không hỗ trợ. Hỗ trợ: Google Sheets, .csv, .xlsx, ảnh (.png/.jpg/.gif/.bmp...), .md, .html, .txt."
        elif name_counts[f["name"]] > 1:
            status = "duplicate"
            reason = "Tên file trùng — file này xuất hiện nhiều lần trong folder."
        elif dtype is None:
            status = "unknown"
            reason = "Không nhận dạng được data type từ tên file. Cần chỉ định thủ công."
        else:
            status = "ok"
            reason = None

        result_files.append({
            "index": idx,
            "name": f["name"],
            "url": f["url"],
            "detected_type": dtype,
            "detected_domain": f.get("detected_domain"),
            "status": status,
            "reason": reason,
        })

    # Tổng hợp issues
    issues: list[str] = []
    duplicate_names = [name for name, count in name_counts.items() if count > 1]
    if duplicate_names:
        issues.append(f"⚠ Tên file trùng: {', '.join(duplicate_names)}")
    unknowns = [f["name"] for f in result_files if f["status"] == "unknown"]
    if unknowns:
        issues.append(f"⚠ Không nhận dạng: {', '.join(unknowns)}")
    unsupported = [f["name"] for f in result_files if f["status"] == "unsupported"]
    if unsupported:
        issues.append(f"✗ Không hỗ trợ (sẽ bỏ qua tự động): {', '.join(unsupported)}")

    return {
        "status": "ok",
        "folder_url": folder_url,
        "total_files": len(result_files),
        "files": result_files,
        "issues": issues,
        "has_issues": bool(issues),
    }


def get_session_summary(session_id: str) -> dict:
    """Trả về trạng thái session: data types đã load và sections có thể tạo."""
    if not session_exists(session_id):
        return {
            "session_id": session_id,
            "available": {},
            "missing": sorted(VALID_DATA_TYPES),
            "available_sections": [],
            "missing_sections": [
                {
                    "id": s,
                    "title": SECTION_TITLES[s],
                    "missing_data": SECTION_REQUIREMENTS[s],
                }
                for s in SECTION_REQUIREMENTS
            ],
            "error": f"Session '{session_id}' không tồn tại",
        }

    loaded = list_loaded_types(session_id)
    loaded_keys = list(loaded.keys())
    missing = [t for t in sorted(VALID_DATA_TYPES) if t not in loaded]
    available_ids = get_available_sections(loaded_keys)
    missing_section_ids = [s for s in SECTION_REQUIREMENTS if s not in available_ids]

    return {
        "session_id": session_id,
        "available": {
            k: {"rows": v["rows"], "loaded_at": v["loaded_at"]}
            for k, v in loaded.items()
        },
        "missing": missing,
        "available_sections": available_ids,
        "missing_sections": [
            {
                "id": s,
                "title": SECTION_TITLES[s],
                "missing_data": [r for r in SECTION_REQUIREMENTS[s] if r not in loaded],
            }
            for s in missing_section_ids
        ],
    }
