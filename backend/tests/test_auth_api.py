"""Unit tests for Authentication API and get_current_user dependency connected to PostgreSQL / SQLAlchemy.

All tests use FastAPI TestClient and an isolated SQLite in-memory database
by overriding the `get_db` dependency. No live or dev database is touched.
"""

from datetime import datetime, timezone
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.auth import get_current_seller, hash_password
from app.db_connection import Base, get_db
from app.main import app
from app.models import User


@pytest.fixture
def test_db_session():
    """Create an isolated SQLite in-memory database and populate test seed data."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    now = datetime.now(timezone.utc)
    # Seed a test seller and a test buyer
    seller = User(
        id="user-seller-1",
        email="existing_seller@fashion.com",
        password_hash=hash_password("Secret123!"),
        role="seller",
        created_at=now,
        updated_at=now,
    )
    buyer = User(
        id="user-buyer-1",
        email="existing_buyer@fashion.com",
        password_hash=hash_password("Secret123!"),
        role="buyer",
        created_at=now,
        updated_at=now,
    )
    session.add_all([seller, buyer])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(test_db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def _override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_register_success(client, test_db_session):
    """1. Successful registration saves user to database."""
    payload = {
        "email": "newuser@fashion.com",
        "password": "Password123!",
        "role": "buyer",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["email"] == "newuser@fashion.com"
    assert data["role"] == "buyer"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data

    # Verify user exists in DB
    db_user = test_db_session.get(User, data["id"])
    assert db_user is not None
    assert db_user.email == "newuser@fashion.com"


def test_register_duplicate_email_rejected(client):
    """2. Registering with an existing email returns 400 error."""
    payload = {
        "email": "existing_buyer@fashion.com",
        "password": "Password123!",
        "role": "buyer",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert res.json() == {"detail": "Email already registered"}


def test_login_success(client):
    """3. Login with correct credentials returns JWT token."""
    payload = {
        "email": "existing_seller@fashion.com",
        "password": "Secret123!",
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "existing_seller@fashion.com"
    assert data["user"]["role"] == "seller"


def test_login_incorrect_password(client):
    """4. Login with incorrect password returns 401 error."""
    payload = {
        "email": "existing_seller@fashion.com",
        "password": "WrongPassword!",
    }
    res = client.post("/api/auth/login", json=payload)
    assert res.status_code == 401
    assert res.json() == {"detail": "Incorrect email or password"}


def test_get_me_success(client):
    """5. /api/auth/me with valid Bearer token returns user info."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": "existing_buyer@fashion.com", "password": "Secret123!"},
    )
    token = login_res.json()["access_token"]

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["email"] == "existing_buyer@fashion.com"
    assert data["role"] == "buyer"


def test_get_me_invalid_or_expired_token(client):
    """6. /api/auth/me rejects invalid token with 401."""
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
    assert res.status_code == 401
    assert res.json() == {"detail": "Could not validate credentials"}


