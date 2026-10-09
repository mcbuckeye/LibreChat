#!/bin/sh
set -eu
TASK_LOCAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CODE_INTERPRETER_PROJECT_DIR=${CODE_INTERPRETER_PROJECT_DIR:-"$(CDPATH= cd -- "$TASK_LOCAL_DIR/../.." && pwd)/code-interpreter-mygpt2-upgrade"}
export CODE_INTERPRETER_PROJECT_DIR
cd "$CODE_INTERPRETER_PROJECT_DIR"
if ! docker image inspect mygpt2-python:v0.8.8 >/dev/null 2>&1; then
  docker build --network=host -f Dockerfile.python -t mygpt2-python:v0.8.8 .
fi
docker build --network=host -t mygpt2-upgrade-interpreter:local .
docker compose -p mygpt2-upgrade-interpreter -f compose.yml -f "$TASK_LOCAL_DIR/interpreter.compose.yml" up -d --no-build
