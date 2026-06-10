"""Xử lý dữ liệu SEO và tạo context cho các section báo cáo."""

from __future__ import annotations

import base64
import io
import unicodedata
from datetime import datetime, timezone
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.core.session_store import list_loaded_types, load_data_type


SECTION_REQUIREMENTS: dict[str, list[str]] = {
    "website_overview":   ["my_domain"],
    "search_behavior":    ["keywords", "aio_domains"],
    "ranking_analysis":   ["rankings"],
    "organic_traffic":    ["monthly_traffic"],
    "seo_audit":          ["seo_audit"],
    "url_traffic_groups": ["url_traffic"],
    "chatgpt_mentions":   ["chatgpt_mentions"],
    "chatgpt_citations":  ["chatgpt_citations"],
}

SECTION_TITLES: dict[str, str] = {
    "website_overview":   "Tổng quan Website",
    "search_behavior":    "Hành vi Tìm kiếm",
    "ranking_analysis":   "Phân tích Thứ hạng",
    "organic_traffic":    "Traffic Organic",
    "seo_audit":          "Kiểm tra SEO",
    "url_traffic_groups": "Traffic theo Nhóm URL",
    "chatgpt_mentions":   "Đề cập trên ChatGPT",
    "chatgpt_citations":  "Citation Domains ChatGPT",
}

SECTION_ORDER = list(SECTION_REQUIREMENTS.keys())


def get_available_sections(loaded_types: list[str]) -> list[str]:
    """Trả về danh sách section_id có thể tạo từ loaded_types hiện tại."""
    loaded = set(loaded_types)
    return [s for s in SECTION_ORDER if all(r in loaded for r in SECTION_REQUIREMENTS[s])]


# ── Internal helpers ─────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _to_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def _normalize_str(s: pd.Series) -> pd.Series:
    """Strip + lowercase + NFKC normalize (xử lý \xa0 và ký tự đặc biệt từ Google Sheets)."""
    return s.astype(str).apply(lambda x: unicodedata.normalize("NFKC", x)).str.strip().str.lower()


def _html_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    subset = df.head(max_rows)
    ths = "".join(f"<th>{c}</th>" for c in subset.columns)
    trs = "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>"
        for _, row in subset.iterrows()
    )
    return f"<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>"


def _kpi_html(kpis: list[dict]) -> str:
    cards = "".join(
        f'<div class="kpi-card">'
        f'<span class="kpi-value">{kpi["value"]}</span>'
        f'<span class="kpi-label">{kpi["label"]}</span>'
        f'</div>'
        for kpi in kpis
    )
    return f'<div class="kpi-grid">{cards}</div>'


def _badge_html(text: str, level: str) -> str:
    level = level.lower().strip()
    css = {"critical": "badge-critical", "high": "badge-high",
           "medium": "badge-medium", "low": "badge-low"}.get(level, "badge-low")
    return f'<span class="badge {css}">{text}</span>'


def _fig_to_b64(fig) -> str:
    # Fix #11: try/finally đảm bảo buf và fig luôn được close dù savefig có lỗi
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    finally:
        buf.close()
        plt.close(fig)


# ── Section processors ───────────────────────────────────────────────────────

