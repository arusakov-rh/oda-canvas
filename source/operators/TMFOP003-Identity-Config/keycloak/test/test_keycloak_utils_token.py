"""Unit tests for Keycloak Admin API token acquisition."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from keycloakUtils import Keycloak  # noqa: E402


@pytest.fixture
def kc():
    return Keycloak("http://keycloak.example:8080")


@patch("keycloakUtils.requests.post")
def test_get_token_password(mock_post, kc):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "pwd-token"},
        raise_for_status=lambda: None,
    )
    token = kc.get_token("password", "admin", "adpass")
    assert token == "pwd-token"
    args, kwargs = mock_post.call_args
    assert args[0].endswith("/realms/master/protocol/openid-connect/token")
    assert kwargs["data"]["grant_type"] == "password"
    assert kwargs["data"]["client_id"] == "admin-cli"


@patch("keycloakUtils.requests.post")
def test_get_token_client_credentials(mock_post, kc):
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "sa-token"},
        raise_for_status=lambda: None,
    )
    token = kc.get_token(
        "clientCredentials", "canvas-idop", "s3cret", "master"
    )
    assert token == "sa-token"
    _args, kwargs = mock_post.call_args
    assert kwargs["data"]["grant_type"] == "client_credentials"
    assert kwargs["data"]["client_id"] == "canvas-idop"
    assert kwargs["data"]["client_secret"] == "s3cret"
