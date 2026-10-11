# MyGPT2 handoff to the BeOne Mac

Prepared 2026-10-11. This is a development handoff, not a production migration.

## Code and context

Repository: https://github.com/mcbuckeye/LibreChat
Branch: codex/upgrade-librechat-v0.8.8 (customized upstream v0.8.8).
Open the cloned folder as a local Codex project. Read this document,
MYGPT2-CHROME-ACCEPTANCE.md, MYGPT2-CODE-INTERPRETER.md,
MYGPT2-UPGRADE.md and MYGPT2-UPGRADE-TESTS.md before continuing.

Current changes include BeOne branding/Terms, DOCX allowlists, the official
interpreter integration and rollback switch, and direct OpenAI model specs:
GPT-6 Luna, GPT-6.1 Sol and GPT-6 Astra, explicitly using Responses API.
All three passed real Chrome code-interpreter smoke tests. Azure endpoints
remain configured. New-model file search and vision are not exhaustively tested.

SSO initializes and the existing Entra app accepts the localhost callback.
Personal-Mac login stopped at Entra error 530003, device Unregistered, before
an authorization code returned. On the managed BeOne Mac, complete Microsoft
sign-in/MFA yourself, then verify callback, role restriction, user provisioning,
logout and absence of duplicate accounts. The company role restriction remains.

## Fresh local checkout

Install company-approved Codex desktop/CLI, Git, Node 24 and Docker Desktop.
Install Azure CLI through the company-approved method as well. Authenticate GitHub, Azure CLI and Codex separately on this Mac; browser SSO does not automatically sign the CLI into Azure. Use az login and confirm the intended subscription with az account show. Same-account Codex login
does not transfer browser sessions, private runtime files or Docker volumes.

```sh
mkdir -p ~/Development
cd ~/Development
git clone --branch codex/upgrade-librechat-v0.8.8 https://github.com/mcbuckeye/LibreChat.git MyGPT2
cd MyGPT2
npm ci
```

This intentionally starts with a fresh development database and test files.
The old Mac and its Docker volumes remain available. Do not run down -v.
If preserving old local chats is later desired, back up and restore database,
file volumes and matching encryption settings together; Git is not a data backup.

## Private configuration transfer

A private runtime archive is prepared separately on the source Mac, outside
tracked Git files, under .mygpt-local/beone-transfer/private-runtime.tar.gz.
It contains runtime.env, secrets.json, official-interpreter.yml and
interpreter-mode. It contains credentials and signing material: transfer through
an approved secure channel, never GitHub, a chat upload, or a public link.
It does not contain Docker volumes, private SSH keys or browser sessions.

The archive's interpreter overlay is adapted for an SSH tunnel; the source Mac's
active overlay is unchanged. Copy the archive to the new clone's .mygpt-local,
then extract from the repository root:

```sh
mkdir -p .mygpt-local
chmod 700 .mygpt-local
tar -xzf .mygpt-local/private-runtime.tar.gz
chmod 600 .mygpt-local/runtime.env .mygpt-local/secrets.json .mygpt-local/official-interpreter.yml .mygpt-local/interpreter-mode
```

Do not run initialization until these files are restored. start.sh now preserves
existing runtime.env and the selected interpreter overlay. Fresh initialization
without the archive deliberately defaults to local email login and custom mode.

## Interpreter without Tailscale on the BeOne Mac

The official interpreter already runs on pchomelab as the separate mygpt2-codeapi
Compose project. Do not recreate it or expose its API publicly for this handoff.
The developer Mac needs SSH access to a hostname/IP reachable without Tailscale.
Its address, forwarded SSH port and authorized login must be confirmed first.
Do not guess a public IP or change router/firewall settings automatically.

Set up approved SSH access on the BeOne Mac and verify the host key through a
trusted source. Do not copy a private SSH key from the personal Mac; use your
approved existing key or provision a new authorized key deliberately.

In a terminal, keep this running (replace the example with the confirmed host):

