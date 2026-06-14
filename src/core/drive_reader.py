"""Đọc dữ liệu SEO từ Google Sheets, CSV, Excel, hoặc text input."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd

from src.core.session_store import VALID_DATA_TYPES

# Data types nhận text input thay vì spreadsheet
TEXT_DATA_TYPES = {"my_domain", "competitor_domains", "chatgpt_prompts", "analysis_comments", "img_overview"}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif"}

TEXT_FILE_EXTENSIONS = {".md", ".html", ".htm", ".txt"}

SHEETS_URL_RE = re.compile(r"https?://docs\.google\.com/spreadsheets")
DRIVE_FOLDER_URL_RE = re.compile(
    r"https?://drive\.google\.com/drive(?:/u/\d+)?/folders/([a-zA-Z0-9_\-]+)"
)

# Extensions và MIME types hỗ trợ khi quét folder
SUPPORTED_EXTENSIONS = {
    ".csv", ".xlsx", ".xls", ".xlsm",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff", ".tif",
    ".md", ".html", ".htm", ".txt",
}
SUPPORTED_MIME_TYPES = {
    "application/vnd.google-apps.spreadsheet",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/vnd.ms-excel.sheet.macroEnabled.12",
    "image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp", "image/tiff",
    "text/markdown", "text/html", "text/plain",
}

# Heuristic patterns để đoán data_type từ tên file — thứ tự quan trọng (specific trước)
_DTYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"img[_\-. ]?overview|overview[_\-. ]?img|screenshot|screen[_\-. ]?shot|tong[_\-. ]?quan[_\-. ]?img", re.I), "img_overview"),
    (re.compile(r"url[_\-. ]?traffic|url[_\-. ]?group|traffic[_\-. ]?url|traffic[_\-. ]?group|url[_\-. ]?labeler|labeler|top[_\-. ]?page|toppage", re.I), "url_traffic"),
    (re.compile(r"monthly[_\-. ]?traffic|traffic[_\-. ]?monthly|organic[_\-. ]?traffic|traffic[_\-. ]?organic|perf[_\-. ]?sub|subdomain[_\-. ]?perf|top[_\-. ]?overview|topoverview", re.I), "monthly_traffic"),
    (re.compile(r"chatgpt[_\-. ]?mention|mention[_\-. ]?chatgpt|brand[_\-. ]?mention", re.I), "chatgpt_mentions"),
    (re.compile(r"chatgpt[_\-. ]?cit|citation|chatgpt[_\-. ]?domain", re.I), "chatgpt_citations"),
    (re.compile(r"chatgpt[_\-. ]?prompt|prompt[_\-. ]?chatgpt|ai[_\-. ]?prompt", re.I), "chatgpt_prompts"),
    (re.compile(r"referral|backlink|ref[_\-. ]?domain|domain[_\-. ]?ref|referring", re.I), "referral_domains"),
    (re.compile(r"seo[_\-. ]?audit|audit[_\-. ]?seo|audit", re.I), "seo_audit"),
    (re.compile(r"ranking[_\-. ]?aio|aio[_\-. ]?rank", re.I), "ranking_aio"),
    (re.compile(r"keyword|kw(?:[^a-z]|$)", re.I), "keywords"),
    (re.compile(r"ranking|rank(?:[^a-z]|$)|position|checktop|check[_\-. ]?top", re.I), "rankings"),
    (re.compile(r"competitor|rival|đối[_\-. ]?thủ", re.I), "competitor_domains"),
    (re.compile(r"aio|ai[_\-. ]?overview|keyword[_\-. ]?aio", re.I), "keyword_aio"),
    (re.compile(r"comment|note|nhận[_\-. ]?xét|analysis[_\-. ]?comment", re.I), "analysis_comments"),
    (re.compile(r"my[_\-. ]?domain|client[_\-. ]?domain", re.I), "my_domain"),
]


_SEO_HEADER_KEYWORDS = {
    "domain", "keyword", "position", "rank", "volume", "top 1", "top 3",
    "average", "intent", "url", "session", "traffic", "severity", "issue",
    "month", "organic", "page", "backlink", "spam", "rate", "category",
}


def _auto_detect_real_header(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fix Semrush / tool exports that embed metadata rows before the real header.
    Scans the first 10 rows for a row whose values match ≥2 known SEO column terms.
    If found, rebuilds the DataFrame using that row as the header.
    """
    # Heuristic: suspicious if the first column header is very long or contains ":"
    first_col = str(df.columns[0]).lower()
    unnamed_count = sum(1 for c in df.columns if str(c).lower().startswith("unnamed"))
    suspicious = (
        len(first_col) > 40
        or ":" in first_col
        or unnamed_count > len(df.columns) * 0.4
    )
    if not suspicious:
        return df

    for i in range(min(10, len(df))):
        row_vals = [str(v).strip().lower() for v in df.iloc[i].values]
        non_empty = [v for v in row_vals if v and v != "nan"]
        if len(non_empty) < 3:
            continue
        matches = sum(
            1 for v in non_empty
            for kw in _SEO_HEADER_KEYWORDS if kw in v
        )
        if matches >= 2:
            new_df = df.iloc[i + 1:].copy()
            new_df.columns = [str(h).strip().lower() for h in df.iloc[i].values]
            # Drop columns that are still empty / unnamed after re-header
            new_df = new_df.loc[:, ~new_df.columns.str.startswith("unnamed")]
            new_df = new_df.loc[:, new_df.columns.str.strip() != ""]
            new_df = new_df.dropna(how="all").reset_index(drop=True)
            return new_df

    return df


