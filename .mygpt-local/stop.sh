#!/bin/sh
set -eu
TASK_LOCAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
docker compose -p mygpt2-upgrade -f "$TASK_LOCAL_DIR/compose.yml" stop
