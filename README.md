# SEO Overview — Claude MCP Plugin

Tự động tạo báo cáo SEO tổng quan từ dữ liệu Google Drive. Plugin MCP cho Claude Desktop App.

## Tính năng

- Quét Google Drive folder hoặc local folder, tự động nhận dạng 13 loại dữ liệu SEO
- Phân tích và tạo báo cáo với 8 sections: Search Behavior, Ranking Analysis, Organic Traffic, SEO Audit, Traffic by URL Groups, ChatGPT Brand Mentions, ChatGPT Citation Domains, Website Overview
- Xuất báo cáo dạng **DOCX**, **HTML** (interactive charts), **PPTX**, **PNG**
- Upload kết quả lên Google Drive

## Cài đặt nhanh

```bash
bash <(curl -fsSL https://github.com/minhdo01011990-glitch/seo-overview/releases/latest/download/install.sh)
```

Hoặc cài từ PyPI:

```bash
pip install seo-overview
seo-overview-install
```

Sau đó tắt và mở lại Claude Desktop — biểu tượng 🔧 xuất hiện là MCP hoạt động.

## Cài thủ công (dev)

```bash
git clone https://github.com/minhdo01011990-glitch/seo-overview
cd seo-overview
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
seo-overview-install
```

## Cấu hình Google Service Account

Plugin cần Service Account để đọc Google Sheets và Google Drive.

1. Tạo Service Account tại [Google Cloud Console](https://console.cloud.google.com/)
2. Bật APIs: **Google Sheets API** và **Google Drive API**
3. Tạo JSON key và set biến môi trường:

```bash
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
```

Hoặc trỏ đến file:

```bash
export GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

Sau đó chạy lại `seo-overview-install` để cập nhật config.

## Sử dụng

Trong Claude Desktop, gõ slash command:

```
/seo-overview:SEO-Overview
```

Plugin sẽ hướng dẫn từng bước:
1. Nhập domain cần phân tích
2. Cung cấp dữ liệu (quét folder hoặc từng file riêng)
3. Review outline báo cáo
4. Chọn format xuất (DOCX/HTML/PPTX/PNG)

## 13 loại dữ liệu hỗ trợ

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

## Yêu cầu

- Python 3.9+
- Claude Desktop App
- Google Service Account (để đọc Google Sheets/Drive)

## License

MIT