def process_website_overview(
    my_domain_df: pd.DataFrame,
    competitor_domains_df: Optional[pd.DataFrame] = None,
) -> dict:
    if my_domain_df.empty:
        raise ValueError("Không có dữ liệu my_domain")

    val_col = _find_col(my_domain_df, "value", "domain") or my_domain_df.columns[0]
    # Fix #14: hỗ trợ key-value format (nhiều row, mỗi row là 1 metric như DA, DR, industry...)
    key_col = _find_col(my_domain_df, "key", "metric", "chỉ số", "label")

    kpis: list[dict] = []
    if key_col and len(my_domain_df) > 1:
        domain = str(my_domain_df[val_col].iloc[0]).strip()
        for _, row in my_domain_df.iterrows():
            kpis.append({
                "value": str(row[val_col]).strip(),
                "label": str(row[key_col]).strip(),
            })
    else:
        domain = str(my_domain_df[val_col].iloc[0]).strip()
        kpis.append({"value": domain, "label": "Domain chính"})
        # Các cột metadata phụ (DA, DR, industry...) nếu có
        extra_cols = [c for c in my_domain_df.columns if c not in {val_col} and not c.startswith("_")]
        if extra_cols and len(my_domain_df) == 1:
            for col in extra_cols:
                kpis.append({
                    "value": str(my_domain_df[col].iloc[0]).strip(),
                    "label": col.replace("_", " ").title(),
                })

    parts: list[str] = []
    if competitor_domains_df is not None and not competitor_domains_df.empty:
        kpis.append({"value": len(competitor_domains_df), "label": "Đối thủ cạnh tranh"})

    parts.append(_kpi_html(kpis))

    if competitor_domains_df is not None and not competitor_domains_df.empty:
        comp_col = _find_col(competitor_domains_df, "value", "domain") or competitor_domains_df.columns[0]
        comp_df = competitor_domains_df[[comp_col]].rename(columns={comp_col: "Domain đối thủ"}).copy()
        comp_df.insert(0, "#", range(1, len(comp_df) + 1))
        parts.append("<h3>Danh sách đối thủ cạnh tranh</h3>")
        parts.append(_html_table(comp_df))

    return {
        "id": "website_overview",
        "title": SECTION_TITLES["website_overview"],
        "content_html": "\n".join(parts),
        "charts": [],
        "key_insights": [f"Domain chính: {domain}"],
    }


def process_search_behavior(
    keywords_df: pd.DataFrame,
    aio_domains_df: pd.DataFrame,
) -> dict:
    if keywords_df.empty:
        raise ValueError("Không có dữ liệu keywords")

    kw_col = _find_col(keywords_df, "keyword", "keywords", "từ khóa") or keywords_df.columns[0]
    vol_col = _find_col(keywords_df, "volume", "search volume", "search_volume", "lượt tìm kiếm")
    intent_col = _find_col(keywords_df, "intent", "search intent", "search_intent", "mục đích")

    parts: list[str] = []
    charts: list[dict] = []
    insights: list[str] = []
    total_kw = len(keywords_df)
    kpis = [{"value": f"{total_kw:,}", "label": "Tổng số từ khóa"}]

    df = keywords_df.copy()
    if vol_col:
        df["_vol"] = _to_numeric(df[vol_col])
        total_vol = int(df["_vol"].sum())
        kpis.append({"value": f"{total_vol:,}", "label": "Tổng search volume"})
        insights.append(f"Tổng search volume: {total_vol:,}")

    parts.append(_kpi_html(kpis))
    insights.append(f"Tổng {total_kw:,} từ khóa")

    if vol_col:
        # Fix #4: sort bằng _vol numeric, không re-parse string
        top10_df = df.nlargest(10, "_vol")
        top10_display = top10_df[[kw_col, vol_col]].rename(
            columns={kw_col: "Từ khóa", vol_col: "Search Volume"}
        )
        parts.append("<h3>Top 10 từ khóa theo Search Volume</h3>")
        parts.append(_html_table(top10_display))

        fig, ax = plt.subplots(figsize=(9, 4))
        sorted_top = top10_df.sort_values("_vol")
        ax.barh(sorted_top[kw_col].astype(str), sorted_top["_vol"], color="#4361ee")
        ax.set_xlabel("Search Volume")
        ax.set_title("Top 10 từ khóa theo Search Volume")
        charts.append({"image_b64": _fig_to_b64(fig), "title": "Top 10 từ khóa theo Volume"})

    if intent_col:
        intent_counts = df[intent_col].value_counts()
        intent_table = intent_counts.reset_index()
        intent_table.columns = ["Intent", "Số lượng"]
        parts.append("<h3>Phân bố Search Intent</h3>")
        parts.append(_html_table(intent_table))
        insights.append(f"Intent chính: {intent_counts.index[0]} ({intent_counts.iloc[0]:,})")

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(intent_counts.index.astype(str), intent_counts.values, color="#4361ee")
        ax.set_ylabel("Số lượng từ khóa")
        ax.set_title("Phân bố Search Intent")
        plt.xticks(rotation=20, ha="right")
        charts.append({"image_b64": _fig_to_b64(fig), "title": "Phân bố Search Intent"})

    # Fix #13: guard aio_domains_df.empty trước khi access columns
    parts.append("<h3>Domains có AIO cao</h3>")
    if not aio_domains_df.empty:
        domain_col = _find_col(aio_domains_df, "domain", "tên miền") or aio_domains_df.columns[0]
        rate_col = _find_col(aio_domains_df, "aio_rate", "rate", "tỷ lệ", "aio rate")
        aio_df = aio_domains_df.copy()

        if rate_col:
            # Fix #4 (AIO): sort bằng _rate numeric, không re-parse string
            aio_df["_rate"] = _to_numeric(aio_df[rate_col])
            top_aio_df = aio_df.nlargest(10, "_rate")
            top_aio_display = top_aio_df[[domain_col, rate_col]].rename(
                columns={domain_col: "Domain", rate_col: "AIO Rate"}
            )
            parts.append(_html_table(top_aio_display))
            insights.append(f"AIO domain #1: {top_aio_df[domain_col].iloc[0]}")

            fig, ax = plt.subplots(figsize=(9, 4))
            sorted_aio = top_aio_df.sort_values("_rate")
            ax.barh(sorted_aio[domain_col].astype(str), sorted_aio["_rate"], color="#3a0ca3")
            ax.set_xlabel("AIO Rate")
            ax.set_title("Top 10 AIO Domains")
            charts.append({"image_b64": _fig_to_b64(fig), "title": "Top 10 AIO Domains"})
        else:
            parts.append(_html_table(aio_domains_df.head(10)))
    else:
        parts.append("<p><em>Không có dữ liệu AIO domains.</em></p>")
        insights.append("Chưa có dữ liệu AIO domains")

    return {
        "id": "search_behavior",
        "title": SECTION_TITLES["search_behavior"],
        "content_html": "\n".join(parts),
        "charts": charts,
        "key_insights": insights,
    }


