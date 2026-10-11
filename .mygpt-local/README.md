# MyGPT2 on LibreChat v0.8.8

The upgrade runs from source in a separate Docker Compose project, `mygpt2-upgrade`. Node 24.16.0 builds and serves the app inside Docker. Node on the Mac prepares the build context. The original `mygpt2-local` stack remains on port 3080 with its existing volumes.

| Service | Local URL |
| --- | --- |
| Upgraded MyGPT2 | http://localhost:3081 |
| Reporting dashboard | http://localhost:8083/dashboard |
| Upgraded custom interpreter API | http://localhost:8084 |

MongoDB 8.0.20, Meilisearch 1.35.1, pgvector and the pinned RAG API run with separate named volumes. RAG uses the existing privately supplied provider key for embeddings. Every published development port binds to loopback.

## Start and stop

On a fresh checkout, provide the private environment source. With an existing runtime.env (including one restored from the handoff package), start.sh preserves it unchanged. Start the custom interpreter separately only when deliberately using custom mode:

```sh
CODE_INTERPRETER_PROJECT_DIR=/absolute/path/to/code-interpreter-mygpt2-upgrade .mygpt-local/start-interpreter.sh
MYGPT_ENV_SOURCE=/absolute/path/to/private/.env .mygpt-local/start.sh
```

If this checkout has its own ignored `.env`, omit MYGPT_ENV_SOURCE. It must contain the configured model provider credentials. On first initialization only, the helper generates persistent local encryption/session keys and a PostgreSQL password under `.mygpt-local`, creates runtime.env with local email registration and SSO disabled. Subsequent starts preserve runtime.env, including SSO and model settings. It retains interpreter-mode, or selects official mode if its private overlay is present. Keep generated keys with their database. Do not delete runtime.env to change a setting; edit the ignored file deliberately. See MYGPT2-HANDOFF.md for the BeOne Mac setup and SSH tunnel.

```sh
.mygpt-local/stop.sh
CODE_INTERPRETER_PROJECT_DIR=/absolute/path/to/code-interpreter-mygpt2-upgrade .mygpt-local/stop-interpreter.sh
docker compose -p mygpt2-upgrade -f .mygpt-local/compose.yml ps
```

Stopping preserves data. Do not use `down -v` unless intentionally discarding the test database and files.

## Interpreter

MyGPT2 currently connects to the official Linux KVM interpreter at `http://100.68.21.112:33114/v1` with JWT authentication. See tracked `MYGPT2-CODE-INTERPRETER.md` for the current deployment and the verified `scripts/mygpt2/interpreter.sh official|custom|status` switch. The preserved custom rollback target is `http://host.docker.internal:8084/v1/librechat`. The upgraded custom interpreter supports Bash using our scientific Python sandbox, SDK 4 storage-session references, and staging inputs from multiple upload sessions. It uses a separate API image and the `mygpt2-python:v0.8.8` sandbox tag. Only Python/Bash were built and tested; other languages require their sandbox images.

To use it, choose Tools Options beside the attachment button, enable **Run Code**, and ask for Python execution. Charts display in chat and workbooks open as previews and can be downloaded. **File Search** uses the separate RAG service.

```sh
docker compose -p mygpt2-upgrade -f .mygpt-local/compose.yml exec -T api node < .mygpt-local/test-interpreter.cjs
```

The custom interpreter is a private local test service and uses the Docker socket to start execution containers. It is not a production authentication/isolation design. The official Apache-licensed LibreChat interpreter is a separate candidate for production; it has its own Redis, object storage and sandbox runner. The official interpreter is now deployed as the separate `mygpt2-codeapi` project on pchomelab; its maintained source and tests are in `/Users/stephenmclaughlin/Development/mygpt2-code-interpreter`. The earlier temporary Mac official-test containers have been stopped, with volumes retained.

## Deployment boundary

This is a fresh-data local validation environment. Live Entra SSO, company-server deployment, production user/data migration, experimental workspaces/scheduling and all model-provider combinations require separate acceptance testing. SCHEDULES_SINGLE_PROCESS=true describes this single API process; a multi-replica deployment must use the appropriate shared Redis stores instead. Beta features are not exposed by this local configuration.

Private environment files, generated secrets, build contexts and test artifacts are excluded from Git. Existing company configuration is not modified. The root Compose file now builds MyGPT2 from source so the additional tested dependency fixes are included; do not apply it to the older production database without a migration plan.
