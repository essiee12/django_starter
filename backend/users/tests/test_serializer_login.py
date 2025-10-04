from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.http import HttpRequest, HttpResponseBadRequest
from django.test import TestCase
from django.urls import NoReverseMatch
from requests.exceptions import HTTPError
from rest_framework import serializers
from rest_framework_simplejwt.settings import api_settings as jwt_settings

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.oauth2.client import OAuth2Error

from users.serializers import (
    SocialLoginInputSerializer,
    UserLoginSerializer,
    UserRefreshTokenSerializer,
)
from users.tests.factories import UserFactory


class UserLoginSerializerTests(TestCase):
    def test_token_contains_user_fields(self):
        user = UserFactory.create(is_email_verified=True)
        serializer = UserLoginSerializer()
        token = serializer.get_token(user)
        self.assertEqual(token["email"], user.email)
        self.assertEqual(token["full_name"], user.full_name)

    @patch("rest_framework_simplejwt.serializers.TokenObtainPairSerializer.validate")
    def test_validate_delegates_to_parent(self, mock_parent_validate):
        mock_parent_validate.return_value = {"refresh": "r", "access": "a"}
        serializer = UserLoginSerializer()
        result = serializer.validate({"email": "test@example.com", "password": "pwd"})
        mock_parent_validate.assert_called_once_with(
            {"email": "test@example.com", "password": "pwd"}
        )
        self.assertEqual(result, {"refresh": "r", "access": "a"})


class UserRefreshSerializerTests(TestCase):
    def test_accepts_refresh_token_string(self):
        user = UserFactory.create(is_email_verified=True)

        class DummyToken:
            def __init__(self, token):
                self._token = token
                self.payload = {jwt_settings.USER_ID_CLAIM: user.pk}
                self.access_token = "access-token"

            def __str__(self):
                return self._token

            def blacklist(self):
                return None

            def set_jti(self):
                return None

            def set_exp(self):
                return None

            def set_iat(self):
                return None

            def outstand(self):
                return None

        with patch(
            "users.serializers.UserRefreshTokenSerializer.token_class", DummyToken
        ):
            serializer = UserRefreshTokenSerializer(data={"refresh": "token"})
            self.assertTrue(serializer.is_valid(raise_exception=True))
            self.assertEqual(serializer.validated_data["access"], "access-token")


