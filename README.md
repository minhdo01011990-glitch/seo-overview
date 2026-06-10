# SEO Overview MCP Plugin

Tự động tạo báo cáo SEO tổng quan từ dữ liệu Google Drive.  
Chạy trên **Claude Desktop App** — hỗ trợ lệnh `/seo-overview:SEO-Overview` trong Cowork.  
Xuất báo cáo dạng **DOCX · HTML · PPTX · PNG**.

---

## Cài Đặt

### Bước 1 — Chạy 1 lệnh terminal

```bash
bash <(curl -sSL https://raw.githubusercontent.com/minhdo01011990-glitch/seo-overview/main/install.sh)
```

Script tự động:
1. Phát hiện Python 3.11+ và cài `seo-overview` từ PyPI
2. Cấu hình MCP server vào `claude_desktop_config.json` (Claude Desktop)
3. Cấu hình MCP server vào `~/.claude/settings.json` (Claude Code CLI)
4. Cài plugin files vào `~/.local/share/seo-overview/plugin/`
5. Thêm shell function vào `~/.zshrc` / `~/.bashrc` để tự load `--plugin-dir`
6. Restart Claude Desktop (macOS)

### Bước 2 — Upload plugin vào Cowork (1 lần duy nhất)

1. Tải file [`seo-overview.plugin`](https://github.com/minhdo01011990-glitch/seo-overview/releases/latest) từ trang Releases
2. Mở Claude Desktop → **Cowork → Settings → Plugins → Upload** → chọn file vừa tải

Sau bước này, gõ `/seo-overview:SEO-Overview` trong Cowork là dùng được.

---

## Yêu Cầu

- Python **3.11+** ([tải tại đây](https://python.org/downloads/)) hoặc [`uv`](https://docs.astral.sh/uv/)
- Claude Desktop App (Mac hoặc Windows)
- Google Service Account JSON — để đọc Google Sheets / Drive ([hướng dẫn](https://cloud.google.com/iam/docs/service-accounts-create))

---

## Cấu Hình Google Service Account

Plugin cần Service Account để đọc Google Sheets và Google Drive folder.

1. Tạo Service Account tại [Google Cloud Console](https://console.cloud.google.com/)
2. Bật: **Google Sheets API** + **Google Drive API**
3. Tạo JSON key → thêm vào config:

Trong `claude_desktop_config.json` (Claude Desktop):
```json
{
  "mcpServers": {
    "seo-overview": {
      "command": "seo-overview-server",
      "env": {
        "GOOGLE_SERVICE_ACCOUNT_JSON": "{\"type\":\"service_account\",...}"
      }
    }
  }
}
```

Hoặc set biến môi trường trước khi chạy `seo-overview-install`:
```bash
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
seo-overview-install
```

---

## Sử Dụng

Trong Claude Desktop → Cowork, gõ:

```
/seo-overview:SEO-Overview
```

Claude hướng dẫn từng bước:
1. Nhập domain cần phân tích
2. Cung cấp dữ liệu — quét Google Drive folder tự động hoặc nhập từng file riêng
3. Xác nhận danh sách file (bỏ trùng lặp / file không nhận dạng)
4. Review outline báo cáo
5. Chọn định dạng xuất (DOCX / HTML / PPTX / PNG)

---

## Cập Nhật Lên Phiên Bản Mới

### Bước 1 — Cập nhật MCP server

```bash
bash <(curl -sSL https://raw.githubusercontent.com/minhdo01011990-glitch/seo-overview/main/install.sh)
```

### Bước 2 — Cập nhật plugin Cowork

*(Chỉ cần khi SKILL.md hoặc AGENT.md thay đổi — xem Release Notes)*

1. Tải `seo-overview.plugin` mới từ [Releases](https://github.com/minhdo01011990-glitch/seo-overview/releases/latest)
2. Cowork → Settings → Plugins → **xóa plugin cũ** → **Upload** file mới

---

## 13 Loại Dữ Liệu Hỗ Trợ

| data_type | Mô tả |
|---|---|
| `keywords` | Từ khóa + search volume + intent |
| `rankings` | Thứ hạng từ khóa theo domain |
| `monthly_traffic` | Lưu lượng organic theo tháng |
| `url_traffic` | Traffic phân theo URL groups |
| `seo_audit` | Lỗi kỹ thuật SEO |
| `chatgpt_mentions` | Brand mentions trong ChatGPT |
| `chatgpt_citations` | Domain citations trong ChatGPT |
| `aio_domains` | AI Overview presence by domain |
| `referral_domains` | Referring domains |
| `competitor_domains` | Danh sách competitor |
| `chatgpt_prompts` | Prompt list để test ChatGPT |
| `analysis_comments` | Nhận xét của analyst |
| `my_domain` | Domain cần phân tích |

---

## MCP Tools

| Tool | Mô tả |
|------|-------|
| `create_seo_session` | Khởi tạo session mới |
| `scan_seo_folder` | Quét folder, tự nhận dạng data type từng file |
| `load_seo_input` | Load một data type từ Sheets / file / text |
| `get_session_summary` | Xem trạng thái session + sections sẵn sàng |
| `generate_analysis_outline` | Preview key insights trước khi xuất |
| `generate_seo_report` | Xuất báo cáo DOCX / HTML / PPTX / PNG |

---

## License

MIT
