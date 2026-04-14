#!/bin/bash
# apply_patches.sh
# Run this from the project root AFTER cloning mini-sglang.
# It copies our modified/new files into the correct locations in the repo.
#
# Usage:
#   bash apply_patches.sh [path/to/mini-sglang]
# Default mini-sglang path: ./mini-sglang

set -e

REPO="${1:-./mini-sglang}"
SRC="$(dirname "$0")/src"

if [ ! -d "$REPO" ]; then
    echo "Error: mini-sglang repo not found at '$REPO'"
    echo "Clone it first:  git clone https://github.com/sgl-project/mini-sglang"
    exit 1
fi

PKG="$REPO/python/minisgl"

echo "Applying patches to $PKG ..."

# New files
cp "$SRC/minisgl/scheduler/telemetry.py"  "$PKG/scheduler/telemetry.py"
cp "$SRC/minisgl/scheduler/policies.py"   "$PKG/scheduler/policies.py"

# Modified files
cp "$SRC/minisgl/scheduler/utils.py"      "$PKG/scheduler/utils.py"
cp "$SRC/minisgl/scheduler/prefill.py"    "$PKG/scheduler/prefill.py"
cp "$SRC/minisgl/scheduler/scheduler.py"  "$PKG/scheduler/scheduler.py"
cp "$SRC/minisgl/message/backend.py"      "$PKG/message/backend.py"
cp "$SRC/minisgl/message/tokenizer.py"    "$PKG/message/tokenizer.py"
cp "$SRC/minisgl/tokenizer/server.py"     "$PKG/tokenizer/server.py"
cp "$SRC/minisgl/server/api_server.py"    "$PKG/server/api_server.py"

echo "Done. Files written:"
echo "  [NEW]  $PKG/scheduler/telemetry.py"
echo "  [NEW]  $PKG/scheduler/policies.py"
echo "  [MOD]  $PKG/scheduler/utils.py        (+ client_id, arrival_time on PendingReq)"
echo "  [MOD]  $PKG/scheduler/prefill.py      (+ policy dispatch + deficit update)"
echo "  [MOD]  $PKG/scheduler/scheduler.py    (+ telemetry recording + AIMD wiring)"
echo "  [MOD]  $PKG/message/backend.py        (+ client_id on UserMsg)"
echo "  [MOD]  $PKG/message/tokenizer.py      (+ client_id on TokenizeMsg)"
echo "  [MOD]  $PKG/tokenizer/server.py       (+ pass client_id -> UserMsg)"
echo "  [MOD]  $PKG/server/api_server.py      (+ client_id on request models)"
echo ""
echo "Quick smoke test:"
echo "  cd $REPO && pip install -e . && MINISGL_POLICY=lpm python -m minisgl --model-path Qwen/Qwen3-0.6B --dummy-weight --shell-mode"
echo ""
echo "To run with a specific policy:"
echo "  MINISGL_POLICY=dlpm MINISGL_STATIC_Q=8000 python -m minisgl ..."
echo "  MINISGL_POLICY=adaptive_dlpm python -m minisgl ..."
