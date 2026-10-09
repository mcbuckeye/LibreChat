# MyGPT2 on LibreChat v0.8.8

The upgrade runs from source in a separate Docker Compose project, `mygpt2-upgrade`. Node 24.16.0 builds and serves the app inside Docker. Node on the Mac prepares the build context. The original `mygpt2-local` stack remains on port 3080 with its existing volumes.

| Service | Local URL |
| --- | --- |
| Upgraded MyGPT2 | http://localhost:3081 |
| Reporting dashboard | http://localhost:8083/dashboard |
| Upgraded custom interpreter API | http://localhost:8084 |

MongoDB 8.0.20, Meilisearch 1.35.1, pgvector and the pinned RAG API run with separate named volumes. RAG uses the existing privately supplied provider key for embeddings. Every published development port binds to loopback.

## Start and stop

From this checkout, provide the private environment source and the upgraded interpreter checkout location:

```sh
CODE_INTERPRETER_PROJECT_DIR=/absolute/path/to/code-interpreter-mygpt2-upgrade .mygpt-local/start-interpreter.sh
MYGPT_ENV_SOURCE=/absolute/path/to/private/.env .mygpt-local/start.sh
```

If this checkout has its own ignored `.env`, omit MYGPT_ENV_SOURCE. It must contain the configured model provider credentials. The helper generates persistent local encryption/session keys and a PostgreSQL password under `.mygpt-local`, creates a private runtime.env, disables Microsoft SSO for localhost, and enables local email registration. Keep those generated keys when restarting this database.

```sh
.mygpt-local/stop.sh
CODE_INTERPRETER_PROJECT_DIR=/absolute/path/to/code-interpreter-mygpt2-upgrade .mygpt-local/stop-interpreter.sh
docker compose -p mygpt2-upgrade -f .mygpt-local/compose.yml ps
```

Stopping preserves data. Do not use `down -v` unless intentionally discarding the test database and files.

## Interpreter

MyGPT2 connects to `http://host.docker.internal:8084/v1/librechat`. The upgraded custom interpreter supports Bash using our scientific Python sandbox, SDK 4 storage-session references, and staging inputs from multiple upload sessions. It uses a separate API image and the `mygpt2-python:v0.8.8` sandbox tag. Only Python/Bash were built and tested; other languages require their sandbox images.

To use it, choose Tools Options beside the attachment button, enable **Run Code**, and ask for Python execution. Charts display in chat and workbooks open as previews and can be downloaded. **File Search** uses the separate RAG service.

```sh
docker compose -p mygpt2-upgrade -f .mygpt-local/compose.yml exec -T api node < .mygpt-local/test-interpreter.cjs
```

The interpreter is a private local test service and uses the Docker socket to start execution containers. It is not a production authentication/isolation design. The official Apache-licensed LibreChat interpreter is a separate candidate for production; it has its own Redis, object storage and sandbox runner. It has not been deployed by this upgrade.

## Deployment boundary

This is a fresh-data local validation environment. Live Entra SSO, company-server deployment, production user/data migration, experimental workspaces/scheduling and all model-provider combinations require separate acceptance testing. SCHEDULES_SINGLE_PROCESS=true describes this single API process; a multi-replica deployment must use the appropriate shared Redis stores instead. Beta features are not exposed by this local configuration.

Private environment files, generated secrets, build contexts and test artifacts are excluded from Git. Existing company configuration is not modified. The root Compose file now builds MyGPT2 from source so the additional tested dependency fixes are included; do not apply it to the older production database without a migration plan.