def process_ranking_analysis(rankings_df: pd.DataFrame) -> dict:
    if rankings_df.empty:
        raise ValueError("Không có dữ liệu rankings")

    kw_col = _find_col(rankings_df, "keyword", "từ khóa") or rankings_df.columns[0]
    pos_col = _find_col(rankings_df, "position", "vị trí", "rank", "ranking", "pos")
    domain_col = _find_col(rankings_df, "domain", "website", "url")

    parts: list[str] = []
    charts: list[dict] = []
    top3_count = 0
    top10_count = 0

    df = rankings_df.copy()
    if pos_col:
        df["_pos"] = _to_numeric(df[pos_col])
        top3_count = int((df["_pos"] <= 3).sum())
        top10_count = int((df["_pos"] <= 10).sum())
        top20_count = int((df["_pos"] <= 20).sum())
        beyond_count = int((df["_pos"] > 20).sum())
        # Fix #12: thêm "quick win" (pos 4–10) — nhóm quan trọng nhất để push lên top 3
        quick_win = int(((df["_pos"] >= 4) & (df["_pos"] <= 10)).sum())

        kpis = [
            {"value": top3_count, "label": "Top 3"},
            {"value": quick_win, "label": "Quick Win (Pos 4–10)"},
            {"value": top10_count, "label": "Top 10"},
            {"value": top20_count, "label": "Top 20"},
            {"value": len(df), "label": "Tổng từ khóa"},
        ]
        parts.append(_kpi_html(kpis))

        fig, ax = plt.subplots(figsize=(7, 4))
        labels = ["Top 3", "Top 4–10", "Top 11–20", "Ngoài top 20"]
        values = [top3_count, top10_count - top3_count, top20_count - top10_count, beyond_count]
        colors = ["#2dc653", "#4361ee", "#ffd166", "#ef476f"]
        bars = ax.bar(labels, values, color=colors)
        ax.bar_label(bars, padding=3)
        ax.set_ylabel("Số từ khóa")
        ax.set_title("Phân bố thứ hạng từ khóa")
        charts.append({"image_b64": _fig_to_b64(fig), "title": "Phân bố thứ hạng"})

        parts.append("<h3>Từ khóa thứ hạng cao nhất</h3>")
        show_cols = [c for c in [kw_col, pos_col, domain_col] if c is not None]
        top_df = df.nsmallest(20, "_pos")[show_cols].copy()
        parts.append(_html_table(top_df))

        insights = [
            f"Top 3: {top3_count} từ khóa",
            f"Top 10: {top10_count} từ khóa",
            f"Quick win (pos 4–10): {quick_win} từ khóa",
        ]
    else:
        parts.append(_html_table(rankings_df.head(20)))
        insights = [f"Tổng {len(rankings_df):,} từ khóa có ranking"]

    return {
        "id": "ranking_analysis",
        "title": SECTION_TITLES["ranking_analysis"],
        "content_html": "\n".join(parts),
        "charts": charts,
        "key_insights": insights,
        "top3_count": top3_count,
        "top10_count": top10_count,
    }


