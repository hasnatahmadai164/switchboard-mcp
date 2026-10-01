# Switchboard

A production-grade remote MCP (Model Context Protocol) server exposing five business-tool integrations — Postgres, Pinecone, Google Sheets, Gmail, and Google Calendar — as a single, reusable service. Standalone and general-purpose, not built for any one company.

## What makes this different from a typical MCP tutorial server

- **Remote, over Streamable HTTP** — not a local stdio script.
- **OAuth 2.1 protects it.** The server is a pure resource server, validating bearer tokens issued by a real external identity provider (Auth0). It never handles login or issues tokens itself.
- **Stateless auth.** Access tokens are JWTs, validated locally against the identity provider's public JWKS — no server-side session store needed.
- **Every tool carries real MCP annotations** (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`), so a calling agent can reason about risk before invoking anything.
- **Tools are curated, higher-level operations** — not raw 1:1 wraps of each API's endpoints.
- **MCP Resources and Prompts are both implemented** — the two primitives most toy servers skip entirely.
- **Defense in depth on the SQL path**: parameterized queries, least-privilege database roles, and an independent statement-shape guard — three layers, not one.
- **A real pytest suite and CI**, not just a linter.
- **A real LangGraph client** proving the server works end to end with an actual agentic task.

See [`docs/architecture.md`](docs/architecture.md) for the full design, including a request-flow diagram, and [`docs/requirements.md`](docs/requirements.md) for the complete functional and non-functional requirements this was built against.

## Tools

| Integration | Tools |
|---|---|
| Postgres | `query_database`, `list_tables`, `describe_table`, `execute_write` |
| Pinecone | `list_indexes`, `semantic_search`, `upsert_documents`, `delete_vectors` |
| Google Sheets | `read_range`, `list_sheets`, `append_row`, `update_range` |
| Gmail | `search_emails`, `read_email`, `create_draft`, `send_email` |
| Google Calendar | `list_events`, `check_availability`, `create_event` |

Plus `ping` and `whoami` for connectivity and auth verification.

**Resources:** `switchboard://postgres/schema` (live DB schema), `switchboard://calendar/upcoming` (next 7 days of events).

**Prompts:** `draft_follow_up_email`, `summarize_week_events`.

## Running this project

No cloud deployment — this stops at a working local Docker Compose setup, built with production-grade methodology throughout (real OAuth, real security posture, real tests) even though it never leaves your machine.

### 1. Clone and configure

```powershell
git clone <this repo>
cd switchboard-mcp
Copy-Item .env.example .env
```

Fill in `.env` — see `.env.example` for what each variable is and where to get it. You'll need:
- An **Auth0** tenant (API + Machine-to-Machine application) — see `docs/architecture.md` for the auth model.
- Postgres credentials of your own choosing (the server provisions these roles itself on first boot — see `db/init/`).
- A **Pinecone** API key.
- Google OAuth credentials, minted once via `python scripts/google_oauth_setup.py` (see that script's docstring).

### 2. Run it

```powershell
docker compose up --build
```

This brings up the server alongside a local Postgres container seeded with demo data.

### 3. Test it

```powershell
pip install -e .
pip install -r requirements-dev.txt
pytest tests/ -v
```

For manually exercising the running server, `scripts/call-tool.ps1` wraps the MCP Inspector CLI:

```powershell
$env:SWITCHBOARD_TOKEN = "..."  # see scripts/ for how to mint one
.\scripts\call-tool.ps1 -ToolName list_tables
```

### 4. Run the real agent

```powershell
cd client
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # fill it in
python agent.py
```

This runs a real LangGraph agent against the live server — checking calendar availability, drafting a follow-up email, and logging the outcome to a Google Sheet.

## Security posture

- Postgres: parameterized queries only, enforced in code; the read path runs under a database role with no write permissions; a SQL statement-shape guard is a third, independent layer.
- Every tool output is treated as untrusted content before it re-enters a calling agent's context.
- Least-privilege credentials per integration — no single credential has broad access across every tool.

## CI

GitHub Actions runs linting (`ruff`), the pytest suite, an import-cleanliness check against the real entrypoint, and a Docker build check on every push.

## Repo structure

```
switchboard-mcp/
├── src/switchboard/
│   ├── server.py              # entry point; registers every tool/resource/prompt
│   ├── auth/                  # Auth0 token validation, scopes
│   ├── core/                  # config, lifespan (connection pools), Google credentials
│   ├── tools/                 # one module per integration
│   ├── resources/
│   ├── prompts/
│   └── security/              # SQL guard
├── client/                    # LangGraph agent, proves the server end to end
├── db/init/                   # schema, seed data, role provisioning
├── tests/
├── scripts/                   # setup and manual-testing helpers
├── docs/
└── .github/workflows/ci.yml
```

## License

MIT — see `LICENSE`.
