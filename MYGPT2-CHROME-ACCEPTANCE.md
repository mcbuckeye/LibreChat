# MyGPT2 Chrome acceptance testing — 2026-10-10 / 2026-10-11

Acceptance run completed for the accessible configured workflows. Scope: test configured development functionality through Google
Chrome, excluding SSO. Production MyGPT and its data are outside this run.
Synthetic test content only. Existing chats, files and account credentials
must be preserved. No claim that every configuration or input combination is
covered. UI control checks are distinguished from complete workflows.

App: http://localhost:3081. Browser: actual Google Chrome, Codex extension.
Running About diagnostics: v0.8.8, commit 2699f59,
branch codex/upgrade-librechat-v0.8.8. Repository head includes later deployment
documentation/scripts at 752d2a209. Official interpreter: validated base image;
experimental extra-language image is not deployed.

| Area | Status | Evidence / limitation |
|---|---|---|
| Local login | Pass | Steve signed in successfully from Chrome; logout/re-login passed; required-field validation for login/registration passed |
| Azure gpt-4o-mini chat | Pass | Actual response: cobalt-731 and 17×23=391 |
| Conversation context | Pass | Follow-up retained cobalt-731 |
| Markdown / math rendering | Pass | Rendered table and math; model initially fenced the table, corrected on request |
| Settings sections | UI pass | General, Chat, Speech, Langfuse, Data & Privacy, Account, About open |
| Theme selection | UI pass | Dark → Light → restored System |
| Chat preference toggles | UI pass | 26 switches changed and restored; not 26 end-to-end feature passes |
| Settings search | Pass | Search draft finds Save drafts locally |
| Additional chat controls | Partial | Edited prompt rerun returned 247, regeneration and sibling branches work; visible-message fork preserved history; positive feedback saved. System clipboard copy/paste verified with native Chrome on Oct11; earlier virtual-clipboard limitation resolved. Stop cancelled a real 25-second sandbox execution: active executions fell from 1 to 0, no leftover workspaces; next execution returned CHROME_AFTER_STOP_OK391 |
| Chat organization | Partial | Rename, pin/unpin, archive/filter/unarchive, bookmark create/edit/filter, project create/edit/new-chat/sort/remove passed; message search found edited prompt; title sorting changed grouping; duplicate preserved all four messages at a new URL across reload; moved duplicate into QA project |
| Import/export/share | Partial | JSON, Markdown, text, CSV and PNG export files created (5565/566/611/714/126008 bytes). Shared chat rendered with User replacing name; restricting Everyone access saved; signed-out restricted link redirects to login. Oct11 native import succeeded, separate new conversation preserved original; rendered prompt/answer and sibling branch verified. Malformed JSON rejected |
| Presets/prompts | Pass | Saved/applied Azure preset; created/edited prompt, slash picker found it and executed edited text; response PROMPT_LIBRARY_OK |
| Model/provider selection | Partial / external failure | All 9 listed OpenAI models and both Azure OpenAI models returned correct answers. DeepSeek-R1 returns HTTP 400 unknown_model; direct configured-provider calls with both configured/reported casing fail too |
| Uploads/code/files/artifacts | Partial | Scientific Python total31, SciPy1.18.1, chart/XLSX creation, rendered XLSX values7/11/13 and 5335-byte Chrome download passed. Node/Bun/TypeScript returned391 after correcting model-generated invalid Bun commands. Existing CSV attachment read actual R7/S11 (total18), reused generated XLSX total31. Oct11 native uploads and actual contents passed for CSV, JSON, TXT, XLSX, PDF; PNG upload/vision passed. DOCX initially rejected, now enabled and verified by the Oct11 DOCX fix below. Read File fails before first Bash staging; cumulative six-file turn rejected despite agent UI limit10 (details below) |
| File Search/RAG | Pass with citation limitation | Actual tool retrieved search-check.txt verification cobalt-742 and source excerpt. Answer displayed raw [ref:tool0turn0] instead of an inline citation chip |
| Agents/marketplace/tools | Partial | Private agent creation/edit, model/tools selection, v1 restore and return to v2, marketplace search/category empty state/pin, and actual Calculator tool result 56088 passed. Python/Bash/Node/Bun/TypeScript executed; intentional Python error reported, recovery worked. HTML artifact counter incremented to2; code/preview switching worked. Fullscreen entered and exited with native input on Oct11; full artifact view visually verified |
| Reporting | Fail: counts; backend routes and Chrome UI pass | All five authenticated routes200, anonymous401. Report counts transactions as Messages, omits generated files without createdAt. Oct11 native Basic authentication succeeded; usage/metrics screens, ten chart canvases, date filters and theme worked; no reporting console errors captured |
| Session/persistence/responsiveness | Partial | Project draft survives reload. Temporary chat has isTemporary=true and 30-day expiredAt; not immediate database deletion. Logout and login passed; registration/login empty submission validation passed without account creation. Restarted only mygpt2-upgrade-api-1: healthy, saved22-message agent history restored, code returned CHROME_AFTER_RESTART_OK391, indexed search found prompt/stdout. Oct11 native DevTools390×844: body width390, sidebar open/close, message submission and391 response passed; device emulation and DevTools closed afterward |
| Permissions/admin | UI pass | Admin settings remote-agent API role USER switches are disabled; no credentials created or permissions expanded. Thirteen private API routes denied anonymous requests401; public config contains BeOne Medicines and no configured provider/encryption/JWT secret values |
| Memory | Partial / configuration gap | Manual create/edit/filter works; fresh Azure chat returned MEMORY_UNAVAILABLE. YAML has no memory configuration or agent memory capability; storage UI is not proof of model use |
| Model parameters | Pass | Custom name/instructions, temperature 0.2, output limit 128 and non-streaming returned PARAM_OK and 42; restored original values |
| File management | UI pass | Filter final-upload finds XLSX+PNG; image preview opens; existing files preserved |
| Langfuse | Blocked | Settings explicitly Not configured |
| Speech hardware | Blocked / UI only | Browser engines and voice selection visible; Read aloud clicked but no playback state confirmed; recording and audible output not verified; no microphone permission granted |
| Destructive account/global-data actions | Excluded from execution | Preserve existing account and chats; inspect controls only |
| Email workflows | Blocked unless local sink exists | Do not send test email to real recipients |
| SSO | Excluded | User explicitly excluded unconfigured SSO |
| OpenAI image generation/editing | Pass with model/UI caveat | Actual generation1024×1024 and edit blue→green worked; preview visually confirmed. Initial model chose unsupported256×256 and provider rejected it. Failed tool calls nevertheless show “Image created” |
| Gemini image generation | Blocked: authentication | Actual tool failed initialization: no usable key/service-account authentication available |
| MCP | UI pass / unconfigured | Empty list, Add MCP dialog and required-field validation tested; no server configured, no trust/access granted |
| DALL-E-3 | Unconfigured | Selecting tool opens a required OpenAI API Key dialog; no key entered or tool added |
| Search/external tools | Unconfigured | Native Web Search needs a provider. Google Search, Tavily, Traversaal, Wolfram, weather and other key-dependent tools have no usable configured credentials/services; not claimed operational |
| Schedules / beta features | Disabled | Schedules, skills and stateful-workspace beta features are not enabled; Handoffs UI inspected with zero configured destinations, beta orchestration not executed |
| External feedback/support links | Inspection only | Link targets inspected; no email or feedback sent. Footer retains askit@beigene.com and existing corporate SharePoint hostname; ownership/redirects not verified |

