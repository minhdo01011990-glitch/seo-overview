#!/usr/bin/env bash
# install.sh — Cài đặt / cập nhật seo-overview MCP server
# Dùng: bash <(curl -fsSL https://github.com/minhdo01011990-glitch/seo-overview/releases/latest/download/install.sh)
set -euo pipefail

BOLD="\033[1m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"

REPO="https://github.com/minhdo01011990-glitch/seo-overview"
PLUGIN_DIR="$HOME/.claude/plugins/seo-overview"
PLUGIN_FILE="/tmp/seo-overview-$$.plugin"

# ── Cleanup trap: xóa file tạm khi script exit (bình thường hoặc lỗi) ────────

cleanup() {
    rm -f "$PLUGIN_FILE"
    # Nếu có backup venv nhưng script fail giữa chừng, khôi phục lại
    if [[ -d "/tmp/seo-overview-venv-backup-$$" ]]; then
        mv "/tmp/seo-overview-venv-backup-$$" "$PLUGIN_DIR/.venv" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── 1. Tìm Python 3.9+ ───────────────────────────────────────────────────────

PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" &>/dev/null; then
        _major=$("$candidate" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)
        _minor=$("$candidate" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
        if [[ "$_major" -eq 3 && "$_minor" -ge 9 ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo -e "${RED}❌ Không tìm thấy Python 3.9+.${RESET}"
    echo "   Tải tại: https://python.org/downloads/"
    echo "   (python3 --version hiện tại: $(python3 --version 2>/dev/null || echo 'không tìm thấy'))"
    exit 1
fi
echo -e "${BOLD}Python:${RESET} $("$PYTHON" --version)"

# ── 2. Tải .plugin từ GitHub Releases ────────────────────────────────────────

echo -e "${BOLD}Tải seo-overview từ GitHub Releases...${RESET}"
if ! curl -fsSL --connect-timeout 10 --max-time 120 \
        "$REPO/releases/latest/download/seo-overview.plugin" -o "$PLUGIN_FILE"; then
    echo -e "${RED}❌ Không tải được file. Kiểm tra kết nối Internet hoặc URL release.${RESET}"
    echo "   URL: $REPO/releases/latest/download/seo-overview.plugin"
    exit 1
fi

# ── 2b. Verify checksum nếu có file .sha256 ──────────────────────────────────

SHA256_FILE="/tmp/seo-overview-$$.sha256"
if curl -fsSL --connect-timeout 10 --max-time 30 \
        "$REPO/releases/latest/download/seo-overview.plugin.sha256" -o "$SHA256_FILE" 2>/dev/null; then
    echo -e "${BOLD}Kiểm tra checksum...${RESET}"
    # Ghi lại tên file tạm vào file sha256 để shasum/sha256sum có thể verify
    expected_hash=$(cat "$SHA256_FILE" | awk '{print $1}')
    if command -v shasum &>/dev/null; then
        actual_hash=$(shasum -a 256 "$PLUGIN_FILE" | awk '{print $1}')
    elif command -v sha256sum &>/dev/null; then
        actual_hash=$(sha256sum "$PLUGIN_FILE" | awk '{print $1}')
    else
        actual_hash=""
    fi
    rm -f "$SHA256_FILE"
    if [[ -n "$actual_hash" && "$actual_hash" != "$expected_hash" ]]; then
        echo -e "${RED}❌ Checksum không khớp — file có thể bị lỗi hoặc giả mạo.${RESET}"
        echo "   Expected: $expected_hash"
        echo "   Actual:   $actual_hash"
        exit 1
    fi
fi

# ── 3. Giải nén vào ~/.claude/plugins/seo-overview/ ──────────────────────────

UPDATE_MODE=false
if [[ -d "$PLUGIN_DIR" ]]; then
    UPDATE_MODE=true
    echo -e "${YELLOW}⟳  Phát hiện cài đặt cũ — đang cập nhật...${RESET}"
    # Giữ lại .venv để không phải cài lại dependencies
    if [[ -d "$PLUGIN_DIR/.venv" ]]; then
        # Xóa backup cũ nếu còn sót từ lần trước để tránh mv lồng thư mục
        rm -rf "/tmp/seo-overview-venv-backup-$$"
        mv "$PLUGIN_DIR/.venv" "/tmp/seo-overview-venv-backup-$$"
    fi
    rm -rf "$PLUGIN_DIR"
fi

mkdir -p "$PLUGIN_DIR"

# Giải nén: ưu tiên unzip, fallback về python zipfile module (cross-version safe)
if command -v unzip &>/dev/null; then
    unzip -q "$PLUGIN_FILE" -d "$PLUGIN_DIR"
else
    "$PYTHON" -c "
import zipfile, sys
with zipfile.ZipFile(sys.argv[1]) as zf:
    zf.extractall(sys.argv[2])
" "$PLUGIN_FILE" "$PLUGIN_DIR"
fi

# Khôi phục .venv nếu đang update (trap đã cleanup nếu thất bại)
if [[ "$UPDATE_MODE" == "true" && -d "/tmp/seo-overview-venv-backup-$$" ]]; then
    mv "/tmp/seo-overview-venv-backup-$$" "$PLUGIN_DIR/.venv"
fi

# ── 4. Tạo virtualenv + cài dependencies ─────────────────────────────────────

if [[ ! -d "$PLUGIN_DIR/.venv" ]]; then
    echo -e "${BOLD}Tạo virtualenv...${RESET}"
    "$PYTHON" -m venv "$PLUGIN_DIR/.venv"
fi

# Guard: kiểm tra venv được tạo thành công
if [[ ! -f "$PLUGIN_DIR/.venv/bin/pip" ]]; then
    echo -e "${RED}❌ Tạo virtualenv thất bại — không tìm thấy pip trong .venv.${RESET}"
    exit 1
fi

echo -e "${BOLD}Cài dependencies...${RESET}"
"$PLUGIN_DIR/.venv/bin/pip" install --quiet --upgrade pip
# Không dùng --quiet để pip hiển thị lỗi nếu install thất bại
"$PLUGIN_DIR/.venv/bin/pip" install -e "$PLUGIN_DIR"

# ── 5. Đăng ký MCP server vào Claude Desktop + Claude Code ───────────────────

echo -e "${BOLD}Đăng ký MCP server...${RESET}"
"$PLUGIN_DIR/.venv/bin/seo-overview-install"

# ── 6. Kết quả ───────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}${BOLD}✅ Cài đặt hoàn tất!${RESET}"
echo ""

if [[ -z "${GOOGLE_SERVICE_ACCOUNT_JSON:-}" ]]; then
    echo -e "${YELLOW}⚠  GOOGLE_SERVICE_ACCOUNT_JSON chưa được set.${RESET}"
    echo "   Plugin cần Google Service Account để đọc Google Sheets."
    echo ""
    echo "   Cách set:"
    echo '   export GOOGLE_SERVICE_ACCOUNT_JSON='"'"'{"type":"service_account",...}'"'"
    echo "   Sau đó chạy lại: $PLUGIN_DIR/.venv/bin/seo-overview-install"
    echo ""
fi

if [[ "$UPDATE_MODE" == "true" ]]; then
    echo "   Đã cập nhật lên phiên bản mới nhất."
else
    echo "   Bước tiếp theo:"
fi
echo "   • Tắt Claude Desktop (Cmd+Q) rồi mở lại"
echo "   • Kiểm tra: biểu tượng 🔧 xuất hiện trong chat = MCP hoạt động"
echo "   • Dùng slash command: /seo-overview:SEO-Overview"
echo ""
