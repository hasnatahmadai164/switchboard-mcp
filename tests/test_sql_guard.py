"""
Unit tests for the SQL guard -- the app-level second line of defense
behind parameterized queries and least-privilege database roles (see
security/sql_guard.py's own docstring for the full threat-model
reasoning). Pure logic, no database needed, so these run fast and
without any external dependency.
"""

import pytest

from switchboard.security.sql_guard import (
    SQLGuardError,
    assert_read_only,
    assert_write_statement,
)


class TestAssertReadOnly:
    def test_accepts_select(self):
        assert_read_only("SELECT * FROM customers")

    def test_accepts_select_with_where(self):
        assert_read_only("SELECT id, name FROM customers WHERE id = $1")

    def test_accepts_with_cte(self):
        assert_read_only("WITH recent AS (SELECT * FROM orders) SELECT * FROM recent")

    def test_rejects_insert(self):
        with pytest.raises(SQLGuardError):
            assert_read_only("INSERT INTO customers (name) VALUES ('x')")

    def test_rejects_update(self):
        with pytest.raises(SQLGuardError):
            assert_read_only("UPDATE customers SET name = 'x'")

    def test_rejects_delete(self):
        with pytest.raises(SQLGuardError):
            assert_read_only("DELETE FROM customers")

    def test_rejects_drop(self):
        with pytest.raises(SQLGuardError):
            assert_read_only("DROP TABLE customers")

    def test_rejects_stacked_statements(self):
        with pytest.raises(SQLGuardError):
            assert_read_only("SELECT 1; DROP TABLE customers")

    def test_rejects_stacked_statements_no_space(self):
        with pytest.raises(SQLGuardError):
            assert_read_only("SELECT * FROM customers;DELETE FROM customers")

    def test_trailing_semicolon_alone_is_fine(self):
        # A single trailing semicolon after one real statement should
        # NOT be treated as a second, empty statement.
        assert_read_only("SELECT * FROM customers;")


class TestAssertWriteStatement:
    def test_accepts_insert(self):
        assert_write_statement("INSERT INTO customers (name) VALUES ($1)")

    def test_accepts_update(self):
        assert_write_statement("UPDATE customers SET name = $1 WHERE id = $2")

    def test_accepts_delete(self):
        assert_write_statement("DELETE FROM customers WHERE id = $1")

    def test_rejects_select(self):
        with pytest.raises(SQLGuardError):
            assert_write_statement("SELECT * FROM customers")

    def test_rejects_drop(self):
        with pytest.raises(SQLGuardError):
            assert_write_statement("DROP TABLE customers")

    def test_rejects_truncate(self):
        with pytest.raises(SQLGuardError):
            assert_write_statement("TRUNCATE customers")

    def test_rejects_stacked_statements(self):
        with pytest.raises(SQLGuardError):
            assert_write_statement("INSERT INTO customers (name) VALUES ('x'); DROP TABLE customers")
