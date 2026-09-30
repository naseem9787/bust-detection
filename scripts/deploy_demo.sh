#!/usr/bin/env bash
# Build the backend-free demo (saved real API responses) and publish it to
# the gh-pages branch -> https://naseem9787.github.io/bust-detection/
#
#   bash scripts/deploy_demo.sh            # reuse data/demo_snapshot if present
#   REBUILD_SNAPSHOT=1 bash scripts/deploy_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
SNAP="$ROOT/data/demo_snapshot"
DIST="$ROOT/data/demo_dist"

if [[ ! -f "$SNAP/regions.json" || "${REBUILD_SNAPSHOT:-0}" == "1" ]]; then
  rm -rf "$SNAP"
  .venv/Scripts/python.exe -m src.production.build_demo_snapshot "$SNAP"
fi

(cd frontend && VITE_SNAPSHOT=true VITE_USE_MOCK=false VITE_BASE=/bust-detection/ \
   npx vite build --outDir "$DIST" --emptyOutDir)
cp -r "$SNAP" "$DIST/snapshot"
touch "$DIST/.nojekyll"

WT="$ROOT/data/gh-pages-worktree"
rm -rf "$WT"; git worktree prune
if git ls-remote --exit-code --heads origin gh-pages >/dev/null; then
  git fetch -q origin gh-pages
  git worktree add -q "$WT" -B gh-pages origin/gh-pages
else
  git worktree add -q --detach "$WT"
  (cd "$WT" && git checkout -q --orphan gh-pages)
fi
(cd "$WT" && git rm -rq --ignore-unmatch . && cp -r "$DIST"/. . && git add -A \
   && git commit -qm "Deploy static demo ($(git -C "$ROOT" rev-parse --short HEAD))" && git push -q origin gh-pages)
git worktree remove --force "$WT"
echo "Deployed -> https://naseem9787.github.io/bust-detection/"