_TREND_LABELS = {
    "critical_drop": "⚠ Giảm nghiêm trọng (>30%)",
    "warning_drop":  "↓↓ Cảnh báo giảm (>20%)",
    "down":          "↓ Giảm nhẹ (>10%)",
    "stable":        "→ Ổn định",
    "up":            "↑ Tăng trưởng",
}


def process_organic_traffic(monthly_traffic_df: pd.DataFrame) -> dict:
    if monthly_traffic_df.empty:
        raise ValueError("Không có dữ liệu monthly_traffic")

    month_col = _find_col(monthly_traffic_df, "month", "tháng", "date", "period") or monthly_traffic_df.columns[0]
    # Fix #2: không include "organic" trong sess_col candidates để tránh conflict với organic_col
    sess_col = _find_col(monthly_traffic_df, "sessions", "total_sessions", "traffic", "visits")
    organic_col = _find_col(monthly_traffic_df, "organic", "organic_sessions", "organic_traffic")

    # Fix #2: dùng primary_col riêng, không reassign sess_col
    primary_col = sess_col or organic_col

    df = monthly_traffic_df.copy()
    df["_month_str"] = df[month_col].astype(str).str.strip()

    if primary_col:
        df["_sessions"] = _to_numeric(df[primary_col])
    else:
        df["_sessions"] = _to_numeric(df.iloc[:, 1])

    df = df.sort_values("_month_str").reset_index(drop=True)

    # Fix #3: guard trước khi idxmax() để tránh crash khi tất cả NaN
    if df["_sessions"].isna().all():
        raise ValueError(
            "Không thể parse giá trị số từ cột sessions — "
            "kiểm tra lại format dữ liệu monthly_traffic"
        )

    months = df["_month_str"].tolist()
    session_vals = df["_sessions"].fillna(0).tolist()

    peak_idx = df["_sessions"].idxmax()
    peak_month = str(df.loc[peak_idx, "_month_str"])
    peak_sessions = int(df.loc[peak_idx, "_sessions"])

    # Fix #1: MoM % change từng tháng
    df["_mom_pct"] = df["_sessions"].pct_change() * 100

    # Fix #1: ngưỡng trend theo chuẩn SEO (>20% MoM / >30% là cảnh báo)
    n = len(df)
    if n >= 6:
        first3_avg = df["_sessions"].iloc[:3].mean()
        last3_avg = df["_sessions"].iloc[-3:].mean()
        if first3_avg > 0:
            change_pct = (last3_avg - first3_avg) / first3_avg * 100
            if change_pct <= -30:
                trend_direction = "critical_drop"
            elif change_pct <= -20:
                trend_direction = "warning_drop"
            elif change_pct <= -10:
                trend_direction = "down"
            elif change_pct >= 10:
                trend_direction = "up"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "stable"

    total_sessions = int(df["_sessions"].sum())
    kpis = [
        {"value": f"{total_sessions:,}", "label": "Tổng sessions"},
        {"value": peak_month, "label": "Tháng đỉnh"},
        {"value": f"{peak_sessions:,}", "label": "Sessions cao nhất"},
        {"value": _TREND_LABELS[trend_direction], "label": "Xu hướng"},
    ]
    parts = [_kpi_html(kpis)]

    # Table với cột MoM %
    show_cols = [c for c in [month_col, primary_col] if c is not None and c in df.columns]
    if organic_col and organic_col in df.columns and organic_col != primary_col:
        show_cols.append(organic_col)
    table_df = df[show_cols].copy()
    table_df["MoM %"] = df["_mom_pct"].map(
        lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
    )
    parts.append(_html_table(table_df))

    # Line chart
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(months, session_vals, marker="o", color="#4361ee", linewidth=2, label=primary_col or "Sessions")
    ax.fill_between(months, session_vals, alpha=0.1, color="#4361ee")
    ax.set_xlabel("Tháng")
    ax.set_ylabel("Sessions")
    ax.set_title("Traffic Organic theo tháng")
    plt.xticks(rotation=30, ha="right")

    # Fix #2: điều kiện đúng vì primary_col không còn bị reassign
    if organic_col and organic_col in df.columns and organic_col != primary_col:
        org_vals = _to_numeric(df[organic_col]).fillna(0).tolist()
        ax.plot(months, org_vals, marker="s", color="#f72585", linewidth=2, linestyle="--", label="Organic")
        ax.legend()

    charts = [{"image_b64": _fig_to_b64(fig), "title": "Traffic theo tháng"}]

    # Fix #1: thêm cảnh báo tháng drop > 20% MoM vào insights
    insights = [
        f"Đỉnh traffic: {peak_month} ({peak_sessions:,} sessions)",
        f"Xu hướng: {_TREND_LABELS[trend_direction]}",
    ]
    mom_drops = df[df["_mom_pct"] < -20][["_month_str", "_mom_pct"]].dropna()
    for _, row in mom_drops.iterrows():
        insights.append(f"Drop >20% MoM: {row['_month_str']} ({row['_mom_pct']:+.1f}%)")

    return {
        "id": "organic_traffic",
        "title": SECTION_TITLES["organic_traffic"],
        "content_html": "\n".join(parts),
        "charts": charts,
        "key_insights": insights,
        "months": months,
        "peak_month": peak_month,
        "trend_direction": trend_direction,
    }