Generated screenshots, synthetic fixtures, downloads and logs are kept outside
Git in `.mygpt-local/chrome-acceptance/`.

## Findings requiring follow-up

1. **Reporting compatibility (production blocker):** at the frozen snapshot the
   CSV reported272 Messages and5 Files. MongoDB had97 saved non-temporary
   messages and27 file records. The code counts token-ledger transactions as
   messages and matches file createdAt dates, excluding22 records with missing
   createdAt. Clarify metric semantics and fix/test generated-file coverage
   before using these reports for production usage or billing decisions.
2. **DeepSeek-R1 deployment/configuration:** configured Azure calls return400
   unknown_model, including direct provider requests; this is not an interpreter
   failure. Keep model unavailable until its deployed endpoint is corrected.
3. **Memory configuration:** manual storage works, but neither the global memory
   configuration nor agent memory capability is enabled. Do not promise agents
   will remember saved memory.
4. **Image tool error presentation:** failed OpenAI/Gemini calls display an
   “Image created” label. Response text correctly reports failure; label is
   misleading. OpenAI generation/editing itself passed with supported dimensions.
5. **Model tool reliability:** initial Bun execution used invalid heredoc syntax;
   explicit corrected commands passed. The model also initially chose an
   unsupported image size. Tool-call output must remain visible for diagnosis.
