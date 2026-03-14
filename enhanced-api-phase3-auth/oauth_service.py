"""
OAuth Service Implementation
Handles OAuth2 provider integrations (Google, GitHub, Microsoft, Okta)
"""

import os
import json
import secrets
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from urllib.parse import urlencode, parse_qs, urlparse
import logging

from models_auth import OAuthAccount, User, OAuthProvider
from pydantic_models_auth import OAuthCallbackRequest

logger = logging.getLogger(__name__)


class OAuthService:
    """OAuth provider service"""

    # Provider configurations
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"
    GITHUB_EMAIL_URL = "https://api.github.com/user/emails"

    MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    MICROSOFT_USER_URL = "https://graph.microsoft.com/v1.0/me"

    OKTA_AUTH_URL_TEMPLATE = "https://{domain}/oauth2/v1/authorize"
    OKTA_TOKEN_URL_TEMPLATE = "https://{domain}/oauth2/v1/token"
    OKTA_USER_URL_TEMPLATE = "https://{domain}/oauth2/v1/userinfo"

    def __init__(self):
        """Initialize OAuth service with credentials"""
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.github_client_id = os.getenv("GITHUB_CLIENT_ID")
        self.github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        self.microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.microsoft_client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.okta_domain = os.getenv("OKTA_DOMAIN")
        self.okta_client_id = os.getenv("OKTA_CLIENT_ID")
        self.okta_client_secret = os.getenv("OKTA_CLIENT_SECRET")

    def generate_state(self) -> str:
        """Generate CSRF protection state string"""
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, provider: str, redirect_uri: str) -> Dict[str, str]:
        """Get OAuth authorization URL for provider"""
        state = self.generate_state()

        if provider == OAuthProvider.GOOGLE.value:
            return self._get_google_auth_url(redirect_uri, state)
        elif provider == OAuthProvider.GITHUB.value:
            return self._get_github_auth_url(redirect_uri, state)
        elif provider == OAuthProvider.MICROSOFT.value:
            return self._get_microsoft_auth_url(redirect_uri, state)
        elif provider == OAuthProvider.OKTA.value:
            return self._get_okta_auth_url(redirect_uri, state)
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

    def _get_google_auth_url(self, redirect_uri: str, state: str) -> Dict[str, str]:
        """Build Google OAuth authorization URL"""
        params = {
            "client_id": self.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return {
            "auth_url": f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}",
            "state": state,
        }

    def _get_github_auth_url(self, redirect_uri: str, state: str) -> Dict[str, str]:
        """Build GitHub OAuth authorization URL"""
        params = {
            "client_id": self.github_client_id,
            "redirect_uri": redirect_uri,
            "scope": "user:email",
            "state": state,
            "allow_signup": "true",
        }
        return {
            "auth_url": f"{self.GITHUB_AUTH_URL}?{urlencode(params)}",
            "state": state,
        }

    def _get_microsoft_auth_url(self, redirect_uri: str, state: str) -> Dict[str, str]:
        """Build Microsoft OAuth authorization URL"""
        params = {
            "client_id": self.microsoft_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid profile email offline_access",
            "state": state,
            "response_mode": "query",
        }
        return {
            "auth_url": f"{self.MICROSOFT_AUTH_URL}?{urlencode(params)}",
            "state": state,
        }

    def _get_okta_auth_url(self, redirect_uri: str, state: str) -> Dict[str, str]:
        """Build Okta OAuth authorization URL"""
        auth_url = self.OKTA_AUTH_URL_TEMPLATE.format(domain=self.okta_domain)
        params = {
            "client_id": self.okta_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
        }
        return {
            "auth_url": f"{auth_url}?{urlencode(params)}",
            "state": state,
        }

    async def handle_callback(
        self,
        request: OAuthCallbackRequest,
        redirect_uri: str,
        db: Session,
    ) -> tuple[User, Optional[OAuthAccount]]:
        """Handle OAuth callback and create/update user"""
        
        if request.provider == OAuthProvider.GOOGLE.value:
            return await self._handle_google_callback(request.code, redirect_uri, db)
        elif request.provider == OAuthProvider.GITHUB.value:
            return await self._handle_github_callback(request.code, redirect_uri, db)
        elif request.provider == OAuthProvider.MICROSOFT.value:
            return await self._handle_microsoft_callback(request.code, redirect_uri, db)
        elif request.provider == OAuthProvider.OKTA.value:
            return await self._handle_okta_callback(request.code, redirect_uri, db)
        else:
            raise ValueError(f"Unsupported OAuth provider: {request.provider}")

    async def _handle_google_callback(
        self, code: str, redirect_uri: str, db: Session
    ) -> tuple[User, Optional[OAuthAccount]]:
        """Handle Google OAuth callback"""
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_resp = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.google_client_id,
                    "client_secret": self.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            # Get user info
            user_resp = await client.get(
                self.GOOGLE_USER_URL,
                params={"access_token": token_data.get("access_token")},
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

            return self._sync_oauth_user(
                OAuthProvider.GOOGLE.value,
                user_data,
                token_data,
                db,
            )

    async def _handle_github_callback(
        self, code: str, redirect_uri: str, db: Session
    ) -> tuple[User, Optional[OAuthAccount]]:
        """Handle GitHub OAuth callback"""
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_resp = await client.post(
                self.GITHUB_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.github_client_id,
                    "client_secret": self.github_client_secret,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            # Get user info
            user_resp = await client.get(
                self.GITHUB_USER_URL,
                headers={
                    "Authorization": f"token {token_data.get('access_token')}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

            # Get primary email
            emails_resp = await client.get(
                self.GITHUB_EMAIL_URL,
                headers={
                    "Authorization": f"token {token_data.get('access_token')}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary_email = next(
                (e["email"] for e in emails if e.get("primary")), ""
            )

            # Add email to user data
            user_data["email"] = primary_email

            return self._sync_oauth_user(
                OAuthProvider.GITHUB.value,
                user_data,
                token_data,
                db,
            )

    async def _handle_microsoft_callback(
        self, code: str, redirect_uri: str, db: Session
    ) -> tuple[User, Optional[OAuthAccount]]:
        """Handle Microsoft OAuth callback"""
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_resp = await client.post(
                self.MICROSOFT_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.microsoft_client_id,
                    "client_secret": self.microsoft_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": "openid profile email",
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            # Get user info
            user_resp = await client.get(
                self.MICROSOFT_USER_URL,
                headers={
                    "Authorization": f"Bearer {token_data.get('access_token')}",
                },
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

            return self._sync_oauth_user(
                OAuthProvider.MICROSOFT.value,
                user_data,
                token_data,
                db,
            )

    async def _handle_okta_callback(
        self, code: str, redirect_uri: str, db: Session
    ) -> tuple[User, Optional[OAuthAccount]]:
        """Handle Okta OAuth callback"""
        token_url = self.OKTA_TOKEN_URL_TEMPLATE.format(domain=self.okta_domain)
        user_url = self.OKTA_USER_URL_TEMPLATE.format(domain=self.okta_domain)

        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_resp = await client.post(
                token_url,
                data={
                    "code": code,
                    "client_id": self.okta_client_id,
                    "client_secret": self.okta_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            # Get user info
            user_resp = await client.get(
                user_url,
                headers={
                    "Authorization": f"Bearer {token_data.get('access_token')}",
                },
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

            return self._sync_oauth_user(
                OAuthProvider.OKTA.value,
                user_data,
                token_data,
                db,
            )

    def _sync_oauth_user(
        self, provider: str, user_data: Dict[str, Any], token_data: Dict[str, Any], db: Session
    ) -> tuple[User, Optional[OAuthAccount]]:
        """Synchronize OAuth user with database"""
        
        # Extract common fields (varies by provider)
        provider_email = self._extract_email(provider, user_data)
        provider_user_id = self._extract_user_id(provider, user_data)
        first_name = user_data.get("given_name") or user_data.get("first_name") or ""
        last_name = user_data.get("family_name") or user_data.get("last_name") or ""

        if not provider_email or not provider_user_id:
            raise ValueError(f"Could not extract email or user ID from {provider}")

        # Find or create user
        user = db.query(User).filter(User.email == provider_email).first()
        if not user:
            user = User(
                email=provider_email,
                first_name=first_name,
                last_name=last_name,
                is_verified=True,  # OAuth users are pre-verified by provider
            )
            db.add(user)
            db.flush()

        # Find or create OAuth account
        oauth_account = (
            db.query(OAuthAccount)
            .filter(
                OAuthAccount.user_id == user.id,
                OAuthAccount.provider == provider,
            )
            .first()
        )

        if not oauth_account:
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
                provider_data=user_data,
                is_primary=True,  # First OAuth account is primary
            )
            db.add(oauth_account)
        else:
            oauth_account.last_used_at = datetime.utcnow()
            oauth_account.provider_data = user_data

        db.commit()
        return user, oauth_account

    @staticmethod
    def _extract_email(provider: str, user_data: Dict[str, Any]) -> str:
        """Extract email from provider-specific user data"""
        if provider == OAuthProvider.GOOGLE.value:
            return user_data.get("email", "")
        elif provider == OAuthProvider.GITHUB.value:
            return user_data.get("email", "")
        elif provider == OAuthProvider.MICROSOFT.value:
            return user_data.get("userPrincipalName") or user_data.get("mail", "")
        elif provider == OAuthProvider.OKTA.value:
            return user_data.get("email", "")
        return ""

    @staticmethod
    def _extract_user_id(provider: str, user_data: Dict[str, Any]) -> str:
        """Extract provider user ID from user data"""
        if provider == OAuthProvider.GOOGLE.value:
            return user_data.get("id", "")
        elif provider == OAuthProvider.GITHUB.value:
            return str(user_data.get("id", ""))
        elif provider == OAuthProvider.MICROSOFT.value:
            return user_data.get("id", "")
        elif provider == OAuthProvider.OKTA.value:
            return user_data.get("sub", "")
        return ""
