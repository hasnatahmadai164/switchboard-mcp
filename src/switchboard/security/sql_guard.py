"""
Defense-in-depth for the Postgres tools' SQL path.

This is deliberately a SECOND line of defense, not the first: the real
guarantee against SQL injection is that every query is parameterized
(never string-built), and the read path additionally runs under a
Postgres role that has no write grants to begin with (see
db/init/03-create-roles.sh). This module exists to catch a different
mistake -- SQL that is syntactically valid, fully parameterized, and
still doing something it has no business doing, like a SELECT with a
second statement stacked onto it via a semicolon.

Uses `sqlparse` for real statement parsing rather than regex/keyword
matching against raw SQL text, which is exactly the kind of naive check
that's easy to bypass with comments, whitespace, or case changes.
"""

import sqlparse
from sqlparse.sql import Statement


class SQLGuardError(ValueError):
    """Raised when a query fails the SQL guard's safety checks."""


def _parse_single_statement(sql: str) -> Statement:
    statements = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True) is not None]
    if len(statements) != 1:
        raise SQLGuardError(
            f"Expected exactly one SQL statement, got {len(statements)}. "
            "Stacked/batched statements are not allowed."
        )
    return statements[0]


def assert_read_only(sql: str) -> None:
    """Raises SQLGuardError unless `sql` is a single SELECT (or WITH ...) statement."""
    statement = _parse_single_statement(sql)
    keyword = statement.token_first(skip_cm=True).value.upper()
    if keyword not in ("SELECT", "WITH"):
        raise SQLGuardError(
            f"query_database only accepts SELECT statements, got '{keyword}'. "
            "Use execute_write for data-modifying statements."
        )


def assert_write_statement(sql: str) -> None:
    """Raises SQLGuardError unless `sql` is a single INSERT/UPDATE/DELETE statement.

    Deliberately excludes DDL (DROP/ALTER/TRUNCATE/CREATE) even though the
    write role could technically be granted DDL rights -- least privilege
    applies to what this tool permits, not just what the database role
    permits. Schema changes are out of scope for execute_write entirely.
    """
    statement = _parse_single_statement(sql)
    keyword = statement.token_first(skip_cm=True).value.upper()
    if keyword not in ("INSERT", "UPDATE", "DELETE"):
        raise SQLGuardError(
            f"execute_write only accepts INSERT, UPDATE, or DELETE statements, got '{keyword}'."
        )
