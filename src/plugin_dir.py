"""CLI helper: in ra đường dẫn thư mục plugin để dùng với claude --plugin-dir."""

from __future__ import annotations

import pathlib


def _is_valid_plugin_dir(p: pathlib.Path) -> bool:
    """Kiểm tra thư mục có đủ cấu trúc plugin không (phải có plugin.json)."""
    return (p / ".claude-plugin" / "plugin.json").exists()


def get_plugin_dir() -> pathlib.Path:
    # Khi cài từ wheel (pip install): src/seo_overview_plugin/ được build từ pyproject.toml force-include
    pip_bundle = pathlib.Path(__file__).parent / "seo_overview_plugin"
    if pip_bundle.exists() and _is_valid_plugin_dir(pip_bundle):
        return pip_bundle
    # Khi chạy từ source (git clone / pip install -e): thư mục gốc của project
    source_root = pathlib.Path(__file__).parent.parent
    return source_root


def main() -> None:
    plugin_dir = get_plugin_dir()
    if not _is_valid_plugin_dir(plugin_dir):
        import sys
        print(
            f"WARNING: plugin dir '{plugin_dir}' không tìm thấy .claude-plugin/plugin.json. "
            "Wheel có thể chưa được build đúng.",
            file=sys.stderr,
        )
    print(plugin_dir)


if __name__ == "__main__":
    main()
