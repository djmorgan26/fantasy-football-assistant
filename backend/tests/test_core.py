"""Core utilities: JWT, password hashing, encryption, config."""
import re
from datetime import timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.core.config import settings
from app.utils.encryption import ESPNCredentialManager, encrypt_data, decrypt_data


pytestmark = pytest.mark.unit


class TestPasswords:
    def test_hash_roundtrip(self):
        hashed = get_password_hash("s3cret-password")
        assert hashed != "s3cret-password"
        assert verify_password("s3cret-password", hashed)
        assert not verify_password("wrong", hashed)

    def test_hashes_are_salted(self):
        assert get_password_hash("same") != get_password_hash("same")


class TestTokens:
    def test_create_and_verify(self):
        token = create_access_token({"sub": "42"})
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert "exp" in payload

    def test_expired_token_rejected(self):
        token = create_access_token({"sub": "42"}, expires_delta=timedelta(minutes=-1))
        assert verify_token(token) is None

    def test_garbage_token_rejected(self):
        assert verify_token("not-a-jwt") is None

    def test_token_signed_with_other_key_rejected(self):
        from jose import jwt

        token = jwt.encode({"sub": "42"}, "some-other-secret", algorithm="HS256")
        assert verify_token(token) is None


class TestEncryption:
    def test_roundtrip(self):
        encrypted = encrypt_data("hello world")
        assert encrypted != "hello world"
        assert decrypt_data(encrypted) == "hello world"

    def test_decrypt_garbage_returns_none(self):
        assert decrypt_data("garbage-not-encrypted") is None

    def test_espn_credential_manager_roundtrip(self):
        s2 = ESPNCredentialManager.encrypt_espn_s2("the-espn-s2-cookie")
        swid = ESPNCredentialManager.encrypt_espn_swid("{SWID-VALUE}")
        assert ESPNCredentialManager.decrypt_espn_s2(s2) == "the-espn-s2-cookie"
        assert ESPNCredentialManager.decrypt_espn_swid(swid) == "{SWID-VALUE}"


class TestConfig:
    def test_effective_database_url_in_mock_mode(self):
        original = settings.mock_mode
        try:
            settings.mock_mode = True
            assert settings.effective_database_url == settings.mock_database_url
            settings.mock_mode = False
            assert settings.effective_database_url == settings.database_url
        finally:
            settings.mock_mode = original


class TestAdditiveSchemaBridge:
    """Every migration column must also be in `ensure_additive_schema`.

    Production's schema was created by `create_all` and has no Alembic history
    (see NEXT_SESSION.md), so `alembic upgrade` never runs there. `create_all`
    creates missing *tables* but never alters existing ones, which means a new
    column reaches production only through the additive bridge in `main.py`.

    Getting this wrong is not a degraded feature. SQLAlchemy names every column
    in its SELECT, so one missing column on `leagues` turns every league query
    into a 500. This test derives the requirement from the migrations
    themselves rather than restating a list that would drift.
    """

    ADD_COLUMN = re.compile(
        r"""op\.add_column\(\s*["'](?P<table>\w+)["']\s*,\s*sa\.Column\(\s*["'](?P<column>\w+)["']""",
        re.VERBOSE,
    )

    def _migration_columns(self) -> set:
        versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
        found = set()
        for path in versions.glob("*.py"):
            # The baseline creates tables outright, so `create_all` covers it.
            if path.name.startswith("0001"):
                continue
            for match in self.ADD_COLUMN.finditer(path.read_text()):
                found.add((match.group("table"), match.group("column")))
        return found

    def _bridge_columns(self) -> set:
        source = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text()
        pattern = re.compile(
            r"ALTER TABLE (?P<table>\w+) ADD COLUMN IF NOT EXISTS (?P<column>\w+)"
        )
        return {(m.group("table"), m.group("column")) for m in pattern.finditer(source)}

    def test_every_migration_column_is_bridged(self):
        missing = self._migration_columns() - self._bridge_columns()
        assert not missing, (
            "These columns are added by a migration but not by "
            "ensure_additive_schema, so production (which has no Alembic "
            f"history) would 500 on any query naming them: {sorted(missing)}"
        )

    def test_bridge_has_no_columns_the_models_dropped(self):
        """A stale ALTER would recreate a column nothing reads."""
        from app.db.database import Base

        known = {
            (table.name, column.name)
            for table in Base.metadata.sorted_tables
            for column in table.columns
        }
        stale = {
            (table, column)
            for table, column in self._bridge_columns()
            if (table, column) not in known
        }
        assert not stale, f"bridge adds columns no model defines: {sorted(stale)}"