6. **Cross-tab storage parsing:** Chrome logged two Unexpected end of JSON input
   errors around logout. Deployed hooks bundle3447:1731 maps to
   useLocalStorageAlt storage-event handler, which parses an empty string when
   a tracked key disappears. Core login/chat recovery passed; fix this
   multi-tab edge case with focused verification.
7. **RAG citation rendering:** tool source/excerpt worked, but one response
   displayed the raw reference token instead of a citation chip.

## Explicit coverage limits

During the Oct10 run, extension file selection was blocked and native fallback
was blocked by the locked Mac. After the user unlocked it, Oct11 native file
pickers completed uploads, the import round trip and malformed/unsupported/
oversized-file validation. Extension file permissions were not broadened.
Download metadata confirmed files exist; protected Downloads reads were blocked,
so exported-file contents were not independently parsed. Existing-file attachment,
actual sandbox input, XLSX preview/download and RAG were tested successfully.

Reporting backend routes and Chrome reporting screens were authenticated
privately. Native system clipboard, artifact fullscreen and390×844 mobile
checks passed on Oct11. Actual speech hardware remains unverified. No permissions were broadened to overcome these limits.

No SSO, password reset email, 2FA enrollment, API-key creation, role expansion,
account deletion, purge-all-chats, or real-recipient notifications were executed.
No production migration/load/availability test is implied. Temporary chats use a
30-day expiry field; retention expiration was not waited out. Only representative
artifact types and configured models were exercised, not every MIME type or
provider-parameter combination. Synthetic QA chats, agents, prompts, memory and
project remain for review; no agent was published globally. Custom interpreter
rollback remains available; the official stable interpreter stays selected.

## Evidence and final state

- Main actual Chrome agent chat: http://localhost:3081/c/3722e1a0-915d-5488-a555-2189ea093b4b
- Original project QA chat: http://localhost:3081/c/ac29d68c-f003-5c9a-830c-33993bc4e757
- Duplicate moved to project: http://localhost:3081/c/7d1f6ad0-d74b-4341-971b-c4d77d7b8ae9
- Ignored evidence directory: `.mygpt-local/chrome-acceptance/`, including
  workbook-chrome.png, image-edit-chrome.png, model-results.json,
  export-files.json, anonymous-api-checks.json, report-api-results.json and
  chrome-console-errors.json. Evidence includes synthetic local test account
  data and is deliberately not committed as a public artifact.
- MyGPT2 app healthy after restart, Steve session restored, viewport override
  reset, original app3080 unaffected. Official stable interpreter remains
  selected; custom rollback service remains healthy.

This run changes test records and this report, not application source. Reported
failures/configuration gaps have not been silently repaired or marked passed.

## Native Chrome follow-up — 2026-10-11

The user unlocked the Mac. No extension file access or microphone permission
was enabled. Native Chrome controls resolved the earlier picker/auth/clipboard/
fullscreen/mobile automation limits.

| Check | Result |
|---|---|
| CSV native upload → official interpreter | Actual Alpha7/Beta11/Gamma13, total31; initial model delimiter mistake auto-corrected |
| JSON/TXT multi-file upload → interpreter | Actual JSON_ORCHID_218, values total31; actual violet-936 and420 fictional credits |
| XLSX native upload → interpreter | openpyxl read Sheet One/Second Sheet and real nonempty cells; initial model failed with other tools, explicit Python succeeded |
| PDF native upload → sandbox and RAG | Actual File Search marker PDF_LIME_527; pypdf absent, installed PyPDF2 extracted real text successfully; no package installation |
| PNG native upload → fresh Azure vision chat | Model read actual visible marker; filename contained no answer |
| Size/type validation | 51MiB CSV rejected at50MB limit; plain synthetic .exe rejected as application/x-msdownload; no execution attempted |
| JSON export/import round trip | New conversation decb81b9-4c03-4c03-9b2d-ca9ad28d1408; preserved original; cobalt-731/391 and edited247 branch render; previous/next sibling works |
| Malformed JSON import | Error notification; no success claim |
| System clipboard | Copied rendered CSV answer, native Cmd-V into composer matched; cleared without sending |
| Reporting UI | Native Basic auth; usage/metrics tables/charts render, previous-month zero-usage filter, All Time navigation, dark/light toggle restored |
| Mobile390×844 | No horizontal overflow; native sidebar open/close and actual391 response; restored1728×836 desktop |
| Artifact fullscreen | Native click entered full artifact view with Exit full screen control; visually confirmed, exited cleanly |

