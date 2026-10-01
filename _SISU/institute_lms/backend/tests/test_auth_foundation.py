import os

os.environ.setdefault("SESSION_SECRET", "test-session-secret-that-is-longer-than-32-characters")

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.sessions import decrypt_tokens, digest, encrypt_tokens


def test_session_tokens_are_encrypted_and_round_trip():
    get_settings.cache_clear()
    encrypted = encrypt_tokens("access-value", "refresh-value")
    assert "access-value" not in encrypted
    assert "refresh-value" not in encrypted
    assert decrypt_tokens(encrypted) == ("access-value", "refresh-value")


def test_digest_is_stable_and_does_not_reveal_session_id():
    value = "opaque-browser-session"
    assert digest(value) == digest(value)
    assert value not in digest(value)


def test_health_does_not_claim_database_connectivity():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert "configured" in response.json()


def test_protected_api_rejects_missing_cookie():
    response = TestClient(app).get("/api/courses")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_mutation_rejects_missing_cookie():
    response = TestClient(app).post("/api/courses", json={
        "title": "Course", "description": "", "institution_id": "00000000-0000-0000-0000-000000000000"
    })
    assert response.status_code == 401