def process_seo_audit(seo_audit_df: pd.DataFrame) -> dict:
    if seo_audit_df.empty:
        raise ValueError("Không có dữ liệu seo_audit")

    issue_col = _find_col(seo_audit_df, "issue", "vấn đề", "problem", "error", "title") or seo_audit_df.columns[0]
    cat_col = _find_col(seo_audit_df, "category", "danh mục", "type", "loại")
    sev_col = _find_col(seo_audit_df, "severity", "mức độ", "priority", "level")

    parts: list[str] = []
    charts: list[dict] = []
    df = seo_audit_df.copy()

    if sev_col:
        # Fix #5: NFKC normalize để xử lý \xa0 và ký tự đặc biệt từ Google Sheets
        df["_sev"] = _normalize_str(df[sev_col])

        sev_order = ["critical", "high", "medium", "low"]
        counts = {s: int((df["_sev"] == s).sum()) for s in sev_order}

        # Fix #6: phát hiện severity ngoài 4 mức chuẩn và cảnh báo consultant
        known = set(sev_order)
        unknown_sevs = sorted(set(df["_sev"].unique()) - known - {""})

        kpis = [
            {"value": counts["critical"], "label": "Critical"},
            {"value": counts["high"], "label": "High"},
            {"value": counts["medium"], "label": "Medium"},
            {"value": counts["low"], "label": "Low"},
        ]
        parts.append(_kpi_html(kpis))

        fig, ax = plt.subplots(figsize=(7, 3))
        colors = ["#c0392b", "#e67e22", "#c0a000", "#27ae60"]
        bars = ax.bar(["Critical", "High", "Medium", "Low"],
                      [counts[s] for s in sev_order], color=colors)
        ax.bar_label(bars, padding=3)
        ax.set_ylabel("Số vấn đề")
        ax.set_title("Vấn đề SEO theo mức độ nghiêm trọng")
        charts.append({"image_b64": _fig_to_b64(fig), "title": "Issues theo severity"})

        show_cols = [c for c in [issue_col, cat_col, sev_col] if c is not None]
        top_issues = df.copy()
        top_issues["_sev_rank"] = top_issues["_sev"].map(
            {"critical": 0, "high": 1, "medium": 2, "low": 3}
        ).fillna(4)
        top_issues = top_issues.sort_values("_sev_rank")[show_cols].head(30)
        parts.append("<h3>Danh sách vấn đề SEO (ưu tiên cao nhất)</h3>")
        parts.append(_html_table(top_issues))

        insights = [
            f"Critical: {counts['critical']} vấn đề",
            f"High: {counts['high']} vấn đề",
        ]
        if unknown_sevs:
            insights.append(f"Severity không chuẩn (bị bỏ qua): {', '.join(unknown_sevs)}")
    else:
        parts.append(_html_table(df.head(30)))
        insights = [f"Tổng {len(df):,} vấn đề SEO"]

    return {
        "id": "seo_audit",
        "title": SECTION_TITLES["seo_audit"],
        "content_html": "\n".join(parts),
        "charts": charts,
        "key_insights": insights,
    }


