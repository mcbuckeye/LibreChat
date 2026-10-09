#!/bin/sh
set -eu
TASK_LOCAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CODE_INTERPRETER_PROJECT_DIR=${CODE_INTERPRETER_PROJECT_DIR:-"$(CDPATH= cd -- "$TASK_LOCAL_DIR/../.." && pwd)/code-interpreter"}
export CODE_INTERPRETER_PROJECT_DIR
cd "$CODE_INTERPRETER_PROJECT_DIR"
if ! docker image inspect code-interpreter-python:latest >/dev/null 2>&1; then
  docker build --network=host -f Dockerfile.python -t code-interpreter-python:latest .
fi
docker build --network=host -t code-interpreter:latest .
docker compose -p mygpt2-interpreter -f compose.yml -f "$TASK_LOCAL_DIR/interpreter.compose.yml" up -d --no-build
