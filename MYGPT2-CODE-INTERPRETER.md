# MyGPT2 code interpreter and rollback

MyGPT2 at http://localhost:3081 uses the official interpreter on pchomelab
through Tailscale, with KVM isolation and JWT authentication. The maintained
source is `/Users/stephenmclaughlin/Development/mygpt2-code-interpreter`, branch
`codex/mygpt2-official-interpreter`, based on official v1.10.4. Its
`MYGPT2-DEPLOYMENT.md` documents deployment, fixes, and tests.

From this upgraded LibreChat checkout:

```sh
./scripts/mygpt2/interpreter.sh status
./scripts/mygpt2/interpreter.sh custom   # rollback to the existing port 8084 interpreter
./scripts/mygpt2/interpreter.sh official # return to the official Linux interpreter
```

The private `.mygpt-local/official-interpreter.yml` supplies the endpoint and JWT
signing settings. The custom settings remain in `.mygpt-local/runtime.env`.
The script recreates only MyGPT2's API and checks `/health`. Official preflight
runs inside Docker. A failed recreation or health check restores the previous
mode. Existing custom interpreter containers, images, source, and storage are
preserved. Changes to the original port 3080 instance are not needed.

Stop active chats before switching and begin a fresh chat afterward. Historical
chat text remains available, but generated/uploaded file references are specific
to their interpreter backend. Switching does not migrate those files. Keep both
backends' volumes. An outage of Tailscale or pchomelab needs an explicit rollback.
Do not start MyGPT2 with only the base Compose file when intending official mode:
that deliberately restores the custom interpreter.
