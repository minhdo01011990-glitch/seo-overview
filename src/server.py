"""MCP server entry point — wire 5 tools vào FastMCP."""

from __future__ import annotations

from typing import Optional

from fastmcp import FastMCP

from src.tools.analysis_tools import generate_analysis_outline as _generate_analysis_outline
from src.tools.input_tools import (
    create_seo_session as _create_seo_session,
    get_session_summary as _get_session_summary,
    load_seo_input as _load_seo_input,
    scan_seo_folder as _scan_seo_folder,
)
from src.tools.report_tools import generate_seo_report as _generate_seo_report

_INSTRUCTIONS = """
Bạn là chuyên gia phân tích SEO, tự động tạo báo cáo SEO tổng quan từ dữ liệu Google Drive.

## Workflow tổng quát

1. Gọi `create_seo_session()` để khởi tạo session.
2. Gọi `load_seo_input(session_id, data_type, source)` cho từng loại dữ liệu.
   - `source`: Google Sheets URL, đường dẫn file CSV/Excel, hoặc text ngắn.
   - `data_type`: một trong 13 loại dưới đây.
3. Gọi `get_session_summary(session_id)` để xem trạng thái: data nào đã load, section nào sẵn sàng.
   Trả về: `available` (data đã load + rows), `missing` (chưa load), `available_sections`, `missing_sections`.
4. Gọi `generate_analysis_outline(session_id)` để xem key insights và outline báo cáo.
   Gọi sau `get_session_summary` và trước `generate_seo_report`.
5. Gọi `generate_seo_report(session_id, formats, output_dir, upload_drive_url)` để xuất báo cáo.
   - `output_dir` mặc định là `~/Documents/SEO Reports` — không cần truyền trừ khi user muốn thay đổi.
   - Hỏi user: "Bạn có muốn upload báo cáo lên Google Drive không? Nếu có, cung cấp Google Drive folder URL."
   - Nếu user cung cấp URL → truyền vào `upload_drive_url`.

## 13 data_type hợp lệ

| data_type | Mô tả | Tên cột bắt buộc (chấp nhận alias) |
|---|---|---|
| `my_domain` | Domain cần phân tích | text: "example.com" |
| `competitor_domains` | Danh sách competitor | text: mỗi domain 1 dòng |
| `keywords` | Google Sheets | keyword (hoặc keywords), volume (hoặc search_volume), intent |
| `aio_domains` | Google Sheets | domain, aio_rate (hoặc rate) |
| `rankings` | Google Sheets | keyword, position (hoặc rank, pos), domain |
| `url_traffic` | Google Sheets | url (hoặc page, path), sessions (hoặc traffic, visits), label (hoặc group) |
| `monthly_traffic` | Google Sheets | month (hoặc date, period), sessions (hoặc traffic, visits), organic (hoặc organic_sessions) |
| `referral_domains` | Google Sheets | domain, spam_score, links |
| `seo_audit` | Google Sheets | issue (hoặc problem, title), category (hoặc type), severity (hoặc priority) |
| `chatgpt_prompts` | Text | text: mỗi dòng 1 prompt |
| `chatgpt_mentions` | Google Sheets | brand (hoặc domain), mention_rate (hoặc rate, percentage), prompt |
| `chatgpt_citations` | Google Sheets | citation_url (hoặc url, domain), count (hoặc citations, frequency) |
| `analysis_comments` | Text tự do | text tự do (nhận xét analyst) |

**Lưu ý:** Tên cột phải khớp chính xác (case-sensitive). Nếu xuất từ GA4/GSC, đổi tên cột về dạng lowercase trước khi load.

## 8 report sections và data cần thiết

| Section | data_type bắt buộc |
|---|---|
| Website Overview | my_domain |
| Search Behavior | keywords + aio_domains |
| Ranking Analysis | rankings |
| Organic Traffic | monthly_traffic |
| SEO Audit | seo_audit |
| Traffic by URL Groups | url_traffic |
| ChatGPT Brand Mentions | chatgpt_mentions |
| ChatGPT Citation Domains | chatgpt_citations |

Section nào thiếu dữ liệu sẽ bị skip và ghi chú trong báo cáo.

## Output formats

`formats`: list subset của `["docx", "html", "pptx", "png"]`

## Xử lý lỗi

- Google Sheets lỗi 403: nhắc user chia sẻ sheet ở chế độ "Anyone with the link can view"
- Sheet rỗng: thông báo, hỏi link khác
- Session không tồn tại: gọi lại `create_seo_session()`
""".strip()

