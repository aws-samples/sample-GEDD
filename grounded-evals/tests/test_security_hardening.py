"""Security hardening: fail-closed guest mode, exact unauthenticated paths, AgentCore placeholder, admin fallback."""

import pytest

import grounded_evals.app as gedd_app
from grounded_evals.agentcore_client import agentcore_configured, agentcore_env


class TestBindSafety:
    @pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
    def test_loopback_without_auth_is_allowed(self, host):
        gedd_app.check_bind_safety(host, auth_configured=False, allow_guest=False)

    @pytest.mark.parametrize("host", ["0.0.0.0", "::", "10.0.0.5"])
    def test_non_loopback_without_auth_refuses_to_start(self, host):
        with pytest.raises(SystemExit, match="without authentication"):
            gedd_app.check_bind_safety(host, auth_configured=False, allow_guest=False)

    def test_non_loopback_with_auth_is_allowed(self):
        gedd_app.check_bind_safety("0.0.0.0", auth_configured=True, allow_guest=False)

    def test_explicit_guest_opt_in_is_allowed(self):
        gedd_app.check_bind_safety("0.0.0.0", auth_configured=False, allow_guest=True)


class TestUnrestrictedPaths:
    @pytest.mark.parametrize("path", ["/login", "/auth/callback", "/favicon.ico", "/health", "/_nicegui/3.19.0/static/x.js"])
    def test_open_paths(self, path):
        assert gedd_app.is_unrestricted_path(path)

    @pytest.mark.parametrize("path", ["/loginX", "/login/../coach", "/healthz", "/health/admin", "/_niceguix", "/", "/coach"])
    def test_lookalike_and_app_paths_require_auth(self, path):
        assert not gedd_app.is_unrestricted_path(path)


class TestAgentCorePlaceholder:
    @pytest.mark.parametrize("value", ["", "PLACEHOLDER", "placeholder", "  PLACEHOLDER  ", "None"])
    def test_placeholder_values_are_unset(self, monkeypatch, value):
        monkeypatch.setenv("AGENTCORE_AGENT_ID", value)
        monkeypatch.delenv("AGENTCORE_AGENT_ARN", raising=False)
        assert agentcore_env("AGENTCORE_AGENT_ID") == ""
        assert not agentcore_configured()

    def test_real_id_is_configured(self, monkeypatch):
        monkeypatch.setenv("AGENTCORE_AGENT_ID", "gedd_coach-AbC123")
        assert agentcore_env("AGENTCORE_AGENT_ID") == "gedd_coach-AbC123"
        assert agentcore_configured()


class TestAdminPasswordFallback:
    def test_admin_password_used_only_without_cognito(self, monkeypatch):
        monkeypatch.setattr(gedd_app, "COGNITO_USER_POOL_ID", "")
        monkeypatch.setattr(gedd_app, "COGNITO_CLIENT_ID", "")
        monkeypatch.setattr(gedd_app, "ADMIN_PASSWORD", "s3cret-value")
        assert gedd_app._cognito_auth("anyone@example.com", "s3cret-value")
        assert not gedd_app._cognito_auth("anyone@example.com", "wrong")
        assert not gedd_app._cognito_auth("anyone@example.com", "")

    def test_no_admin_password_means_no_password_login(self, monkeypatch):
        monkeypatch.setattr(gedd_app, "COGNITO_USER_POOL_ID", "")
        monkeypatch.setattr(gedd_app, "COGNITO_CLIENT_ID", "")
        monkeypatch.setattr(gedd_app, "ADMIN_PASSWORD", "")
        assert not gedd_app._cognito_auth("anyone@example.com", "")

    def test_cognito_rejection_does_not_fall_back_to_admin_password(self, monkeypatch):
        monkeypatch.setattr(gedd_app, "COGNITO_USER_POOL_ID", "us-east-1_pool")
        monkeypatch.setattr(gedd_app, "COGNITO_CLIENT_ID", "client")
        monkeypatch.setattr(gedd_app, "ADMIN_PASSWORD", "s3cret-value")

        class NotAuthorizedError(Exception):
            pass

        class UserNotFoundError(Exception):
            pass

        class FakeClient:
            class exceptions:  # noqa: N801 (mirrors boto3's client.exceptions attribute)
                NotAuthorizedException = NotAuthorizedError
                UserNotFoundException = UserNotFoundError

            def initiate_auth(self, **_):
                raise NotAuthorizedError()

        import boto3

        monkeypatch.setattr(boto3, "client", lambda *a, **k: FakeClient())
        assert not gedd_app._cognito_auth("anyone@example.com", "s3cret-value")
