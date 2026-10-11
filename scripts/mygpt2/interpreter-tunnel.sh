#!/bin/sh
# Keep this foreground process running while using the remote interpreter.
set -eu
TASK_HOST=${1:-}
TASK_SSH_PORT=${2:-22}
TASK_LOCAL_PORT=${MYGPT2_TUNNEL_PORT:-33114}
# The interpreter currently listens on pchomelab's own Tailscale interface.
# SSH reaches that interface from the server; the client needs no Tailscale.
TASK_REMOTE=${MYGPT2_CODEAPI_TARGET:-100.68.21.112:33114}
case "$TASK_HOST" in ''|-*) echo 'Usage: interpreter-tunnel.sh user@ssh-host [ssh-port]' >&2; exit 1 ;; esac
for TASK_PORT in "$TASK_SSH_PORT" "$TASK_LOCAL_PORT"; do
  case "$TASK_PORT" in ''|*[!0-9]*) echo 'Ports must be numeric.' >&2; exit 1 ;; esac
  [ "$TASK_PORT" -ge 1 ] && [ "$TASK_PORT" -le 65535 ] || exit 1
done
echo "Opening local interpreter tunnel on 127.0.0.1:$TASK_LOCAL_PORT; Ctrl-C stops it."
exec ssh -N -T -p "$TASK_SSH_PORT" \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L "127.0.0.1:$TASK_LOCAL_PORT:$TASK_REMOTE" "$TASK_HOST"
