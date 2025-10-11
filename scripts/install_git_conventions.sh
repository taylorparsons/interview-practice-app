#!/usr/bin/env bash
# Installs repo-local git conventions:
# - Sets the commit template to .github/commit_template.txt
# - Installs the pre-commit hook that enforces comment lines on code changes
#
# Usage:
#   scripts/install_git_conventions.sh
#
# Notes:
# - Hooks are installed into .git/hooks (not tracked by git).
# - Re-run after cloning or cleaning .git.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

TEMPLATE_PATH="${ROOT_DIR}/.github/commit_template.txt"
HOOK_SRC="${ROOT_DIR}/scripts/hooks/pre-commit"
HOOK_DEST="${ROOT_DIR}/.git/hooks/pre-commit"

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  echo "Commit template missing at $TEMPLATE_PATH" >&2
  exit 1
fi

if [[ ! -f "$HOOK_SRC" ]]; then
  echo "Pre-commit hook missing at $HOOK_SRC" >&2
  exit 1
fi

echo "Configuring git commit template..."
git config commit.template "$TEMPLATE_PATH"

echo "Installing pre-commit hook -> $HOOK_DEST"
mkdir -p "$(dirname "$HOOK_DEST")"
cp "$HOOK_SRC" "$HOOK_DEST"
chmod +x "$HOOK_DEST"

echo "Done. Commit template configured and pre-commit hook installed."

