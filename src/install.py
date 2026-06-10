"""seo-overview-install — configures Claude Desktop, Claude Code, plugin dir, and shell function."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"
_DIV = "━" * 55

PLUGIN_DEST = Path.home() / ".local/share/seo-overview/plugin"


def _ok(msg: str) -> None:
    print(f"  {_BOLD}{_GREEN}✅ {msg}{_RESET}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}⚠️  {msg}{_RESET}")


def _step(n: int, total: int, msg: str) -> None:
    print(f"\n{_BOLD}{n}/{total} {msg}{_RESET}")


def _get_binary() -> str:
    return shutil.which("seo-overview-server") or "seo-overview-server"


def _get_desktop_config_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    if system == "Windows":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData/Roaming")
        return Path(appdata) / "Claude/claude_desktop_config.json"
    return Path.home() / ".config/Claude/claude_desktop_config.json"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        ts = int(time.time())
        backup = path.parent / f"{path.stem}.json.bak.{ts}"
        path.rename(backup)
        _warn(f"File JSON lỗi — backup: {backup}")
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _build_server_entry(binary: str) -> dict:
    entry: dict = {"command": binary}
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if sa_json:
        entry["env"] = {"GOOGLE_SERVICE_ACCOUNT_JSON": sa_json}
    return entry


def _configure_desktop(binary: str) -> None:
    path = _get_desktop_config_path()
    config = _read_json(path)
    config.setdefault("mcpServers", {})["seo-overview"] = _build_server_entry(binary)
    _write_json(path, config)
    _ok("claude_desktop_config.json")


def _configure_claude_code(binary: str) -> None:
    path = Path.home() / ".claude/settings.json"
    config = _read_json(path)
    config.setdefault("mcpServers", {})["seo-overview"] = _build_server_entry(binary)
    _write_json(path, config)
    _ok("~/.claude/settings.json")


def _find_plugin_source() -> Path:
    """Tìm thư mục chứa skills/agents/.claude-plugin — installed wheel hoặc dev mode."""
    # Installed wheel: hatchling force-include đặt files vào src/seo_overview_plugin/
    installed = Path(__file__).parent / "seo_overview_plugin"
    if (installed / "skills").exists():
        return installed
    # Dev mode: files nằm ở repo root (cha của src/)
    dev = Path(__file__).parent.parent
    if (dev / "skills").exists():
        return dev
    raise FileNotFoundError(
        "Không tìm thấy plugin files (skills/, agents/, .claude-plugin/). "
        "Chạy 'pip install seo-overview' hoặc 'pip install -e .' trước."
    )


def _install_plugin_dir() -> Path:
    src = _find_plugin_source()
    PLUGIN_DEST.mkdir(parents=True, exist_ok=True)

    for name in ("skills", "agents", ".claude-plugin"):
        s = src / name
        if s.exists():
            shutil.copytree(s, PLUGIN_DEST / name, dirs_exist_ok=True)

    mcp_json = src / ".mcp.json"
    if mcp_json.exists():
        shutil.copy(mcp_json, PLUGIN_DEST / ".mcp.json")

    _ok(f"Plugin files → {PLUGIN_DEST}")
    return PLUGIN_DEST


def _add_shell_function(plugin_dir: Path) -> None:
    shell = Path(os.environ.get("SHELL", "")).name
    rc_file = Path.home() / (".zshrc" if shell == "zsh" else ".bashrc")
    marker = "seo-overview: SEO-Overview skill"

    func = (
        f"\n# {marker}\n"
        f'function claude() {{ command claude --plugin-dir "{plugin_dir}" "$@"; }}\n'
    )

    text = rc_file.read_text(encoding="utf-8") if rc_file.exists() else ""
    if marker not in text:
        with rc_file.open("a", encoding="utf-8") as f:
            f.write(func)
        _ok(f"Shell function → {rc_file.name} (claude --plugin-dir auto-loaded)")
    else:
        _ok(f"Shell function đã có trong {rc_file.name}")


def _restart_claude() -> None:
    if platform.system() != "Darwin":
        _warn("Restart Claude Desktop thủ công để áp dụng thay đổi.")
        return
    subprocess.run(["osascript", "-e", 'tell application "Claude" to quit'],
                   capture_output=True)
    time.sleep(3)
    subprocess.run(["open", "-a", "Claude"], capture_output=True)
    _ok("Claude Desktop đã restart")


def main() -> None:
    print(f"\n{_BOLD}{_DIV}{_RESET}")
    print(f"{_BOLD}  SEO Overview MCP Plugin — Install{_RESET}")
    print(f"{_BOLD}{_DIV}{_RESET}")

    binary = _get_binary()
    print(f"\n  Binary: {binary}")

    _step(1, 4, "Cấu hình Claude Desktop MCP server...")
    _configure_desktop(binary)

    _step(2, 4, "Cấu hình Claude Code CLI...")
    _configure_claude_code(binary)

    _step(3, 4, "Cài đặt plugin files...")
    plugin_dir = _install_plugin_dir()

    _step(4, 4, "Thêm shell function + restart Claude Desktop...")
    _add_shell_function(plugin_dir)
    _restart_claude()

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    print(f"\n{_BOLD}{_GREEN}{_DIV}{_RESET}")
    print(f"{_BOLD}{_GREEN}  Cài đặt hoàn tất!{_RESET}")
    print(f"{_BOLD}{_GREEN}{_DIV}{_RESET}")
    print(f"\n  MCP tools → hoạt động ngay trong Claude Desktop + Claude Code")

    if not sa_json:
        print(f"\n  {_YELLOW}⚠️  GOOGLE_SERVICE_ACCOUNT_JSON chưa được set.{_RESET}")
        print(f"  Thêm vào claude_desktop_config.json hoặc ~/.claude/settings.json:")
        print(f'    mcpServers → seo-overview → env → "GOOGLE_SERVICE_ACCOUNT_JSON": "..."')

    print(f"\n{_BOLD}  Để dùng /seo-overview:SEO-Overview trong Cowork (1 lần duy nhất):{_RESET}")
    print(f"  Cowork → Settings → Plugins → Upload → chọn file seo-overview.plugin")
    print(f"  (Tải tại: https://github.com/minhdo01011990-glitch/seo-overview/releases/latest)")
    print(f"\n{_BOLD}{_GREEN}{_DIV}{_RESET}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