def process_url_traffic_groups(url_traffic_df: pd.DataFrame) -> dict:
    if url_traffic_df.empty:
        raise ValueError("Không có dữ liệu url_traffic")

    url_col = _find_col(url_traffic_df, "url", "page", "path") or url_traffic_df.columns[0]
    sess_col = _find_col(url_traffic_df, "sessions", "traffic", "visits", "pageviews")
    label_col = _find_col(url_traffic_df, "label", "group", "nhóm", "category", "type")

    parts: list[str] = []
    charts: list[dict] = []
    df = url_traffic_df.copy()

    if sess_col:
        df["_sess"] = _to_numeric(df[sess_col])

    if label_col and sess_col:
        group_agg = df.groupby(label_col)["_sess"].sum().sort_values(ascending=False)
        total_sess = int(df["_sess"].sum())
        kpis = [
            {"value": len(group_agg), "label": "Nhóm URL"},
            {"value": f"{total_sess:,}", "label": "Tổng sessions"},
        ]
        parts.append(_kpi_html(kpis))

        group_df = group_agg.reset_index()
        group_df.columns = ["Nhóm", "Sessions"]

        # Tính % chính xác — dùng largest-remainder để đảm bảo sum = 100.0%
        if total_sess > 0:
            raw_pct = group_df["Sessions"] / total_sess * 100
            floored = raw_pct.apply(lambda x: int(x * 10) / 10)  # floor to 1 decimal
            remainder = raw_pct - floored
            n_adjust = round((100.0 - floored.sum()) * 10)  # số tenths cần bù
            adjust_idx = remainder.nlargest(max(0, int(n_adjust))).index
            floored[adjust_idx] += 0.1
            group_df["Tỷ lệ %"] = floored.round(1)
        else:
            group_df["Tỷ lệ %"] = 0.0

        parts.append("<h3>Traffic theo nhóm URL</h3>")
        parts.append(_html_table(group_df))

        fig, ax = plt.subplots(figsize=(9, 4))
        sorted_g = group_df.sort_values("Sessions")
        ax.barh(sorted_g["Nhóm"].astype(str), sorted_g["Sessions"], color="#4361ee")
        ax.set_xlabel("Sessions")
        ax.set_title("Traffic theo nhóm URL")
        charts.append({"image_b64": _fig_to_b64(fig), "title": "Traffic theo nhóm URL"})

        insights = [f"Nhóm lớn nhất: {group_agg.index[0]} ({int(group_agg.iloc[0]):,} sessions)"]
    else:
        # Fix #9: dùng display_df đã sort thay vì df unsorted
        display_df = df.nlargest(20, "_sess") if sess_col else df.head(20)
        show_cols = [c for c in [url_col, sess_col, label_col] if c is not None]
        parts.append(_html_table(display_df[show_cols]))
        insights = [f"Tổng {len(df):,} URLs"]

    return {
        "id": "url_traffic_groups",
        "title": SECTION_TITLES["url_traffic_groups"],
        "content_html": "\n".join(parts),
        "charts": charts,
        "key_insights": insights,
    }


