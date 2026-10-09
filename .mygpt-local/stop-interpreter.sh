#!/bin/sh
set -eu
TASK_LOCAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CODE_INTERPRETER_PROJECT_DIR=${CODE_INTERPRETER_PROJECT_DIR:-"$(CDPATH= cd -- "$TASK_LOCAL_DIR/../.." && pwd)/code-interpreter"}
export CODE_INTERPRETER_PROJECT_DIR
cd "$CODE_INTERPRETER_PROJECT_DIR"
docker compose -p mygpt2-interpreter -f compose.yml -f "$TASK_LOCAL_DIR/interpreter.compose.yml" stop