class SocialLoginInputSerializerTests(TestCase):
    @patch("users.serializers.complete_social_login", return_value=None)
    def test_validate_handles_access_token_flow(self, mock_complete_social_login):
        user = UserFactory.create(is_email_verified=True)

        login_mock = MagicMock()
        login_mock.account = MagicMock(user=user)
        login_mock.is_existing = False
        login_mock.state = {}
        login_mock.lookup = MagicMock()
        login_mock.save = MagicMock()

        adapter = MagicMock()
        adapter.provider_id = "google"
        provider = MagicMock()
        provider.app = MagicMock()
        provider.get_scope.return_value = []
        adapter.get_provider.return_value = provider
        parsed_token = MagicMock()
        adapter.parse_token.return_value = parsed_token
        adapter.complete_login.return_value = login_mock

        serializer = SocialLoginInputSerializer(
            data={"access_token": "abc123", "id_token": "id123"},
            context={"view": MagicMock(), "request": MagicMock()},
        )

        with (
            patch("users.serializers.reverse", return_value="/callback"),
            patch.object(serializer, "_get_adapter", return_value=adapter),
            patch.object(serializer, "_get_request", return_value=MagicMock()),
        ):
            result = serializer.is_valid(raise_exception=True)
            self.assertTrue(result)
            validated = serializer.validated_data
            self.assertEqual(validated["user"], user)
            mock_complete_social_login.assert_called_once()

    def test_raises_when_social_app_missing(self):
        adapter = MagicMock()
        adapter.provider_id = "github"
        adapter.get_provider.side_effect = SocialApp.DoesNotExist

        serializer = SocialLoginInputSerializer(
            data={"access_token": "token"},
            context={"view": MagicMock(), "request": MagicMock()},
        )

        with patch.object(serializer, "_get_adapter", return_value=adapter):
            with self.assertRaises(serializers.ValidationError):
                serializer.is_valid(raise_exception=True)

    def test_get_request_returns_wrapped_request(self):
        inner_request = MagicMock()
        request_wrapper = MagicMock(_request=inner_request)
        serializer = SocialLoginInputSerializer(context={"request": request_wrapper})
        self.assertEqual(serializer._get_request(), inner_request)

    def test_get_adapter_requires_view(self):
        serializer = SocialLoginInputSerializer(context={})
        with self.assertRaises(serializers.ValidationError):
            serializer._get_adapter()

    def test_get_adapter_requires_adapter_class(self):
        view = type("View", (), {})()
        serializer = SocialLoginInputSerializer(
            context={"view": view, "request": HttpRequest()}
        )
        with self.assertRaises(serializers.ValidationError):
            serializer._get_adapter()

    def test_get_adapter_invokes_adapter_class(self):
        request = HttpRequest()
        adapter_instance = MagicMock()
        view = MagicMock()
        view.adapter_class.return_value = adapter_instance
        serializer = SocialLoginInputSerializer(
            context={"view": view, "request": request}
        )

        result = serializer._get_adapter()

        self.assertEqual(result, adapter_instance)
        view.adapter_class.assert_called_once_with(request)

    def test_build_callback_url_uses_view_value(self):
        serializer = SocialLoginInputSerializer(context={"request": MagicMock()})
        view = MagicMock(callback_url="https://return.example")
        adapter_class = MagicMock()
        self.assertEqual(
            serializer._build_callback_url(view, adapter_class),
            "https://return.example",
        )

    def test_build_callback_url_raises_when_reverse_missing(self):
        serializer = SocialLoginInputSerializer(context={"request": MagicMock()})
        view = MagicMock(callback_url=None)
        adapter_class = MagicMock()
        adapter_class.provider_id = "google"
        with patch("users.serializers.reverse", side_effect=NoReverseMatch("err")):
            with self.assertRaises(serializers.ValidationError):
                serializer._build_callback_url(view, adapter_class)

    def test_validate_requires_token_or_code(self):
        serializer = SocialLoginInputSerializer(
            data={}, context={"view": MagicMock(), "request": MagicMock()}
        )
        with patch.object(serializer, "_get_adapter", return_value=MagicMock()):
            with self.assertRaises(serializers.ValidationError):
                serializer.is_valid(raise_exception=True)

    @patch.object(SocialLoginInputSerializer, "_post_signup")
    @patch("users.serializers.complete_social_login", return_value=None)
    def test_validate_code_flow(self, mock_complete, mock_post_signup):
        user = UserFactory.create(is_email_verified=True)

        login_mock = MagicMock()
        login_mock.account = MagicMock(user=user)
        login_mock.is_existing = False
        login_mock.state = {}
        login_mock.lookup = MagicMock()
        login_mock.save = MagicMock()
        login_mock.user = MagicMock(email=None)

        adapter = MagicMock()
        adapter.provider_id = "github"
        adapter.expires_in_key = "expires"
        provider = MagicMock()
        provider.app = MagicMock()
        provider.get_scope.return_value = []
        adapter.get_provider.return_value = provider
        adapter.parse_token.return_value = MagicMock(app=provider.app)
        adapter.complete_login.return_value = login_mock

        class DummyClient:
            def __init__(
                self,
                request,
                client_id,
                secret,
                method,
                url,
                callback,
                scope,
                scope_delimiter=None,
                headers=None,
                basic_auth=None,
            ):
                self.request = request

            def get_access_token(self, code):
                return {
                    "access_token": "abc",
                    "refresh_token": "def",
                    "id_token": "ghi",
                    "expires": 3600,
                }

        view = MagicMock()
        view.client_class = DummyClient
        view.adapter_class = MagicMock(return_value=adapter)
        view.callback_url = None

        serializer = SocialLoginInputSerializer(
            data={"code": "auth-code"},
            context={"view": view, "request": MagicMock(_request=MagicMock())},
        )

        with patch.object(
            SocialLoginInputSerializer, "_build_callback_url", return_value="/callback"
        ):
            self.assertTrue(serializer.is_valid(raise_exception=True))
            self.assertEqual(serializer.validated_data["user"], user)
            mock_complete.assert_called_once()
            mock_post_signup.assert_called_once()

    def test_validate_code_flow_requires_client_class(self):
        adapter = MagicMock()
        adapter.provider_id = "github"
        adapter.get_provider.return_value = MagicMock(
            app=MagicMock(), get_scope=lambda _: []
        )

        view = MagicMock()
        view.client_class = None
        view.adapter_class = MagicMock(return_value=adapter)

        serializer = SocialLoginInputSerializer(
            data={"code": "auth-code"},
            context={"view": view, "request": MagicMock(_request=MagicMock())},
        )

        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_validate_code_flow_oauth_error(self):
        adapter = MagicMock()
        adapter.provider_id = "github"
        provider = MagicMock()
        provider.app = MagicMock()
        provider.get_scope.return_value = []
        adapter.get_provider.return_value = provider
        adapter.parse_token.return_value = MagicMock(app=provider.app)

        class ErrorClient:
            def __init__(*args, **kwargs):
                pass

            def get_access_token(self, code):
                raise OAuth2Error("nope")

        view = MagicMock()
        view.client_class = ErrorClient
        view.adapter_class = MagicMock(return_value=adapter)

        serializer = SocialLoginInputSerializer(
            data={"code": "auth-code"},
            context={"view": view, "request": MagicMock(_request=MagicMock())},
        )

        with patch.object(
            SocialLoginInputSerializer, "_build_callback_url", return_value="/callback"
        ):
            with self.assertRaises(serializers.ValidationError):
                serializer.is_valid(raise_exception=True)

    def test_validate_access_token_http_error(self):
        adapter = MagicMock()
        adapter.provider_id = "github"
        provider = MagicMock()
        provider.app = MagicMock()
        adapter.get_provider.return_value = provider
        adapter.parse_token.return_value = MagicMock(app=provider.app)
        adapter.complete_login.side_effect = HTTPError("bad")

        serializer = SocialLoginInputSerializer(
            data={"access_token": "abc"},
            context={"view": MagicMock(), "request": MagicMock()},
        )

        with (
            patch.object(serializer, "_get_adapter", return_value=adapter),
            patch.object(serializer, "_get_request", return_value=MagicMock()),
        ):
            with self.assertRaises(serializers.ValidationError):
                serializer.is_valid(raise_exception=True)

    def test_validate_access_token_no_reverse_match(self):
        adapter = MagicMock()
        adapter.provider_id = "github"
        provider = MagicMock()
        provider.app = MagicMock()
        adapter.get_provider.return_value = provider
        adapter.parse_token.return_value = MagicMock(app=provider.app)

        serializer = SocialLoginInputSerializer(
            data={"access_token": "abc"},
            context={"view": MagicMock(), "request": MagicMock()},
        )

        with (
            patch.object(serializer, "_get_adapter", return_value=adapter),
            patch.object(serializer, "_get_request", return_value=MagicMock()),
            patch(
                "users.serializers.complete_social_login",
                side_effect=NoReverseMatch("oops"),
            ),
        ):
            with self.assertRaises(serializers.ValidationError):
                serializer.is_valid(raise_exception=True)

    def test_validate_handles_bad_request_response(self):
        adapter = MagicMock()
        adapter.provider_id = "github"
        provider = MagicMock()
        provider.app = MagicMock()
        adapter.get_provider.return_value = provider
        adapter.parse_token.return_value = MagicMock(app=provider.app)
        adapter.complete_login.return_value = MagicMock(
            account=MagicMock(user=MagicMock()), is_existing=True
        )

        serializer = SocialLoginInputSerializer(
            data={"access_token": "abc"},
            context={"view": MagicMock(), "request": MagicMock()},
        )

        with (
            patch.object(serializer, "_get_adapter", return_value=adapter),
            patch.object(serializer, "_get_request", return_value=MagicMock()),
            patch(
                "users.serializers.complete_social_login",
                return_value=HttpResponseBadRequest(b"error"),
            ),
        ):
            with self.assertRaises(serializers.ValidationError):
                serializer.is_valid(raise_exception=True)

    @patch("users.serializers.get_user_model")
    @patch("users.serializers.complete_social_login", return_value=None)
    def test_validate_unique_email_conflict(self, mock_complete, mock_get_user_model):
        login_mock = MagicMock()
        login_mock.account = MagicMock(user=MagicMock())
        login_mock.user = MagicMock(email="dup@example.com")
        login_mock.is_existing = False
        login_mock.state = {}
        login_mock.lookup = MagicMock()
        login_mock.save = MagicMock()

        adapter = MagicMock()
        adapter.provider_id = "github"
        provider = MagicMock(app=MagicMock())
        adapter.get_provider.return_value = provider
        adapter.parse_token.return_value = MagicMock(app=provider.app)
        adapter.complete_login.return_value = login_mock

        mock_manager = MagicMock()
        mock_manager.filter.return_value.exists.return_value = True
        mock_user_model = MagicMock()
        mock_user_model.objects = mock_manager
        mock_get_user_model.return_value = mock_user_model

        serializer = SocialLoginInputSerializer(
            data={"access_token": "abc"},
            context={"view": MagicMock(), "request": MagicMock()},
        )

        with (
            patch.object(serializer, "_get_adapter", return_value=adapter),
            patch.object(serializer, "_get_request", return_value=MagicMock()),
        ):
            with self.assertRaises(serializers.ValidationError):
                serializer.is_valid(raise_exception=True)

    @patch("users.serializers.complete_social_login", return_value=None)
    def test_validate_integrity_error_from_save(self, mock_complete):
        login_mock = MagicMock()
        login_mock.account = MagicMock(user=MagicMock(email=None))
        login_mock.is_existing = False
        login_mock.state = {}
        login_mock.lookup = MagicMock()
        login_mock.save.side_effect = IntegrityError("boom")
        login_mock.user = MagicMock(email=None)

        adapter = MagicMock()
        adapter.provider_id = "github"
        adapter.get_provider.return_value = MagicMock(app=MagicMock())
        adapter.parse_token.return_value = MagicMock()
        adapter.complete_login.return_value = login_mock

        serializer = SocialLoginInputSerializer(
            data={"access_token": "abc"},
            context={"view": MagicMock(), "request": MagicMock()},
        )

        with (
            patch.object(serializer, "_get_adapter", return_value=adapter),
            patch.object(serializer, "_get_request", return_value=MagicMock()),
        ):
            with self.assertRaises(serializers.ValidationError):
                serializer.is_valid(raise_exception=True)

    @patch("users.serializers.complete_social_login", return_value=None)
    def test_validate_skips_signup_for_existing_user(self, mock_complete):
        login_mock = MagicMock()
        login_mock.account = MagicMock(user=MagicMock(email="existing@example.com"))
        login_mock.is_existing = True
        adapter = MagicMock()
        adapter.provider_id = "github"
        adapter.get_provider.return_value = MagicMock(app=MagicMock())
        adapter.parse_token.return_value = MagicMock()
        adapter.complete_login.return_value = login_mock

        serializer = SocialLoginInputSerializer(
            data={"access_token": "abc"},
            context={"view": MagicMock(), "request": MagicMock()},
        )

        with (
            patch.object(serializer, "_get_adapter", return_value=adapter),
            patch.object(serializer, "_get_request", return_value=MagicMock()),
            patch.object(
                SocialLoginInputSerializer, "_post_signup"
            ) as mock_post_signup,
        ):
            self.assertTrue(serializer.is_valid(raise_exception=True))
            self.assertTrue(mock_complete.called)
            mock_post_signup.assert_not_called()
