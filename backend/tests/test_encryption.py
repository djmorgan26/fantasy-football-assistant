"""
ESPN credential encryption.

These cookies are what let the app read somebody's private league, so the
properties worth pinning are: a round trip returns exactly what went in,
ciphertext never resembles the plaintext, tampering fails closed rather than
returning garbage, and a key change makes old ciphertext unreadable instead of
silently wrong.
"""
import pytest

from app.core.config import settings
from app.utils.encryption import (
    ESPNCredentialManager,
    decrypt_data,
    encrypt_data,
)

pytestmark = pytest.mark.unit

# Shaped like the real thing: ESPN's s2 cookie is a long URL-safe blob.
S2 = "AEB%2FVsomethinglongandopaque%2Fwithslashes%2Bandplus"
SWID = "{1A2B3C4D-5E6F-7890-ABCD-EF1234567890}"


class TestRoundTrip:
    @pytest.mark.parametrize("value", [S2, SWID, "simple", "unicode: café ✅", "x" * 4000])
    def test_what_goes_in_comes_back(self, value):
        assert decrypt_data(encrypt_data(value)) == value

    def test_ciphertext_does_not_contain_the_plaintext(self):
        assert S2 not in encrypt_data(S2)

    def test_the_same_input_encrypts_differently_each_time(self):
        """Fernet includes a timestamp and IV, so ciphertext is not a fingerprint."""
        assert encrypt_data(S2) != encrypt_data(S2)


class TestEmptyAndMissing:
    def test_empty_input_encrypts_to_empty(self):
        assert encrypt_data("") == ""

    def test_empty_input_decrypts_to_none(self):
        """None, not "" — the caller checks truthiness to decide if a cookie exists."""
        assert decrypt_data("") is None

    def test_none_decrypts_to_none(self):
        assert decrypt_data(None) is None


class TestTampering:
    def test_garbage_fails_closed(self):
        assert decrypt_data("not-actually-ciphertext") is None

    def test_a_flipped_byte_fails_closed(self):
        token = encrypt_data(S2)
        tampered = ("A" if token[0] != "A" else "B") + token[1:]
        assert decrypt_data(tampered) is None

    def test_truncation_fails_closed(self):
        assert decrypt_data(encrypt_data(S2)[:-10]) is None

    def test_a_different_secret_key_cannot_read_it(self, monkeypatch):
        """Rotating SECRET_KEY must invalidate old credentials, not misread them."""
        token = encrypt_data(S2)
        monkeypatch.setattr(settings, "secret_key", "a-completely-different-secret-key")
        assert decrypt_data(token) is None


class TestCredentialManager:
    def test_s2_round_trip(self):
        assert ESPNCredentialManager.decrypt_espn_s2(
            ESPNCredentialManager.encrypt_espn_s2(S2)
        ) == S2

    def test_swid_round_trip(self):
        assert ESPNCredentialManager.decrypt_espn_swid(
            ESPNCredentialManager.encrypt_espn_swid(SWID)
        ) == SWID

    def test_no_stored_credentials_means_no_cookies(self):
        user = type("U", (), {"espn_s2_encrypted": None, "espn_swid_encrypted": None})()
        assert ESPNCredentialManager.get_espn_cookies_for_user(user) is None

    def test_both_cookies_are_returned_under_the_names_espn_expects(self):
        user = type("U", (), {
            "espn_s2_encrypted": ESPNCredentialManager.encrypt_espn_s2(S2),
            "espn_swid_encrypted": ESPNCredentialManager.encrypt_espn_swid(SWID),
        })()

        cookies = ESPNCredentialManager.get_espn_cookies_for_user(user)
        assert cookies == {"espn_s2": S2, "SWID": SWID}

    def test_one_stored_cookie_still_yields_a_usable_dict(self):
        user = type("U", (), {
            "espn_s2_encrypted": ESPNCredentialManager.encrypt_espn_s2(S2),
            "espn_swid_encrypted": None,
        })()
        assert ESPNCredentialManager.get_espn_cookies_for_user(user) == {"espn_s2": S2}

    def test_unreadable_stored_credentials_yield_none_not_a_broken_dict(self):
        """Corrupt rows must not produce cookies ESPN will reject confusingly."""
        user = type("U", (), {
            "espn_s2_encrypted": "corrupted",
            "espn_swid_encrypted": "also-corrupted",
        })()
        assert ESPNCredentialManager.get_espn_cookies_for_user(user) is None