```sh
./scripts/mygpt2/interpreter-tunnel.sh steve@REACHABLE_SSH_HOST 22
```

This binds only 127.0.0.1:33114 on the Mac. SSH forwards to the interpreter's
existing interface on pchomelab, 100.68.21.112:33114. The server can reach its own
interface even though the client has no Tailscale. JWT authentication stays
mandatory. No homelab Compose, network binding or other service is changed.
The transferred overlay uses http://host.docker.internal:33114/v1 so the MyGPT2
Docker container can access the Mac tunnel. Closing SSH disconnects interpreter
access; start a new tunnel before using Run Code again.

## Start and validate

With the tunnel running in a separate terminal:

```sh
.mygpt-local/start.sh
docker compose -p mygpt2-upgrade -f .mygpt-local/compose.yml -f .mygpt-local/official-interpreter.yml ps
./scripts/mygpt2/interpreter.sh status
docker compose -p mygpt2-upgrade -f .mygpt-local/compose.yml -f .mygpt-local/official-interpreter.yml exec -T api node -e "fetch(process.env.LIBRECHAT_CODE_BASEURL+'/health').then(r=>{console.log(r.status);process.exit(r.ok?0:1)}).catch(()=>process.exit(1))"
```

Open http://localhost:3081 in the company browser. Complete Microsoft SSO,
then test an Azure chat, direct OpenAI chat and real Run Code call. Verify DOCX
upload/file search and a generated-file download. Install/enable Codex browser
control on the BeOne Mac for actual browser testing there. Local test accounts
from the old Mac are not present in the fresh database; do not put test passwords
in this repository. Keep an approved fallback email account for local development.

Custom interpreter rollback source and images remain on the old Mac. The custom
rollback command is usable on the BeOne Mac only after that backend is separately
provisioned there; host.docker.internal:8084 will not point back to the old Mac.

## Continuing the Codex conversation

For native handoff, pair the Macs using the app's Connections settings and save
a project for this same Git repository on the destination. Choose the destination
in the current chat's run-location menu and Hand off. The destination must appear
as a connected host; signing into the same account alone is not sufficient.
Browser access must be configured on the destination as well. This source chat
cannot hand itself off through its own handoff tool.

If pairing is unavailable, start a local chat in the new project with:

> Continue the MyGPT2 upgrade from MYGPT2-HANDOFF.md and the acceptance reports.
> First verify the private configuration, direct SSH interpreter tunnel and SSO
> on this managed Mac. Preserve the older production MyGPT and interpreter rollback.
> Do not migrate production users or data yet.

## Remaining work

SSO end-to-end testing; direct SSH network reachability from the managed Mac;
new-model acceptance beyond smoke tests; first-read file staging bug; attachment
limit discrepancies; custom-reporting accuracy; unavailable provider credentials;
production-specific Compose/TLS/pinning and backup/rollback rehearsal. Read the
acceptance report for the detailed evidence. Do not label the whole upgrade as
production-ready based on these passing smoke tests.


## Handoff preparation checks

Eight focused Node tests passed for private-runtime preservation, persistent
keys, build-context exclusion, official/custom mode selection, missing-overlay
failure and SSH argument/loopback handling. Real build-context preparation
preserved the active runtime byte-for-byte. Archive contents and the adapted
interpreter endpoint were verified. Secret checks found none of the checked
private runtime values or local test password in staged files or the outgoing
branch diff. The private archive is ignored and mode 0600.

A read-only SSH attempt over the old Mac's current Tailscale route required a
new Tailscale authorization check and was canceled; no end-to-end direct SSH
validation is claimed. The remote hostname/port and BeOne network reachability
remain to be supplied. No homelab service or router setting was changed.

Required npm run lighthouse passed on isolated localhost:3098 with a fresh
production build and Chrome. Three-run medians: LCP 3697ms,
CLS 0.0169, TBT 49ms; all budgets passed.