def _get_gspread_client():
    """Tạo gspread client từ service account JSON env var."""
    import gspread

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise EnvironmentError(
            "Cần set biến môi trường GOOGLE_SERVICE_ACCOUNT_JSON "
            "(đường dẫn file hoặc JSON string)"
        )

    if sa_json.strip().startswith("{"):
        return gspread.service_account_from_dict(json.loads(sa_json))
    return gspread.service_account(filename=sa_json)


def load_sheet_as_dataframe(url: str, worksheet_index: int = 0) -> pd.DataFrame:
    """Đọc Google Sheet thành DataFrame (1 batch API call, không paginate)."""
    import gspread
    import gspread_dataframe

    client = _get_gspread_client()
    try:
        sheet = client.open_by_url(url).get_worksheet(worksheet_index)
    except gspread.exceptions.APIError as e:
        status = e.args[0].get("code") if e.args else None
        if status == 403:
            raise PermissionError(
                f"Không có quyền truy cập Sheet. "
                f"Hãy share Sheet với service account email rồi thử lại.\nURL: {url}"
            ) from e
        raise

    df = gspread_dataframe.get_as_dataframe(
        sheet,
        evaluate_formulas=False,
        dtype=str,
        na_filter=False,
    )
    df = df.dropna(how="all", axis=0).dropna(how="all", axis=1)
    # Bỏ các cột Unnamed mà gspread_dataframe sinh ra từ cột trống của Sheet
    df = df.loc[:, ~df.columns.astype(str).str.lower().str.startswith("unnamed")]
    if df.empty:
        raise ValueError("Sheet không có dữ liệu")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = _auto_detect_real_header(df)
    if df.empty:
        raise ValueError("Sheet không có dữ liệu")
    return df.reset_index(drop=True)


