#!/usr/bin/env bash
# Đóng gói seo-overview.plugin
# Chạy: bash package-plugin.sh
set -euo pipefail

cd "$(dirname "$0")"

OUTPUT="seo-overview.plugin"
rm -f "$OUTPUT"

TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT

cp .mcp.json                "$TMP/.mcp.json"
cp -r .claude-plugin        "$TMP/.claude-plugin"
cp -r skills                "$TMP/skills"

cd "$TMP"
zip -r "$OLDPWD/$OUTPUT" . --exclude "*.DS_Store" --exclude "__pycache__/*"

echo "✅ Đã tạo: $OLDPWD/$OUTPUT"
