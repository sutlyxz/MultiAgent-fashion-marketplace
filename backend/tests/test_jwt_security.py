"""Unit and Integration Tests for JWT Secret Security and Gatekeeper.

Verifies:
1. Development/Test mode defaults to fallback with UserWarning.
2. Production mode strictly rejects missing secret.
3. Production mode strictly rejects empty/whitespace secret.
4. Production mode strictly rejects insecure hardcoded default secret.
5. Production mode strictly rejects short secret (<32 chars).
6. Production mode strictly rejects weak placeholder keywords.
7. Production mode strictly rejects low-entropy repeating secrets.
8. Production mode accepts strong secret and verifies token encoding/decoding.
9. SECRET_KEY alias is accepted when JWT_SECRET is unset.
10. Conflicting JWT_SECRET and SECRET_KEY raises clear configuration error.
11. Matching JWT_SECRET and SECRET_KEY is accepted.
12. Error messages never leak the secret value or sensitive content.
"""

import os
import sys
import warnings
from pathlib import Path

import pytest
from jose import jwt

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import (
    DEFAULT_DEV_JWT_SECRET,
    Settings,
    _resolve_and_validate_jwt_secret,
)
from app.auth import create_access_token


def test_dev_mode_uses_fallback_with_warning():
    """Development environment must use dev fallback and emit UserWarning when secret is unset."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        s = Settings(environment="development", jwt_secret=None, secret_key=None)
        assert s.JWT_SECRET == DEFAULT_DEV_JWT_SECRET
        assert len(w) >= 1
        assert any("Using development fallback JWT secret" in str(item.message) for item in w)


def test_test_mode_uses_fallback_with_warning():
    """Test environment must also use dev fallback when secret is unset."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        s = Settings(environment="test", jwt_secret=None, secret_key=None)
        assert s.JWT_SECRET == DEFAULT_DEV_JWT_SECRET


def test_prod_mode_rejects_missing_secret():
    """Production must strictly reject missing JWT_SECRET with RuntimeError."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(environment="production", jwt_secret=None, secret_key=None)
    assert "CRITICAL: Production environment cannot start without a secure JWT_SECRET" in str(exc_info.value)


def test_prod_mode_rejects_empty_or_whitespace_secret():
    """Production must strictly reject empty or whitespace-only secret."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(environment="production", jwt_secret="   ", secret_key=None)
    assert "CRITICAL: Production environment cannot start without a secure JWT_SECRET" in str(exc_info.value)


def test_prod_mode_rejects_hardcoded_default_secret():
    """Production must strictly reject the insecure legacy default secret."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            environment="production",
            jwt_secret=DEFAULT_DEV_JWT_SECRET,
            secret_key=None,
        )
    assert "CRITICAL: Production environment cannot start using the insecure default JWT_SECRET" in str(exc_info.value)


def test_prod_mode_rejects_short_secret():
    """Production must strictly reject secrets shorter than 32 characters."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(
            environment="production",
            jwt_secret="short-key-less-than-32-chars",
            secret_key=None,
        )
    assert "must be at least 32 characters long" in str(exc_info.value)


def test_prod_mode_rejects_weak_keywords():
    """Production must reject secrets containing weak placeholder words."""
    weak_candidates = [
        "my-super-secret-production-token-1234567890",
        "changeme-immediately-in-production-now-9999",
        "default-marketplace-key-for-clothify-system",
        "this-is-an-admin-password-key-for-our-app-00",
    ]
    for weak_key in weak_candidates:
        with pytest.raises(RuntimeError) as exc_info:
            Settings(environment="production", jwt_secret=weak_key, secret_key=None)
        err = str(exc_info.value)
        assert "must not contain known weak placeholders" in err
        # Ensure secret itself is never leaked into the error message
        assert weak_key not in err


def test_prod_mode_rejects_low_entropy_secret():
    """Production must reject secrets with insufficient character variety."""
    low_entropy = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    with pytest.raises(RuntimeError) as exc_info:
        Settings(environment="production", jwt_secret=low_entropy, secret_key=None)
    err = str(exc_info.value)
    assert "insufficient character entropy" in err
    assert low_entropy not in err


def test_prod_mode_accepts_strong_secret():
    """Production must accept high-entropy, strong secrets >= 32 characters."""
    strong_key = "k9#mP$2vL8!zQ5*wE7@rT1^yU4&iO6(p]"
    s = Settings(environment="production", jwt_secret=strong_key, secret_key=None)
    assert s.JWT_SECRET == strong_key
    assert s.ENVIRONMENT == "production"

    # Verify that JWT can be minted and verified with this secret
    token = jwt.encode({"sub": "admin@clothify.com"}, s.JWT_SECRET, algorithm=s.JWT_ALGORITHM)
    decoded = jwt.decode(token, strong_key, algorithms=[s.JWT_ALGORITHM])
    assert decoded["sub"] == "admin@clothify.com"


def test_secret_key_alias_accepted_when_jwt_secret_unset():
    """SECRET_KEY should serve as fallback alias when JWT_SECRET is unset."""
    custom_alias = "alias-custom-dev-secret-123"
    s = Settings(environment="development", jwt_secret=None, secret_key=custom_alias)
    assert s.JWT_SECRET == custom_alias


def test_matching_jwt_secret_and_secret_key_accepted():
    """When both JWT_SECRET and SECRET_KEY are provided and match, accept without error."""
    val = "consistent-secret-value-12345"
    s = Settings(environment="development", jwt_secret=val, secret_key=val)
    assert s.JWT_SECRET == val


def test_conflicting_jwt_secret_and_secret_key_raises_error():
    """When both JWT_SECRET and SECRET_KEY are provided with conflicting values, reject."""
    with pytest.raises(ValueError) as exc_info:
        Settings(
            environment="development",
            jwt_secret="secret-version-one",
            secret_key="secret-version-two",
        )
    assert "Ambiguous configuration: both JWT_SECRET and SECRET_KEY are set with conflicting values" in str(exc_info.value)


def test_error_messages_do_not_leak_secret_value():
    """Error messages must never contain the sensitive secret content."""
    dummy_secret = "my-secret-with-password-word-inside-32chars"
    with pytest.raises(RuntimeError) as exc_info:
        Settings(environment="production", jwt_secret=dummy_secret, secret_key=None)
    err_text = str(exc_info.value)
    assert dummy_secret not in err_text
