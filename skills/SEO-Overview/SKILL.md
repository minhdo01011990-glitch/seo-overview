---
description: Tạo báo cáo SEO tổng quan từ dữ liệu Google Drive. Phân tích từ khóa, ranking, traffic, audit và ChatGPT mentions — xuất DOCX, HTML, PPTX hoặc PNG.
agent: seo-analyst
---

Kích hoạt `seo-analyst` agent để bắt đầu quy trình tạo báo cáo SEO tổng quan.

**Cách dùng:** Gọi lệnh không cần argument — agent sẽ hỏi từng bước.
```
/seo-overview:SEO-Overview
```

Agent sẽ:
1. Tạo session làm việc, sau đó hỏi domain cần phân tích và nguồn dữ liệu
2. Load từng loại dữ liệu: từ khóa, ranking, traffic, audit, ChatGPT mentions...
3. Hiển thị trạng thái session — data nào đã load, section nào sẵn sàng
4. Trình bày outline và key insights của từng section để review trước khi xuất
5. Hỏi định dạng xuất (DOCX, HTML, PPTX, PNG) và thư mục lưu
6. Tạo báo cáo — tuỳ chọn upload lên Google Drive

**Dữ liệu đầu vào cần chuẩn bị:**

| data_type | Section báo cáo | Nguồn |
|---|---|---|
| `my_domain` | Website Overview | Text: "example.com" |
| `keywords`, `aio_domains` | Search Behavior | Google Sheets |
| `rankings` | Ranking Analysis | Google Sheets |
| `monthly_traffic` | Organic Traffic | Google Sheets |
| `seo_audit` | SEO Audit | Google Sheets |
| `url_traffic` | Traffic by URL Groups | Google Sheets |
| `chatgpt_mentions` | ChatGPT Brand Mentions | Google Sheets |
| `chatgpt_citations` | ChatGPT Citation Domains | Google Sheets |
| `competitor_domains` | *(bổ sung Website Overview)* | Text: mỗi domain 1 dòng |
| `referral_domains` | *(load được, không có section riêng)* | Google Sheets |
| `chatgpt_prompts`, `analysis_comments` | *(context bổ sung)* | Text tự do |

Google Sheets phải được chia sẻ ở chế độ "Anyone with the link can view".
