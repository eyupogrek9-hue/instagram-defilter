# backend/tests/test_api.py
import base64
import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np


def make_image_bytes() -> bytes:
    array = np.full((64, 64, 3), 128, dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(array).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_defilter_success(client):
    with (
        patch("main.get_image_from_url", return_value=(make_image_bytes(), "https://cdn.ig.com/test.jpg", False)),
        patch("main.get_claude_corrections", return_value={"brightness": 0.05}),
    ):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/ABC123/"})
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://cdn.ig.com/test.jpg"
    assert data["processed_image"]  # non-empty base64 string
    assert data["claude_pass_applied"] is True


def test_defilter_invalid_url(client):
    with patch("main.get_image_from_url", side_effect=ValueError("bad url")):
        response = client.post("/defilter", json={"url": "https://example.com"})
    assert response.status_code == 400


def test_defilter_private_post(client):
    with patch("main.get_image_from_url", side_effect=PermissionError("private")):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/PRIV/"})
    assert response.status_code == 403


def test_defilter_post_not_found(client):
    with patch("main.get_image_from_url", side_effect=FileNotFoundError("gone")):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/GONE/"})
    assert response.status_code == 404


def test_defilter_rate_limited(client):
    with patch("main.get_image_from_url", side_effect=RuntimeError("Rate limited")):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/RL/"})
    assert response.status_code == 429


def test_defilter_claude_failure_degrades_gracefully(client):
    with (
        patch("main.get_image_from_url", return_value=(make_image_bytes(), "https://cdn.ig.com/test.jpg", False)),
        patch("main.get_claude_corrections", side_effect=Exception("API down")),
    ):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/ABC123/"})
    assert response.status_code == 200
    assert response.json()["claude_pass_applied"] is False
