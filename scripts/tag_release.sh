#!/usr/bin/env bash
# Idempotent tag-and-push script. Reads version from VERSION file.
# Usage: ./scripts/tag_release.sh [--yes] [--skip-existing]
set -euo pipefail

YES=0
SKIP_EXISTING=0
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;;
    --skip-existing) SKIP_EXISTING=1 ;;
  esac
done

VERSION=$(cat VERSION | tr -d '[:space:]')
TAG="v${VERSION}"

if git tag --list | grep -qx "$TAG"; then
  if [[ "$SKIP_EXISTING" -eq 1 ]]; then
    echo "Tag $TAG already exists — skipping (--skip-existing)."
    exit 0
  fi
  echo "Tag $TAG already exists. Use --skip-existing to skip or delete the tag first."
  exit 1
fi

echo "Will create and push tag: $TAG"
if [[ "$YES" -ne 1 ]]; then
  read -r -p "Continue? [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
fi

git tag -a "$TAG" -m "Release $TAG"
git push origin "$TAG"
echo "Tagged and pushed $TAG"
