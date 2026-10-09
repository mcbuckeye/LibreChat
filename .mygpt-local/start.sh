#!/bin/sh
set -eu
TASK_LOCAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
node "$TASK_LOCAL_DIR/prepare.cjs"
docker compose -p mygpt2-local -f "$TASK_LOCAL_DIR/compose.yml" up -d --build
