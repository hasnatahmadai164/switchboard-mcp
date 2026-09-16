"""
Central place for MCP scope constants.

Stage 2 has exactly one scope: broad "call any tool" access, since no real
tools exist yet beyond the health-check `ping`/`whoami`. Once actual tools
land (Postgres, Pinecone, Google integrations), this file grows into
per-capability scopes (e.g. "postgres:read", "gmail:send") so a token can
be minted with only the access a given caller actually needs, instead of
one all-or-nothing scope.
"""

MCP_INVOKE = "mcp:invoke"