mcp = FastMCP("seo-overview", instructions=_INSTRUCTIONS)


@mcp.tool()
def create_seo_session() -> dict:
    """
    Khởi tạo session SEO mới. Gọi đầu tiên trước khi load bất kỳ dữ liệu nào.
    Trả về session_id và created_at.
    """
    return _create_seo_session()


@mcp.tool()
def load_seo_input(
    session_id: str,
    data_type: str,
    source: str,
    domain: Optional[str] = None,
) -> dict:
    """
    Đọc một loại dữ liệu SEO từ Google Sheets, file CSV/Excel, hoặc text và lưu vào session.
    session_id: từ create_seo_session.
    data_type: một trong 13 giá trị hợp lệ (xem instructions).
    source: Google Sheets URL | đường dẫn file | text ngắn.
    domain: tên domain đầy đủ nếu file thuộc về 1 domain cụ thể (per-domain files).
      Khi domain được cung cấp, cột 'domain' sẽ được thêm vào data và tự động ghép
      (append) với data cùng type đã load trước đó.
    Trả về status, rows, columns, preview 3 hàng đầu.
    """
    return _load_seo_input(session_id, data_type, source, domain)


@mcp.tool()
def scan_seo_folder(session_id: str, folder_url: str) -> dict:
    """
    Quét một folder (Google Drive hoặc đường dẫn local) để phát hiện và phân loại data files SEO.
    Với mỗi file, tự động đoán data_type từ tên file và gán status:
      ok=nhận dạng được và duy nhất, duplicate=nhiều files cùng type, unknown=không nhận dạng,
      unsupported=định dạng không hỗ trợ.
    Gọi tool này trước để xem xét, sau đó user xác nhận files nào cần bỏ qua, rồi mới load.
    folder_url: Google Drive folder URL hoặc đường dẫn local folder.
    Trả về: total_files, files (index/name/url/detected_type/status/reason), issues, has_issues.
    """
    return _scan_seo_folder(session_id, folder_url)


@mcp.tool()
def get_session_summary(session_id: str) -> dict:
    """
    Xem trạng thái session: data types đã load và sections nào sẵn sàng để báo cáo.
    Trả về: available (data types đã load + row counts), missing (data types chưa load),
    available_sections (section IDs có thể tạo), missing_sections (sections thiếu data).
    """
    return _get_session_summary(session_id)


@mcp.tool()
def generate_analysis_outline(session_id: str) -> dict:
    """
    Phân tích dữ liệu đã load và trả về outline báo cáo với key insights của từng section.
    Gọi sau get_session_summary và trước generate_seo_report để review insights trước khi xuất file.
    Không gọi external API — chỉ đọc session state và xử lý pandas.
    Trả về available_sections (với key_insights), skipped_sections, và recommendation.
    """
    return _generate_analysis_outline(session_id)


@mcp.tool()
def generate_seo_report(
    session_id: str,
    formats: list[str],
    output_dir: str = "~/Documents/SEO Reports",
    upload_drive_url: Optional[str] = None,
) -> dict:
    """
    Tạo báo cáo SEO ở các định dạng được chọn và lưu ra file.
    formats: list subset của ["docx", "html", "pptx", "png"].
    output_dir: thư mục lưu file (mặc định ~/Documents/SEO Reports).
    upload_drive_url: Google Drive folder URL để upload (tuỳ chọn — hỏi user trước khi truyền).
    Trả về status, files (path + size_kb), drive_urls, skipped_sections, errors.
    """
    return _generate_seo_report(session_id, formats, output_dir, upload_drive_url)


def run():
    mcp.run()


if __name__ == "__main__":
    run()
