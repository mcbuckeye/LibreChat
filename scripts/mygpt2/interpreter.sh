#!/bin/bash
# Switch only MyGPT2's API; preserve custom interpreter and both storage sets.
set -euo pipefail
TASK_ROOT=$(cd -- "$(dirname -- "$0")/../.." && pwd)
TASK_LOCAL=${MYGPT2_RUNTIME_DIR:-"$TASK_ROOT/.mygpt-local"}
TASK_MODE=${1:-status}
TASK_BASE="$TASK_LOCAL/compose.yml"
TASK_OVERLAY="$TASK_LOCAL/official-interpreter.yml"
TASK_STATE="$TASK_LOCAL/interpreter-mode"
compose_mode() {
  local mode=$1; shift
  local args=(-p mygpt2-upgrade -f "$TASK_BASE")
  if [[ $mode == official ]]; then args+=(-f "$TASK_OVERLAY"); fi
  docker compose "${args[@]}" "$@"
}
health() {
  local cid
  cid=$(compose_mode "$1" ps -q api)
  for ((i=0; i<45; i++)); do
    if docker exec "$cid" node -e 'fetch("http://localhost:3080/health").then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))' >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  return 1
}
if [[ $TASK_MODE == status ]]; then
  docker exec mygpt2-upgrade-api-1 node -e 'console.log("Interpreter:",process.env.LIBRECHAT_CODE_BASEURL,"Auth:",process.env.CODEAPI_AUTH_PROVIDER||"legacy")'
  exit
fi
[[ $TASK_MODE == official || $TASK_MODE == custom ]] || { echo 'Usage: interpreter.sh official|custom|status' >&2; exit 2; }
TASK_PREVIOUS=custom
[[ ! -f $TASK_STATE ]] || TASK_PREVIOUS=$(cat "$TASK_STATE")
if [[ $TASK_MODE == official ]]; then
  [[ -r $TASK_OVERLAY ]] || { echo 'Missing private official-interpreter.yml overlay' >&2; exit 1; }
  # Preflight from Docker, where MyGPT2 actually calls the interpreter.
  TASK_ENDPOINT=$(node -e 'const f=require("fs");console.log(JSON.parse(f.readFileSync(process.argv[1])).services.api.environment.LIBRECHAT_CODE_BASEURL)' "$TASK_OVERLAY")
  docker exec mygpt2-upgrade-api-1 node -e 'fetch(process.argv[1]+"/health",{signal:AbortSignal.timeout(10000)}).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))' "$TASK_ENDPOINT"
fi
if ! compose_mode "$TASK_MODE" up -d --no-deps api || ! health "$TASK_MODE"; then
  echo "Switch failed; restoring $TASK_PREVIOUS" >&2
  compose_mode "$TASK_PREVIOUS" up -d --no-deps api
  health "$TASK_PREVIOUS"
  exit 1
fi
printf '%s\n' "$TASK_MODE" > "$TASK_STATE.tmp"
mv "$TASK_STATE.tmp" "$TASK_STATE"
"$0" status
