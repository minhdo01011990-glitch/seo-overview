"""CLI: seo-overview-install — đăng ký MCP server vào Claude Desktop App và Claude Code."""

from __future__ import annotations

import json
import os
import pathlib
import platform
import shutil
import sys
import tempfile


# ── Config paths ────────────────────────────────────────────────────────────

def _desktop_config_path() -> pathlib.Path:
    system = platform.system()
    if system == "Darwin":
        return pathlib.Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if system == "Windows":
        # Fallback an toàn nếu APPDATA không được set (CI, container, profile lỗi)
        appdata = os.environ.get("APPDATA") or str(pathlib.Path.home() / "AppData" / "Roaming")
        return pathlib.Path(appdata) / "Claude" / "claude_desktop_config.json"
    return pathlib.Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _claude_code_settings_path() -> pathlib.Path:
    return pathlib.Path.home() / ".claude" / "settings.json"


def _server_command() -> str:
    cmd = shutil.which("seo-overview-server")
    return cmd if cmd else "seo-overview-server"


# ── JSON helpers ─────────────────────────────────────────────────────────────

def _read_json(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Dùng timestamp để tránh overwrite backup cũ
        import time
        ts = int(time.time())
        backup = path.parent / f"{path.stem}.json.bak.{ts}"
        path.rename(backup)
        print(f"   ⚠ File lỗi JSON — backup: {backup}")
        return {}


def _write_json(path: pathlib.Path, data: dict) -> None:
    """Ghi JSON atomic: ghi ra .tmp rồi rename để tránh corrupt nếu bị interrupt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    # Ghi ra file tạm cùng thư mục để rename atomic (cùng filesystem)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)  # atomic trên POSIX; best-effort trên Windows
    except Exception:
        # Cleanup file tạm nếu có lỗi
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _build_server_entry(server_cmd: str, sa_json: str) -> dict:
    """Build MCP server entry. Chỉ thêm env key nếu sa_json có giá trị."""
    entry: dict = {"command": server_cmd}
    if sa_json:
        entry["env"] = {"GOOGLE_SERVICE_ACCOUNT_JSON": sa_json}
    return entry


# ── Step 1: Claude Desktop App ───────────────────────────────────────────────

def _install_desktop_app(server_cmd: str, sa_json: str) -> tuple[bool, pathlib.Path]:
    path = _desktop_config_path()
    config = _read_json(path)
    mcp = config.setdefault("mcpServers", {})
    already = "seo-overview" in mcp
    mcp["seo-overview"] = _build_server_entry(server_cmd, sa_json)
    _write_json(path, config)
    return already, path


# ── Step 2: Claude Code global MCP ──────────────────────────────────────────

def _install_claude_code_mcp(server_cmd: str, sa_json: str) -> tuple[bool, pathlib.Path]:
    path = _claude_code_settings_path()
    config = _read_json(path)
    mcp = config.setdefault("mcpServers", {})
    already = "seo-overview" in mcp
    mcp["seo-overview"] = _build_server_entry(server_cmd, sa_json)
    _write_json(path, config)
    return already, path


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    server_cmd = _server_command()
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    print()
    print("Đang đăng ký MCP server seo-overview...")
    print()

    # 1. Claude Desktop App
    desktop_already, desktop_path = _install_desktop_app(server_cmd, sa_json)
    verb = "cập nhật" if desktop_already else "thêm mới"
    print(f"✓ [1/2] Claude Desktop App: {verb}")
    print(f"        {desktop_path}")
    print()

    # 2. Claude Code global MCP
    cc_already, cc_path = _install_claude_code_mcp(server_cmd, sa_json)
    verb = "cập nhật" if cc_already else "thêm mới"
    print(f"✓ [2/2] Claude Code — MCP server: {verb}")
    print(f"        {cc_path}")
    print()

    print("─" * 56)
    print()
    print("Bước tiếp theo:")
    print()

    if not sa_json:
        print("  ⚠ GOOGLE_SERVICE_ACCOUNT_JSON chưa được set.")
        print("    Thêm thủ công vào file config sau khi cài:")
        print()
        print("    Claude Desktop App:")
        print(f"      {desktop_path}")
        print('      → mcpServers["seo-overview"]["env"]["GOOGLE_SERVICE_ACCOUNT_JSON"]')
        print()
        print("    Claude Code:")
        print(f"      {cc_path}")
        print('      → mcpServers["seo-overview"]["env"]["GOOGLE_SERVICE_ACCOUNT_JSON"]')
        print()

    print("  Claude Desktop App:")
    print("    • Tắt hoàn toàn (Cmd+Q trên Mac) rồi mở lại")
    print("    • Biểu tượng 🔧 trong chat = MCP đã hoạt động")
    print()
    print("  Claude Code:")
    print("    • MCP tools hoạt động ngay, không cần làm gì thêm")
    print()
    print("  Dùng slash command:")
    print("    /seo-overview:SEO-Overview")
    print()

    sys.exit(0)


if __name__ == "__main__":
    main()
