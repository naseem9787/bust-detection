#!/usr/bin/env bash
# Build the backend-free demo (saved real API responses) and publish it to
# the gh-pages branch -> https://naseem9787.github.io/bust-detection/
#
#   bash scripts/deploy_demo.sh            # reuse data/demo_snapshot if present
#   REBUILD_SNAPSHOT=1 bash scripts/deploy_demo.sh
#
# Repo-relative paths only: on Windows, git and node read Git Bash's /c/...
# absolute paths as C:\c\..., so nothing below uses an absolute path.
set -euo pipefail
export MSYS_NO_PATHCONV=1   # keep /bust-detection/ (the Pages base path) from being rewritten
cd "$(dirname "$0")/.."

SNAP="data/demo_snapshot"
DIST="data/demo_dist"
WT="data/gh-pages-worktree"

if [[ ! -f "$SNAP/regions.json" || "${REBUILD_SNAPSHOT:-0}" == "1" ]]; then
  rm -rf "$SNAP"
  .venv/Scripts/python.exe -m src.production.build_demo_snapshot "$SNAP"
fi

rm -rf "$DIST"
(cd frontend && VITE_SNAPSHOT=true VITE_USE_MOCK=false VITE_BASE=/bust-detection/ \
   npx vite build --outDir "../$DIST" --emptyOutDir)
cp -r "$SNAP" "$DIST/snapshot"
touch "$DIST/.nojekyll"

rm -rf "$WT"; git worktree prune
if git ls-remote --exit-code --heads origin gh-pages >/dev/null 2>&1; then
  git fetch -q origin gh-pages
  git worktree add -q "$WT" -B gh-pages origin/gh-pages
else
  git worktree add -q --detach "$WT"
  (cd "$WT" && git checkout -q --orphan gh-pages)
fi
SHA="$(git rev-parse --short HEAD)"
(cd "$WT" && git rm -rqf --ignore-unmatch . && cp -r "../../$DIST"/. . && git add -A \
   && git commit -qm "Deploy static demo ($SHA)" && git push -q origin gh-pages)
git worktree remove --force "$WT"
echo "Deployed -> https://naseem9787.github.io/bust-detection/"
