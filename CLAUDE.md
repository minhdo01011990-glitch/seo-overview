# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## After Context Compact

Đọc `summary.md` trước tiên để khôi phục trạng thái dự án (hiện trạng, file đã tạo, quyết định kỹ thuật). Nếu cần thêm chi tiết về một phần cụ thể, hỏi user để xin đọc đúng file đó — không tự đọc hàng loạt file.

## After Each Task

Sau khi hoàn thành bất kỳ bước chỉnh sửa nào và đã trình bày kết quả cho user, cập nhật `summary.md`:
- Đánh dấu file vừa tạo/sửa là `✅` trong cấu trúc thư mục
- Thêm dòng mới vào bảng **Lịch sử chỉnh sửa**
- Cập nhật **Hiện trạng dự án** nếu giai đoạn thay đổi
- Cập nhật **Quyết định kỹ thuật** nếu có quyết định mới

## Working Rules

- **Suy nghĩ trước khi code**: Đọc và hiểu rõ yêu cầu, trace luồng dữ liệu liên quan trước khi viết bất kỳ dòng code nào. Không đoán mò.
- **Đơn giản trước**: Chọn giải pháp ít code nhất có thể giải quyết được vấn đề. Không thêm abstraction, wrapper, hay tính năng chưa được yêu cầu.
- **Chỉ sửa chỗ cần sửa**: Không refactor, format, hay đụng vào code không liên quan đến task hiện tại.
- **Test trước, loop đến khi pass**: Viết test trước khi viết implementation. Sau đó tự chạy test, sửa, chạy lại — lặp đến khi tất cả test pass mà không cần hỏi.

## Project Overview

MCP plugin for Claude Desktop App that automates SEO reporting. Users invoke `/seo-overview:SEO-Overview`, provide Google Drive links as data sources, and receive a structured SEO analysis report in DOCX, HTML, PPTX, or PNG format.

Template/reference project: `/Users/maytinh/URL-chia-nhom/` (url-labeler plugin — identical stack).

## Development Commands

```bash
# Create virtualenv and install in editable mode
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run the MCP server locally (for testing)
seo-overview-server

# Register plugin into Claude Desktop App config
seo-overview-install

# Run tests
pytest tests/

# Run a single test
pytest tests/test_data_processor.py::test_keyword_analysis -v
```

## Architecture

### Plugin System (Claude Desktop)

Claude Desktop reads `~/Library/Application Support/Claude/claude_desktop_config.json`. The `seo-overview-install` script adds an entry under `mcpServers`. On restart, Claude loads the MCP server and exposes the slash command.

- **Slash command**: defined in `skills/SEO-Overview/SKILL.md` (frontmatter `agent:` field points to the orchestrator agent)
- **Orchestrator**: `agents/seo-analyst/AGENT.MD` — contains the multi-step conversation prompt that drives the entire workflow
- **Plugin metadata**: `.claude-plugin/plugin.json` lists skills, agents, and `.mcp.json`

### MCP Server (`src/server.py`)

Uses `FastMCP` (same pattern as url-labeler). Exposes 5 tools:

1. `create_seo_session()` — initializes a UUID-keyed session in `session_store.py`
2. `load_seo_input(session_id, data_type, source)` — reads one data source from Google Drive or local file
3. `get_session_summary(session_id)` — returns which of the 13 data types are loaded, with row counts
4. `generate_analysis_outline(session_id)` — determines which of the 8 report sections can be generated
5. `generate_seo_report(session_id, formats, output_dir, upload_drive_url?)` — generates final reports

### Data Flow

```
User Drive URL → drive_reader.py (gspread + Google Drive API)
    → data_processor.py (pandas: clean, aggregate, compute stats per section)
    → report_generator.py (DOCX/HTML/PPTX/PNG output)
```

### 13 Input Data Types (`data_type` values)

`my_domain`, `competitor_domains`, `keywords`, `aio_domains`, `rankings`, `url_traffic`, `monthly_traffic`, `referral_domains`, `seo_audit`, `chatgpt_prompts`, `chatgpt_mentions`, `chatgpt_citations`, `analysis_comments`

### 8 Report Sections

| # | Section | Required data_type |
|---|---------|-------------------|
| 1 | Website Overview | my_domain |
| 2 | Search Behavior | keywords, aio_domains |
| 3 | Ranking Analysis | rankings |
| 4 | Organic Traffic | monthly_traffic |
| 5 | SEO Audit | seo_audit |
| 6 | Traffic by URL Groups | url_traffic |
| 7 | ChatGPT Brand Mentions | chatgpt_mentions |
| 8 | ChatGPT Citation Domains | chatgpt_citations |

Sections with missing data are skipped and noted in the report.

### Google Drive Auth

`drive_reader.py` uses `gspread` with a Google Service Account. Credentials are passed via the `GOOGLE_SERVICE_ACCOUNT_JSON` env var (JSON string or file path), configured in `.mcp.json`. Mirrors the url-labeler pattern exactly.

### Report Generation (`report_generator.py`)

- **DOCX**: `python-docx` + `matplotlib` charts embedded as BytesIO
- **HTML**: `Jinja2` rendering `templates/report.html.j2` with inline Chart.js
- **PPTX**: `python-pptx` — one slide per section, charts as embedded PNG
- **PNG**: `matplotlib` subplot grid — one PNG file per section

Output defaults to `~/Documents/SEO Reports/`. Optionally uploads to a Google Drive folder URL if `upload_drive_url` is provided.

## Key Dependencies

```toml
fastmcp>=0.9        # MCP server framework
gspread>=6.0        # Google Sheets access
google-auth>=2.0    # Service account auth
pandas>=2.0         # Data processing
matplotlib>=3.7     # Charts for all output formats
python-docx>=1.1    # DOCX generation
python-pptx>=0.6    # PPTX generation
jinja2>=3.1         # HTML templating
openpyxl>=3.1       # Excel file reading
```

## Installation for End Users

```bash
# One-step install
bash install.sh

# Manual: add to ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "seo-overview": {
      "command": "/path/to/.venv/bin/seo-overview-server",
      "env": { "GOOGLE_SERVICE_ACCOUNT_JSON": "..." }
    }
  }
}
```