def process_chatgpt_mentions(
    chatgpt_mentions_df: pd.DataFrame,
    chatgpt_prompts_df: Optional[pd.DataFrame] = None,
) -> dict:
    if chatgpt_mentions_df.empty:
        raise ValueError("Không có dữ liệu chatgpt_mentions")

    brand_col = _find_col(chatgpt_mentions_df, "brand", "domain", "tên thương hiệu") or chatgpt_mentions_df.columns[0]
    rate_col = _find_col(chatgpt_mentions_df, "mention_rate", "rate", "tỷ lệ", "percentage", "percent")
    prompt_col = _find_col(chatgpt_mentions_df, "prompt", "câu hỏi", "query")

    parts: list[str] = []
    charts: list[dict] = []
    df = chatgpt_mentions_df.copy()

    kpis = [{"value": len(df), "label": "Brands theo dõi"}]
    if chatgpt_prompts_df is not None and not chatgpt_prompts_df.empty:
        kpis.append({"value": len(chatgpt_prompts_df), "label": "Prompts kiểm tra"})

    if rate_col:
        df["_rate"] = _to_numeric(df[rate_col])
        # Fix #8: chuẩn hóa về thang 0–100 từ đầu, dùng nhất quán cho cả KPI lẫn chart
        df["_rate_pct"] = df["_rate"].apply(
            lambda x: x * 100 if pd.notna(x) and x <= 1 else x
        )
        if not df["_rate_pct"].isna().all():
            max_rate_pct = df["_rate_pct"].max()
            kpis.append({"value": f"{max_rate_pct:.1f}%", "label": "Tỷ lệ cao nhất"})

    parts.append(_kpi_html(kpis))

    show_cols = [c for c in [brand_col, rate_col, prompt_col] if c is not None]
    df_sorted = df.sort_values("_rate_pct", ascending=False) if rate_col and "_rate_pct" in df.columns else df
    parts.append(_html_table(df_sorted[show_cols].head(20)))

    if rate_col and "_rate_pct" in df.columns and not df["_rate_pct"].isna().all():
        fig, ax = plt.subplots(figsize=(9, 4))
        top = df.nlargest(15, "_rate_pct")
        sorted_top = top.sort_values("_rate_pct")
        ax.barh(sorted_top[brand_col].astype(str), sorted_top["_rate_pct"], color="#f72585")
        ax.set_xlabel("Mention Rate (%)")
        ax.set_title("ChatGPT Brand Mention Rate")
        charts.append({"image_b64": _fig_to_b64(fig), "title": "ChatGPT Mention Rate"})

        # Fix #7: guard all-NaN trước idxmax()
        top_brand = str(df.loc[df["_rate_pct"].idxmax(), brand_col])
    else:
        top_brand = str(df[brand_col].iloc[0])

    insights = [f"Brand được đề cập nhiều nhất: {top_brand}"]

    return {
        "id": "chatgpt_mentions",
        "title": SECTION_TITLES["chatgpt_mentions"],
        "content_html": "\n".join(parts),
        "charts": charts,
        "key_insights": insights,
    }


