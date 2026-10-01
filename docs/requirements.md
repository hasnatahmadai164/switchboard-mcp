# Requirements

This document describes what Switchboard was built to do, and the constraints it was built under. Written last, once the system existed to describe accurately.

## Purpose

Switchboard is a standalone, general-purpose remote MCP (Model Context Protocol) server. It exposes five business-tool integrations — Postgres, Pinecone, Google Sheets, Gmail, and Google Calendar — as a single reusable service, built to hold up to real scrutiny on security and correctness rather than as a tutorial demonstration.

## Functional requirements

### MCP protocol surface

- Remote server over Streamable HTTP (MCP spec 2025-06-18), not local stdio.
- OAuth 2.1 authorization: the server is a pure resource server, validating bearer tokens issued by an external identity provider (Auth0). It never issues tokens or handles login itself.
- Every tool carries MCP annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) so a calling agent can reason about risk before invoking anything.
- Beyond tools, the server exposes MCP Resources (ambient, read-only context) and MCP Prompts (reusable message templates) — the two primitives most tutorial servers skip.

### Tool integrations

| Integration | Tools | Notes |
|---|---|---|
| Postgres | `query_database`, `list_tables`, `describe_table`, `execute_write` | Read path runs under a database role with no write grants; `execute_write` is a separate, clearly annotated destructive path |
| Pinecone | `list_indexes`, `semantic_search`, `upsert_documents`, `delete_vectors` | Text in, text out — embedding happens server-side via Pinecone's hosted model, not a separate provider |
| Google Sheets | `read_range`, `list_sheets`, `append_row`, `update_range` | One dedicated demo Google account, not per-caller delegation |
| Gmail | `search_emails`, `read_email`, `create_draft`, `send_email` | `create_draft` is the safer default; `send_email` is the only tool in the server with irreversible real-world side effects |
| Google Calendar | `list_events`, `check_availability`, `create_event` | `check_availability` is deliberately higher-level than a raw event dump |

### Resources

- Live Postgres schema (`switchboard://postgres/schema`)
- Upcoming calendar events, next 7 days (`switchboard://calendar/upcoming`)

### Prompts

- `draft_follow_up_email(recipient_name, topic)`
- `summarize_week_events()` — pulls real calendar data into the template rather than returning a generic instruction

### Client

- A LangGraph agent (`client/`) using `langchain-mcp-adapters`, exercising a real subset of tools (`check_availability`, `create_draft`, `append_row`) against a real task, to prove the server works end to end. Not a second flagship build.

## Non-functional requirements

### Security

- SQL: parameterized queries only, enforced in code; the read path additionally runs under a least-privilege Postgres role; a statement-shape guard (`sql_guard.py`) rejects stacked statements and wrong-type SQL as a third, independent layer.
- Credentials: least-privilege, scoped per integration. No single credential has broad access across every tool. The app process never holds the Postgres admin superuser credentials, only its own two scoped roles.
- Every tool output is treated as untrusted content before it re-enters a calling agent's context (the current MCP threat model — indirect prompt injection via tool outputs).
- Two independent auth layers, not conflated: MCP-level auth (who can call this server) via Auth0/OAuth 2.1, and backend integration credentials (how the server talks to Postgres/Pinecone/Google), which never overlap.

### Testing and CI

- Automated pytest suite covering the security-critical and easy-to-silently-break logic: the SQL guard, the Auth0 token verifier (with real RS256 signature verification against a locally-generated test keypair, not mocked-away crypto), and `Settings`' computed properties.
- GitHub Actions CI: lint (`ruff`), the pytest suite, an import-cleanliness check that exercises the real production entrypoint, and a Docker build check.
- CI never holds real credentials — every external-service setting is a dummy value, present only so `Settings()` can construct.

### Deployment scope

- No cloud deployment. The project stops at a working local Docker Compose setup — `docker-compose` brings up the MCP server alongside a local Postgres container with seeded demo data.
- OAuth is still delegated to a real external identity provider (Auth0) even though the server itself runs locally.
- Pinecone is used via its hosted free tier over the network, same as any deployment.

### Spec and dependency choices

- Built against MCP spec **2025-06-18** (Streamable HTTP + OAuth 2.1 authorization) — the stable, widely-supported baseline — deliberately not the 2026-07-28 release candidate, whose SDK support was still maturing at build time.
- `mcp` SDK pinned to the v1.x line throughout (`mcp[cli]==1.12.0` for the server) even after the SDK's v2.x line was released, for the same reliability reason.
- Dependency versions are pinned exactly, not left as open ranges — several were corrected mid-build after actually installing and running them turned up real conflicts (see `architecture.md`'s "Lessons from the build").

## Explicit non-goals

- Full per-end-user Google OAuth delegation. A real pattern in multi-tenant products, but a second OAuth flow layered on top of the existing Auth0 layer for no real benefit at this project's scale.
- A polished, general-purpose LangGraph client. `client/` exists to prove the server works, not to be a product of its own.
- Production deployment, horizontal scaling, or a managed Postgres/session store. The code is written so it wouldn't break if one were swapped in later, but none of that is in scope here.
