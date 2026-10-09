#!/bin/sh
set -eu
TASK_LOCAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export MYGPT_BUILD_COMMIT="$(git -C "$TASK_LOCAL_DIR/.." rev-parse HEAD)"
export MYGPT_BUILD_BRANCH="$(git -C "$TASK_LOCAL_DIR/.." branch --show-current)"
node "$TASK_LOCAL_DIR/prepare.cjs"
docker compose -p mygpt2-upgrade -f "$TASK_LOCAL_DIR/compose.yml" up -d --build