def load_local_file(path: str) -> pd.DataFrame:
    """Đọc file CSV hoặc Excel local."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    suffix = p.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(p, dtype=str)
    elif suffix in {".xlsx", ".xls", ".xlsm"}:
        df = pd.read_excel(p, dtype=str)
    else:
        raise ValueError(f"Định dạng file không hỗ trợ: {suffix}. Dùng CSV hoặc Excel.")

    df = df.dropna(how="all")
    if df.empty:
        raise ValueError("File không có dữ liệu")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = _auto_detect_real_header(df)
    if df.empty:
        raise ValueError("File không có dữ liệu")
    return df.reset_index(drop=True)


def load_text_source(text: str, data_type: str) -> pd.DataFrame:
    """Chuyển text input thành DataFrame theo data_type."""
    text = text.strip()
    if not text:
        raise ValueError("Text input trống")

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if data_type == "my_domain":
        return pd.DataFrame({"value": [lines[0]]})
    elif data_type == "competitor_domains":
        return pd.DataFrame({"value": lines})
    elif data_type == "chatgpt_prompts":
        return pd.DataFrame({"prompt": lines})
    elif data_type == "analysis_comments":
        return pd.DataFrame({"comment": [text]})
    elif data_type == "img_overview":
        rows = []
        for line in lines:
            if ":" in line:
                key, _, val = line.partition(":")
                rows.append({"metric": key.strip(), "value": val.strip()})
            elif line:
                rows.append({"metric": line.strip(), "value": ""})
        return pd.DataFrame(rows) if rows else pd.DataFrame({"metric": lines, "value": ""})
    else:
        raise ValueError(f"data_type '{data_type}' không hỗ trợ text input")


def detect_data_type_from_filename(filename: str) -> str | None:
    """Heuristic: đoán data_type từ tên file (không kể extension). Trả về None nếu không nhận dạng."""
    stem = Path(filename).stem
    for pattern, dtype in _DTYPE_PATTERNS:
        if pattern.search(stem):
            return dtype
    return None


def detect_domain_from_filename(filename: str, known_domains: list[str]) -> str | None:
    """Tìm domain name trong tên file dựa vào danh sách known_domains.

    Lấy phần đầu tiên của domain (trước dấu chấm) để khớp, ví dụ:
      "huge.com.vn" → tìm "huge" trong stem của filename.
    Trả về domain đầy đủ nếu khớp, None nếu không tìm thấy.
    """
    if not known_domains:
        return None
    stem = Path(filename).stem.lower()
    for domain in known_domains:
        name_part = domain.lower().split(".")[0]
        if len(name_part) >= 3 and name_part in stem:
            return domain
    return None


def _get_drive_service():
    """Tạo Google Drive API v3 service từ service account credentials."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_json:
        raise EnvironmentError(
            "Cần set biến môi trường GOOGLE_SERVICE_ACCOUNT_JSON "
            "(đường dẫn file hoặc JSON string)"
        )

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    raw = sa_json.strip()
    if raw.startswith("{"):
        creds = Credentials.from_service_account_info(json.loads(raw), scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(raw, scopes=scopes)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_drive_folder(folder_url: str) -> list[dict]:
    """
    Liệt kê tất cả files trong một Google Drive folder.
    Returns: list of {name, id, mime_type, url, size_bytes}
    """
    m = DRIVE_FOLDER_URL_RE.search(folder_url)
    if not m:
        raise ValueError(
            "URL không phải Google Drive folder. "
            "Dùng URL dạng: https://drive.google.com/drive/folders/<id>"
        )
    folder_id = m.group(1)

    try:
        service = _get_drive_service()
    except EnvironmentError:
        raise
    except Exception as exc:
        raise EnvironmentError(f"Không thể kết nối Google Drive API: {exc}") from exc

    files: list[dict] = []
    page_token = None
    while True:
        try:
            resp = (
                service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, name, mimeType, size, webViewLink)",
                    pageToken=page_token,
                    pageSize=100,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
        except Exception as exc:
            status_code = getattr(exc, "status_code", None) or int(
                getattr(getattr(exc, "resp", None), "status", 0) or 0
            )
            if status_code == 403:
                raise PermissionError(
                    f"Không có quyền truy cập folder. "
                    f"Hãy share folder với service account email rồi thử lại.\nURL: {folder_url}"
                ) from exc
            raise

        for f in resp.get("files", []):
            mime = f.get("mimeType", "")
            if mime == "application/vnd.google-apps.spreadsheet":
                url = f"https://docs.google.com/spreadsheets/d/{f['id']}"
            else:
                url = f.get("webViewLink", "")
            files.append({
                "name": f.get("name", ""),
                "id": f.get("id", ""),
                "mime_type": mime,
                "url": url,
                "size_bytes": int(f["size"]) if f.get("size") else 0,
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return files


def list_local_folder(folder_path: str) -> list[dict]:
    """
    Liệt kê các file CSV/Excel trong một folder local.
    Returns: list of {name, id, mime_type, url, size_bytes}
    """
    p = Path(folder_path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Không tìm thấy folder: {folder_path}")
    if not p.is_dir():
        raise ValueError(f"Đây không phải folder: {folder_path}")

    files = []
    for f in sorted(p.iterdir()):
        if f.is_file():
            files.append({
                "name": f.name,
                "id": None,
                "mime_type": "",
                "url": str(f),
                "size_bytes": f.stat().st_size,
            })
    return files


def load_seo_source(source: str, data_type: str) -> pd.DataFrame:
    """
    Entry point duy nhất — tự nhận dạng loại nguồn và trả về DataFrame.

    source: Google Sheets URL | file path | text (chỉ cho TEXT_DATA_TYPES)
    data_type: một trong 13 giá trị hợp lệ
    """
    if data_type not in VALID_DATA_TYPES:
        raise ValueError(
            f"data_type không hợp lệ: '{data_type}'. "
            f"Hợp lệ: {sorted(VALID_DATA_TYPES)}"
        )

    source = source.strip()

    if SHEETS_URL_RE.match(source):
        return load_sheet_as_dataframe(source)

    path = Path(source).expanduser()
    if path.exists():
        ext_lower = path.suffix.lower()
        if ext_lower in IMAGE_EXTENSIONS:
            if data_type != "img_overview":
                raise ValueError(
                    f"File ảnh chỉ được load với data_type='img_overview', không phải '{data_type}'."
                )
            return pd.DataFrame({
                "file_path": [str(path)],
                "file_name": [path.name],
                "status": ["pending_extraction"],
            })
        if ext_lower in TEXT_FILE_EXTENSIONS:
            text = path.read_text(encoding="utf-8", errors="replace")
            if ext_lower in {".html", ".htm"}:
                # Thử parse bảng HTML trước
                try:
                    dfs = pd.read_html(text)
                    if dfs:
                        df = dfs[0].dropna(how="all")
                        df.columns = [str(c).strip().lower() for c in df.columns]
                        return df.reset_index(drop=True)
                except Exception:
                    pass
                # Fallback: bóc thẻ HTML → text
                text = re.sub(r"<[^>]+>", "", text)
            return load_text_source(text, data_type)
        return load_local_file(str(path))

    if data_type in TEXT_DATA_TYPES:
        return load_text_source(source, data_type)

    raise FileNotFoundError(
        f"Không tìm thấy: '{source}'. "
        f"Cung cấp Google Sheets URL hoặc đường dẫn file CSV/Excel."
    )
