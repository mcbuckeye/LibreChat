#!/bin/sh
set -eu
TASK_LOCAL_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export MYGPT_BUILD_COMMIT="$(git -C "$TASK_LOCAL_DIR/.." rev-parse HEAD)"
export MYGPT_BUILD_BRANCH="$(git -C "$TASK_LOCAL_DIR/.." branch --show-current)"
TASK_MODE=custom
if [ -f "$TASK_LOCAL_DIR/interpreter-mode" ]; then
  TASK_MODE=$(cat "$TASK_LOCAL_DIR/interpreter-mode")
elif [ -f "$TASK_LOCAL_DIR/official-interpreter.yml" ]; then
  TASK_MODE=official
fi
case "$TASK_MODE" in
  official)
    [ -r "$TASK_LOCAL_DIR/official-interpreter.yml" ] || {
      echo 'Official interpreter selected but its private overlay is missing.' >&2
      exit 1
    }
    set -- -f "$TASK_LOCAL_DIR/compose.yml" -f "$TASK_LOCAL_DIR/official-interpreter.yml"
    ;;
  custom) set -- -f "$TASK_LOCAL_DIR/compose.yml" ;;
  *) echo 'Invalid interpreter-mode; expected official or custom.' >&2; exit 1 ;;
esac
node "$TASK_LOCAL_DIR/prepare.cjs"
docker compose -p mygpt2-upgrade "$@" up -d --build
printf '%s\n' "$TASK_MODE" > "$TASK_LOCAL_DIR/interpreter-mode"
