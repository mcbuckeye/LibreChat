# MyGPT2 local test instance

All application services run in Docker Compose. The API image builds this checkout's source, including its frontend, using Node 20. It does not use the floating upstream LibreChat image.

Open http://localhost:3080 and use Sign up to create a local test account. Local registration is enabled and Microsoft SSO is disabled because its callback is configured for the company domain. Existing provider credentials are copied privately from the root .env, so model calls use those accounts and may incur normal charges.

This project uses separate Docker volumes for its database, search index, uploads, generated images and logs. It does not use the existing data-node directory. All published ports bind to 127.0.0.1.

Start or rebuild after source changes, from the repository root:

```sh
.mygpt-local/start.sh
```

Stop without deleting test data:

```sh
.mygpt-local/stop.sh
```

Inspect services and logs:

```sh
docker compose -p mygpt2-local -f .mygpt-local/compose.yml ps
docker compose -p mygpt2-local -f .mygpt-local/compose.yml logs -f api
```

The reporting dashboard runs at http://localhost:8082/dashboard and uses the existing Flask dashboard credentials. With the fresh database, reports initially contain no usage data.

The code interpreter runs as a separate Compose project from a sibling `code-interpreter` checkout (override its location with `CODE_INTERPRETER_PROJECT_DIR`), at http://localhost:8080. MyGPT2 connects through http://host.docker.internal:8080/v1/librechat. Python uses the customized code-interpreter-python:latest sandbox image. Other languages need their respective sandbox images built separately.

Start/rebuild the interpreter with `.mygpt-local/start-interpreter.sh`; stop it with `.mygpt-local/stop-interpreter.sh`. The local override binds its API to 127.0.0.1 and runs the service without privileged mode, while retaining the Docker socket required to create execution containers.

The initial builds encountered Docker build-time DNS failures; the helper uses `docker build --network=host` for dependency downloads. Runtime execution sandboxes retain the project's disabled-network default. The Python Dockerfile upgrades h5py, pyarrow, numexpr and bottleneck to match the newer NumPy installed by its analysis packages.

Verified from inside the MyGPT2 API container: interpreter health, Python execution with pandas, and generation/download of an Excel workbook and PNG chart. To repeat the check, run:

```sh
docker compose -p mygpt2-local -f .mygpt-local/compose.yml exec -T api node < .mygpt-local/test-interpreter.cjs
```

RAG/document-search is not included in the local stack. Microsoft SSO needs a registered localhost callback before it can be tested locally.

The selected setup scripts are tracked. Runtime configuration, generated credentials and build context are excluded from Git. The production .env and existing Compose files were not edited by this setup. Node on the Mac is used only to prepare the build context; it does not serve the application.

Browser usage: click the sliders icon beside the paperclip (Tools Options), then Code Interpreter. A purple Code Interpreter toggle appears beneath the prompt. Ask the model to execute Python; creating an Agent is optional.

Browser validation succeeded with Azure GPT-4o-mini: Python returned 6, displayed a chart, and downloaded a workbook containing 1, 2, 3. LibreChat code-tool loading now normalizes explicit null values for optional session_id/args fields; its focused tool tests pass (15 tests).