def test_token_user_not_found(client, test_db_session):
    """7. Token referencing a deleted/non-existent user returns 401."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": "existing_buyer@fashion.com", "password": "Secret123!"},
    )
    token = login_res.json()["access_token"]

    # Delete user from DB
    buyer = test_db_session.get(User, "user-buyer-1")
    test_db_session.delete(buyer)
    test_db_session.commit()

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert res.json() == {"detail": "Could not validate credentials"}


def test_password_not_exposed_in_response(client):
    """8. Registration and login responses do not expose password or password_hash."""
    reg_res = client.post(
        "/api/auth/register",
        json={"email": "secret_test@fashion.com", "password": "Pass", "role": "buyer"},
    )
    reg_data = reg_res.json()
    assert "password" not in reg_data
    assert "password_hash" not in reg_data

    login_res = client.post(
        "/api/auth/login",
        json={"email": "secret_test@fashion.com", "password": "Pass"},
    )
    login_user_data = login_res.json()["user"]
    assert "password" not in login_user_data
    assert "password_hash" not in login_user_data


def test_auth_does_not_depend_on_in_memory_db(client, monkeypatch):
    """9. Authentication operates on DB even if in-memory db.users is cleared."""
    from app.database import db

    monkeypatch.setattr(db, "users", [])

    login_res = client.post(
        "/api/auth/login",
        json={"email": "existing_seller@fashion.com", "password": "Secret123!"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["email"] == "existing_seller@fashion.com"


def test_get_current_user_return_shape_compatibility(test_db_session):
    """10. get_current_user returns a dictionary compatible with existing router usage."""
    from app.auth import create_access_token, get_current_user
    from fastapi.security import HTTPAuthorizationCredentials

    token = create_access_token({"sub": "existing_seller@fashion.com"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    current_user_dict = get_current_user(credentials=creds, db=test_db_session)

    assert isinstance(current_user_dict, dict)
    assert current_user_dict["id"] == "user-seller-1"
    assert current_user_dict["email"] == "existing_seller@fashion.com"
    assert current_user_dict["role"] == "seller"

    seller_dict = get_current_seller(current_user=current_user_dict)
    assert seller_dict["role"] == "seller"


def test_register_seller_with_name_and_store_name(client, test_db_session):
    """11. Seller can register with name and store_name."""
    payload = {
        "email": "boutique_seller@fashion.com",
        "password": "Password123!",
        "role": "seller",
        "name": "Jean Dupont",
        "store_name": "Maison Dupont",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Jean Dupont"
    assert data["store_name"] == "Maison Dupont"

    db_user = test_db_session.get(User, data["id"])
    assert db_user.name == "Jean Dupont"
    assert db_user.store_name == "Maison Dupont"


def test_register_buyer_with_name_and_null_store_name(client, test_db_session):
    """12. Buyer can register with name, store_name defaults to None."""
    payload = {
        "email": "alice_buyer@fashion.com",
        "password": "Password123!",
        "role": "buyer",
        "name": "Alice Smith",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Alice Smith"
    assert data["store_name"] is None

    db_user = test_db_session.get(User, data["id"])
    assert db_user.name == "Alice Smith"
    assert db_user.store_name is None


def test_register_buyer_cannot_have_store_name(client):
    """13. Buyer registration rejects non-empty store_name with 400."""
    payload = {
        "email": "illegal_store_buyer@fashion.com",
        "password": "Password123!",
        "role": "buyer",
        "name": "Bob",
        "store_name": "Bob's Illegal Shop",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert res.json() == {"detail": "Buyers cannot have a store name"}


def test_update_profile_seller_success(client):
    """14. Authenticated seller can update name and store_name via PATCH /api/auth/me."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": "existing_seller@fashion.com", "password": "Secret123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_res = client.patch(
        "/api/auth/me",
        headers=headers,
        json={"name": "Renowned Seller", "store_name": "Haute Couture Studio"},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "Renowned Seller"
    assert data["store_name"] == "Haute Couture Studio"

    # Verify GET /api/auth/me reflects updated profile
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Renowned Seller"
    assert me_res.json()["store_name"] == "Haute Couture Studio"


def test_update_profile_buyer_cannot_set_store_name(client):
    """15. Authenticated buyer cannot set a store_name via PATCH /api/auth/me."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": "existing_buyer@fashion.com", "password": "Secret123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Updating name is allowed
    ok_res = client.patch("/api/auth/me", headers=headers, json={"name": "Buyer Name"})
    assert ok_res.status_code == 200
    assert ok_res.json()["name"] == "Buyer Name"

    # Setting store_name is rejected with 400
    fail_res = client.patch(
        "/api/auth/me", headers=headers, json={"store_name": "Disallowed Boutique"}
    )
    assert fail_res.status_code == 400
    assert fail_res.json() == {"detail": "Only sellers can set a store name"}


def test_profile_handles_null_values(client):
    """16. Profile update allows clearing fields by passing empty/null values."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": "existing_seller@fashion.com", "password": "Secret123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    update_res = client.patch(
        "/api/auth/me",
        headers=headers,
        json={"name": "", "store_name": ""},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] is None
    assert data["store_name"] is None


def test_profile_update_unauthorized_without_token(client):
    """17. Profile update requires authentication."""
    res = client.patch("/api/auth/me", json={"name": "No Auth"})
    assert res.status_code == 401


def test_register_invalid_role_rejected(client):
    """18. Registration with unauthorized role (e.g., admin) is rejected with 400."""
    payload = {
        "email": "hacker@fashion.com",
        "password": "Password123!",
        "role": "admin",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert res.json() == {"detail": "Role must be either 'buyer' or 'seller'"}


def test_profile_update_cannot_escalate_role(client, test_db_session):
    """19. Profile update mass-assignment of role is completely ignored; role remains intact."""
    login_res = client.post(
        "/api/auth/login",
        json={"email": "existing_buyer@fashion.com", "password": "Secret123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to elevate role to seller via profile update
    res = client.patch(
        "/api/auth/me",
        headers=headers,
        json={"name": "Buyer Hacker", "role": "seller"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "buyer"  # Role remained buyer!

    # Verify directly in DB
    db_user = test_db_session.get(User, "user-buyer-1")
    assert db_user.role == "buyer"