### New findings from real native uploads

- **First-read attachment staging failure:** reproducible in a fresh single-file
  chat14734c65-7123-5e7a-868d-5a00655b5c4d. Read File on the newly uploaded
  `/mnt/data/read-first.txt` fails “No such file or directory”; subsequent Bash
  `cat` prints the actual uploaded contents; Read File then succeeds on that
  same path. Earlier JSON/TXT first-read failures follow the same pattern.
  Fix first-use attachment provisioning for the Read File tool, then retest the
  sequence without a Bash workaround. Evidence: first-read-chrome.txt/png.
- **Attachment-limit mismatch / cumulative context:** in chat
  253e046c-4c45-56ab-ab5e-54874d86fcc8, attachments added over separate turns
  reached six and the next request was rejected “6 > 5.” The agent frontend
  allows10 while the underlying Azure provider configuration has limit5.
  The error suggests removing attachments, but previously sent attachments
  have no equivalent composer removal control. Reconcile effective limits and
  communicate the cumulative context behavior; fresh one-file chat worked.
- **DOCX configuration gap (resolved by subsequent user-requested fix below):** the repository sample.docx is a harmless public
  fixture; native upload rejected its official DOCX MIME. Current agent
  supportedMimeTypes includes XLSX/PDF but not DOCX. No allowlist was changed.
- **Model/parser distinction:** PyPDF2/openpyxl worked. Missing pypdf and an
  initially incorrect spreadsheet strategy were visible model errors, not
  proof that PDFs/XLSX cannot be processed.

New screenshots: mobile-native-chrome.png, reporting-native-chrome.png and
first-read-chrome.png. Synthetic PDF fixture and preview stay in the ignored
local evidence directory. Reporting count errors, earlier external-provider and
memory configuration gaps, citation rendering and cross-tab parsing findings
remain unresolved. No production changes or source fixes were made in this
follow-up. Stable official interpreter and custom rollback are preserved.

## DOCX enabled — 2026-10-11

At the user's request, added the official DOCX MIME type
`application/vnd.openxmlformats-officedocument.wordprocessingml.document`
to all four endpoint allowlists in librechat.yaml: agents, openAI, azureOpenAI
and custom. Restarted only mygpt2-upgrade-api-1; healthy afterward.
Configuration schema validation passed. Existing limits were preserved.

Actual Chrome native upload of the public sample.docx succeeded. The official
interpreter read its actual word/document.xml and printed the expected sentence;
File Search independently retrieved that sentence from the ingested DOCX with
75% relevance. Chrome conversation33b7538b-06e1-5cbe-894d-ba8c87a4e864 contains
both real tool outputs. Evidence: docx-chrome.txt and docx-chrome.png.

This resolves the DOCX allowlist finding. First-read provisioning and attachment
limit discrepancies remain separate unresolved issues. Production was not changed.

Required Lighthouse verification passed on disposable port3098 after avoiding
occupied3080. Production frontend build succeeded. Three-run medians: LCP3735ms
(limit4500), CLS0.0169 (limit0.1), TBT50.45ms (limit500); seeded transcript
assertion passed. No running app was reused for this test.

## Entra localhost redirect check — 2026-10-11

At the user’s request, sent an authorization-code request using the existing
Microsoft Entra client ID, with callback http://localhost:3081/oauth/openid/callback
and prompt=none. No client secret, username or password was transmitted. Entra
returned login_required/AADSTS50058 to the local callback, demonstrating that
the existing registration accepts it. A deliberate different callback path
kept the error on Entra instead of redirecting, confirming the validation
control. Normal interactive authorization displayed the company sign-in page;
no sign-in was completed. Microsoft ignores localhost port differences, so
this test does not establish which port was originally entered in the portal.

