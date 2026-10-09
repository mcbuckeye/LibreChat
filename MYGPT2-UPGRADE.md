# MyGPT2 upgrade assessment

Assessed October 9, 2026. The pinned v0.8.8 upgrade has now been integrated and tested in an isolated Docker Compose stack with fresh data. See [the implementation and test report](MYGPT2-UPGRADE-TESTS.md) for the completed work and remaining validation. Production MyGPT and its data have not been migrated. The assessment below records the original baseline and migration considerations.

## Baseline and target

- MyGPT2 application version: `v0.8.0-rc3`, based on upstream `e1ad235f1` (August 25, 2025), with our custom baseline commit `314d286f0`.
- Tested local setup, BeOne Medicines Terms, and code-tool null argument fix saved in `5d2f9934b` on `feature/mygpt-wip`.
- Upgrade branch: `codex/upgrade-librechat-v0.8.8`.
- Proposed upstream target: **v0.8.8**, published September 30, 2026 in US Eastern time (October 1 UTC). There are 2,817 commits between the upstream base and that tag, including merge commits.
- Release labeling is inconsistent: GitHub labels v0.8.8 a prerelease, while the configuration changelog calls it a stable release deployment snapshot. Use the exact numbered tag rather than floating `main` or `latest`.
- Custom Python sandbox Dockerfile saved locally as `cc8f32a` on `codex/mygpt2-python-sandbox` in the sibling interpreter repository. Its remote is the original author's repository. Other pre-existing interpreter modifications remain uncommitted; this is not a complete snapshot of that repository.
- Environment files, private certificates, generated runtime data, and existing unreviewed deployment drafts are not included in the MyGPT2 commit.

## Meaningful changes after our base

| Area | Changes | Relevance to BeOne |
| --- | --- | --- |
| Security | v0.8.4 alone reports 30+ security fixes; subsequent releases further tighten credentials, tenant boundaries, OAuth and tool authorization. | Strong reason to upgrade an internal company service. |
| Documents | Native provider uploads, local PDF/Office extraction, improved attachment routing, and inline Office/CSV artifact previews. | Better spreadsheet and document workflows; upload behavior will change. |
| Agents and tools | Handoffs, Skills, subagents, background tools, context compaction, improved Agent Builder and tool approvals. | More capable analysis workflows, with additional permissions and configuration to review. |
| Chat experience | Resumable streaming, Projects, favorites/pins, redesigned settings/navigation, context and optional cost visibility. | Better organization and fewer lost responses; users may need brief orientation. |
| Enterprise administration | Expanded role/group controls, Entra group synchronization, SSO role synchronization and a bundled admin panel. | Useful for company administration, but identity and authorization must be tested. |
| Operations | Metrics, tracing/logging, readiness and shutdown improvements, and Redis coordination for multiple replicas. | Easier support and diagnosis; tracing requires deliberate configuration of data export. |
| Code Interpreter | Official open-source interpreter now available; v0.8.8 adds highly experimental stateful workspaces requiring compatible services. | Evaluate the official service separately; retain our scientific packages and tested execution/download behavior. |

Some foundational Agent and permission features described in the aggregate v0.8.0 changelog already existed in our release-candidate base; they should not all be counted as new.

## Main migration concerns

1. **Existing MongoDB indexes:** v0.8.8 introduces tenant-scoped indexes. The explicit migration can be necessary even for single-tenant deployments. Back up the database, stop all writers, run `npm run migrate:tenant-indexes:dry-run`, then the migration, verify success, and only then restart writers. The dry run does not prove replacement indexes can be built. Rehearse using a restored database copy first.
2. **Microsoft SSO:** OpenID account matching, claims, group retrieval and role synchronization changed substantially. Test existing-account login without duplicate accounts, new-account creation, logout, group membership, and administrator access against a suitable Entra test registration. Local email login does not validate this.
3. **Interpreter compatibility:** Agents SDK changes from 2.4.76 to 4.0.0, and tool loading changed substantially. Re-evaluate our null-argument fix against the new SDK before retaining it. Test Python execution, CSV/Excel uploads, chart rendering, generated workbook downloads, repeated executions and error handling. The new workspace features are not guaranteed to work with our custom interpreter.
4. **Configuration validation:** Our YAML is version 1.2.8; the target uses 1.3.17. Translate and validate configuration against the target schema, including MIME patterns, upload limits, Azure endpoints, privacy Terms, permissions and Code settings. Malformed explicit CREDS_KEY/CREDS_IV now fail startup. Preserve valid production encryption keys; do not blindly regenerate keys used by stored credentials.
5. **Runtime and Compose:** The target Dockerfile uses Node 24.16.0 and the repository declares npm 11.13.0, versus our local Node 20 setup. Upstream Compose pins MongoDB 8.0.20 and Meilisearch 1.35.1, changes pgvector image, registry, log paths and persistent volumes, and adds an admin panel requiring a session secret. Treat these as separate infrastructure decisions, not a blind Compose replacement. Use supported database upgrade paths and test Meilisearch migration or reindexing. Keep custom builds pinned to the chosen source/tag.
6. **Custom reporting:** Revalidate Flask reports against updated transaction/user schemas and tool/subagent usage records. Check user counts, token totals, costs and dashboard authentication against known fixtures or a restored database copy. New message/tenant fields and expanded usage types may affect assumptions even where older fields remain.
7. **Scope and rollback:** Scheduling, stateful workspaces, Plugins and some APIs are beta or experimental. Keep them disabled for the first upgrade. A rollback needs pre-migration database and file backups, as well as the old source and images. Reverting Git alone is insufficient after persistent-data changes.

## Suggested execution order

1. Inventory the committed customizations and remaining deployment files; validate configuration without exposing credentials.
2. Integrate the pinned v0.8.8 source on the upgrade branch, retaining BeOne branding, Terms, reporting and interpreter integration. Resolve Compose changes deliberately.
3. Build and test a separate Compose instance with separate ports and fresh volumes, leaving the working baseline available.
4. Rehearse migration on a restored database copy; compare account, conversation and usage counts before and after.
5. Complete browser regression testing for providers, SSO, Code Interpreter, uploads/downloads, permissions, search and reporting. RAG and SSO were not exercised by the current local stack.
6. Prepare a deployment and rollback plan before changing the company service.

## Primary sources

- [GitHub releases](https://github.com/LibreChat-AI/LibreChat/releases)
- [v0.8.1](https://www.librechat.ai/changelog/v0.8.1), [v0.8.2](https://www.librechat.ai/changelog/v0.8.2), [v0.8.3](https://www.librechat.ai/changelog/v0.8.3), [v0.8.4](https://www.librechat.ai/changelog/v0.8.4), [v0.8.5](https://www.librechat.ai/changelog/v0.8.5), [v0.8.6](https://www.librechat.ai/changelog/v0.8.6), [v0.8.7](https://www.librechat.ai/changelog/v0.8.7), [v0.8.8](https://www.librechat.ai/changelog/v0.8.8)
- [Config 1.3.15](https://www.librechat.ai/changelog/config_v1.3.15), [Config 1.3.16](https://www.librechat.ai/changelog/config_v1.3.16), [Config 1.3.17](https://www.librechat.ai/changelog/config_v1.3.17)
- [Tenant index migration](https://www.librechat.ai/docs/configuration/mongodb/tenant_index_migration)
- [Official Code Interpreter](https://github.com/LibreChat-AI/code-interpreter)
- Runtime/Compose versions and source compatibility observations verified directly with `git show v0.8.8:<path>` and a diff from `e1ad235f1` to `v0.8.8`.
