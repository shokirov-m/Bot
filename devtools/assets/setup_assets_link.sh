#!/usr/bin/env bash
# Symlink tower_bot/assets -> content/assets
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LINK="$ROOT/assets"
TARGET="$ROOT/content/assets"
if [[ -e "$LINK" ]]; then
  echo "Already exists: $LINK"
  exit 0
fi
ln -s "content/assets" "$LINK"
echo "Created symlink: assets -> content/assets"
