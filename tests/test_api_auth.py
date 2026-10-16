"""
Unit tests for API endpoints authentication and subscriber workflows.
Verifies fail-closed security on notify-subscribers and unsubscribe endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def test_notify_subscribers_fails_closed_when_token_unset(monkeypatch):
    """Ensure endpoint rejects access with 401 when NOTIFY_SECRET_TOKEN is None or empty."""
    monkeypatch.delenv("NOTIFY_SECRET_TOKEN", raising=False)
    
    payload = {
        "date": "2026-10-16",
        "published_at": "2026-10-16T08:00:00Z",
        "briefs": []
    }
    
    # Even if client passes any token, it MUST fail closed (401)
    response = client.post("/api/notify-subscribers?token=any_token", json=payload)
    assert response.status_code == 401
    assert "Invalid or unconfigured notification authorization token" in response.json()["detail"]


def test_notify_subscribers_fails_closed_when_token_mismatched(monkeypatch):
    """Ensure endpoint rejects access with 401 when token doesn't match NOTIFY_SECRET_TOKEN."""
    monkeypatch.setenv("NOTIFY_SECRET_TOKEN", "super_secret_xyz_123")
    
    payload = {
        "date": "2026-10-16",
        "published_at": "2026-10-16T08:00:00Z",
        "briefs": []
    }
    
    # Wrong token
    response = client.post("/api/notify-subscribers?token=wrong_token", json=payload)
    assert response.status_code == 401
    assert "Invalid or unconfigured notification authorization token" in response.json()["detail"]
    
    # Missing token query param
    response = client.post("/api/notify-subscribers", json=payload)
    assert response.status_code == 401


def test_unsubscribe_nonexistent_email():
    """Verify nonexistent email returns 404 Not Found."""
    response = client.post("/api/unsubscribe", json={"email": "nonexistent_99999@testdaily.dev"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