def process_chatgpt_citations(chatgpt_citations_df: pd.DataFrame) -> dict:
    if chatgpt_citations_df.empty:
        raise ValueError("Không có dữ liệu chatgpt_citations")

    url_col = _find_col(chatgpt_citations_df, "citation_url", "url", "domain", "website") or chatgpt_citations_df.columns[0]
    count_col = _find_col(chatgpt_citations_df, "count", "citations", "số lần", "frequency")

    parts: list[str] = []
    charts: list[dict] = []
    df = chatgpt_citations_df.copy()

    if count_col:
        df["_count"] = _to_numeric(df[count_col])
        total = int(df["_count"].sum())
        kpis = [
            {"value": len(df), "label": "Citation domains"},
            {"value": f"{total:,}", "label": "Tổng citations"},
        ]
        parts.append(_kpi_html(kpis))

        top = df.nlargest(20, "_count")[[url_col, count_col]].rename(
            columns={url_col: "Citation URL/Domain", count_col: "Số lần"}
        )
        parts.append(_html_table(top))

        fig, ax = plt.subplots(figsize=(9, 5))
        top15 = df.nlargest(15, "_count")
        sorted_top = top15.sort_values("_count")
        ax.barh(sorted_top[url_col].astype(str), sorted_top["_count"], color="#4361ee")
        ax.set_xlabel("Số lần được trích dẫn")
        ax.set_title("Top 15 Citation Domains trên ChatGPT")
        charts.append({"image_b64": _fig_to_b64(fig), "title": "Top Citation Domains"})

        top_domain = str(top15.nlargest(1, "_count")[url_col].iloc[0])
        insights = [f"Domain được cite nhiều nhất: {top_domain} ({int(top15['_count'].max()):,} lần)"]
    else:
        parts.append(_html_table(df.head(20)))
        insights = [f"Tổng {len(df):,} citation domains"]

    return {
        "id": "chatgpt_citations",
        "title": SECTION_TITLES["chatgpt_citations"],
        "content_html": "\n".join(parts),
        "charts": charts,
        "key_insights": insights,
    }


# ── Orchestrator ─────────────────────────────────────────────────────────────

def build_report_context(session_id: str) -> dict:
    """Tải toàn bộ dữ liệu của session, gọi các processor, trả về context cho Jinja2."""
    loaded = list_loaded_types(session_id)
    loaded_keys = set(loaded.keys())
    available = get_available_sections(list(loaded_keys))

    _PROCESSORS = {
        "website_overview": lambda data: process_website_overview(
            data["my_domain"],
            data.get("competitor_domains"),
        ),
        "search_behavior": lambda data: process_search_behavior(
            data["keywords"],
            data["aio_domains"],
        ),
        "ranking_analysis": lambda data: process_ranking_analysis(data["rankings"]),
        "organic_traffic": lambda data: process_organic_traffic(data["monthly_traffic"]),
        "seo_audit": lambda data: process_seo_audit(data["seo_audit"]),
        "url_traffic_groups": lambda data: process_url_traffic_groups(data["url_traffic"]),
        "chatgpt_mentions": lambda data: process_chatgpt_mentions(
            data["chatgpt_mentions"],
            data.get("chatgpt_prompts"),
        ),
        "chatgpt_citations": lambda data: process_chatgpt_citations(data["chatgpt_citations"]),
    }

    sections = []
    for section_id in SECTION_ORDER:
        if section_id not in available:
            continue
        data = {dt: load_data_type(session_id, dt) for dt in SECTION_REQUIREMENTS[section_id]}
        if section_id == "website_overview" and "competitor_domains" in loaded_keys:
            data["competitor_domains"] = load_data_type(session_id, "competitor_domains")
        if section_id == "chatgpt_mentions" and "chatgpt_prompts" in loaded_keys:
            data["chatgpt_prompts"] = load_data_type(session_id, "chatgpt_prompts")
        sections.append(_PROCESSORS[section_id](data))

    missing_sections = []
    for s_id in SECTION_ORDER:
        if s_id in available:
            continue
        required = SECTION_REQUIREMENTS[s_id]
        missing_data = [r for r in required if r not in loaded_keys]
        missing_sections.append({
            "id": s_id,
            "title": SECTION_TITLES[s_id],
            "reason": f"Thiếu dữ liệu: {', '.join(missing_data)}",
        })

    # Fix #10: cache my_domain từ section đã build, không load lại lần 2
    my_domain = "N/A"
    for sec in sections:
        if sec["id"] == "website_overview":
            for insight in sec.get("key_insights", []):
                if insight.startswith("Domain chính: "):
                    my_domain = insight[len("Domain chính: "):]
                    break
            break
    if my_domain == "N/A" and "my_domain" in loaded_keys:
        domain_df = load_data_type(session_id, "my_domain")
        val_col = _find_col(domain_df, "value", "domain") or domain_df.columns[0]
        my_domain = str(domain_df[val_col].iloc[0]).strip()

    return {
        "title": f"Báo cáo SEO Tổng quan — {my_domain}",
        "generated_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "my_domain": my_domain,
        "sections": sections,
        "missing_sections": missing_sections,
    }