Full SSO, client-secret validity, claims and role mapping remain untested. Local
SSO was disabled at the time of this check. Evidence: sso-redirect-check.json in the ignored directory.


## Local SSO enabled — 2026-10-11

Enabled OpenID only in the isolated MyGPT2 Docker API at localhost:3081,
reusing the existing confidential Entra application configuration from the
original ignored .env. Generated a separate local session secret. Email login
remains enabled, automatic SSO redirect is disabled, and the existing required
company role is preserved. No Entra registration or production settings changed.

Recreated only the upgrade API using both the base Compose file and official
interpreter overlay. Container is healthy; startup reports OpenID Connect
configured successfully. Actual Chrome logout showed the Microsoft SSO button;
clicking it reached the company-branded Microsoft sign-in page through the
application's own authorization flow. User sign-in/MFA is pending, so token
exchange, secret validity, role validation and an authenticated chat session
are not yet verified. OpenID's source applies the required-role check before
creating a new local SSO user; generic social-registration settings do not gate
this OpenID-specific creation path.

Evidence in ignored .mygpt-local/chrome-acceptance: sso-local-login.png and
sso-microsoft-handoff.png. Private env backup: runtime.env.before-local-sso.
To roll back this local setup, restore that backup to runtime.env and recreate
only api with the same two Compose files (including official-interpreter.yml).
The backup and runtime credentials remain ignored by Git and mode 0600.


## SSO device-policy blocker — 2026-10-11

After the user entered company Microsoft credentials, Entra kept the flow on
its device-setup page. Read-only More details inspection reports error 530003,
application MyGPT2, platform macOS, device identifier unavailable and device
state Unregistered (sign-in timestamp 2026-10-11T14:49:48.482Z). No callback or
token exchange success has been observed. This blocks end-to-end SSO validation
at the identity provider before LibreChat receives the authorization code.

No device enrollment, company Conditional Access policy change, diagnostic
flagging or new permission grant was performed. Next step is to have IT review
the sign-in event and device requirements, or use the company's supported
managed-device browser configuration. Local email login remains available.


## Direct OpenAI models — 2026-10-11

At the user's request, reused the existing ignored MyGPT2 runtime OpenAI key
(no new key created and no secret changed). Added three tracked model specs
under OpenAI: GPT-6 Luna · Fast (low reasoning), GPT-6.1 Sol · Balanced
(medium), and GPT-6 Astra · Deep analysis (medium). All explicitly use Responses
API, with Run Code and File Search enabled. No hard/default override was set.
Existing Azure endpoints, older model entries, SSO and official interpreter
configuration are preserved. Only the isolated upgrade API was recreated.

Added model IDs to ignored runtime.env OPENAI_MODELS for agent-builder selection.
For server deployment, add gpt-6-luna,gpt-6.1-sol,gpt-6-astra to that server's
OPENAI_MODELS and configure its approved OPENAI_API_KEY privately. The named
model specs are in librechat.yaml; choose these named entries to apply the
Responses API and reasoning defaults. Local rollback env backup is
.mygpt-local/runtime.env.before-openai-models (ignored, mode 0600).

Validation: config schema accepted all specs without dropping preset fields;
API container healthy; git diff --check passed. Live direct model access and
Responses API requests passed for all three. Actual signed-in Chrome chats
then invoked the official interpreter and returned real stdout: Luna 385
(sum of squares 1..10), Sol 3628800 (10 factorial), Astra 5050 (sum 0..100).
These are smoke tests, not an exhaustive new-model acceptance suite; new-model
File Search, vision and generated-file behavior remain to be separately tested.
Screenshots: openai-model-menu.png, openai-luna.png, openai-sol.png and
openai-astra.png in the ignored chrome-acceptance evidence directory.
Production was not changed; Anthropic and Chinese models were not added.

Required npm run lighthouse completed successfully on disposable localhost:3098
with Chrome and a fresh production build. One test passed, with three-run
medians LCP 3723ms (limit 4500), CLS 0.0169 (limit 0.1), and TBT 50ms
(limit 500). This harness validates baseline startup/message performance;
new-model provider behavior is evidenced by the separate live Chrome tests.
