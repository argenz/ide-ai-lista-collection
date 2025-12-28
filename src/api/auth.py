"""OAuth2 authentication for Idealista API."""

from datetime import datetime, timedelta
from typing import Optional
import base64

import requests
import structlog

from src.config import settings

logger = structlog.get_logger()


class OAuth2TokenManager:
    """
    Manages OAuth2 token lifecycle for Idealista API.

    Tokens are valid for 1 hour and cached in memory.
    Auto-refreshes before expiration.
    """

    TOKEN_URL = "https://api.idealista.com/oauth/token"
    TOKEN_VALIDITY_SECONDS = 3600  # 1 hour
    REFRESH_BUFFER_SECONDS = 300  # Refresh 5 minutes before expiry

    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize token manager.

        Args:
            api_key: Idealista API key
            api_secret: Idealista API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    def _encode_credentials(self) -> str:
        """
        Encode API credentials for Basic Auth.

        Returns:
            Base64-encoded credentials string
        """
        credentials = f"{self.api_key}:{self.api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return encoded

    def _request_new_token(self) -> str:
        """
        Request a new OAuth2 token from Idealista API.

        Returns:
            Access token string

        Raises:
            requests.HTTPError: If token request fails
        """
        headers = {
            "Authorization": f"Basic {self._encode_credentials()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "read"
        }

        logger.info("Requesting new OAuth2 token")

        response = requests.post(
            self.TOKEN_URL,
            headers=headers,
            data=data,
            timeout=30
        )

        if response.status_code == 401:
            logger.error("OAuth2 authentication failed - invalid credentials")
            raise requests.HTTPError("Invalid API credentials", response=response)

        response.raise_for_status()

        token_data = response.json()
        access_token = token_data["access_token"]

        # Cache token and expiry time
        self._token = access_token
        self._token_expires_at = datetime.utcnow() + timedelta(
            seconds=self.TOKEN_VALIDITY_SECONDS
        )

        logger.info(
            "OAuth2 token obtained",
            expires_at=self._token_expires_at.isoformat()
        )

        return access_token

    def _is_token_expired(self) -> bool:
        """
        Check if current token is expired or about to expire.

        Returns:
            True if token needs refresh, False otherwise
        """
        if self._token is None or self._token_expires_at is None:
            return True

        # Refresh if within buffer period of expiry
        buffer_time = datetime.utcnow() + timedelta(seconds=self.REFRESH_BUFFER_SECONDS)
        return buffer_time >= self._token_expires_at

    def get_token(self) -> str:
        """
        Get a valid OAuth2 token, refreshing if necessary.

        Returns:
            Valid access token

        Raises:
            requests.HTTPError: If token request fails
        """
        if self._is_token_expired():
            logger.info("Token expired or missing, requesting new token")
            self._request_new_token()

        return self._token

    def invalidate(self):
        """Invalidate cached token, forcing refresh on next request."""
        self._token = None
        self._token_expires_at = None
        logger.info("Token cache invalidated")


# Global token manager instance
_token_manager: Optional[OAuth2TokenManager] = None


def get_token_manager() -> OAuth2TokenManager:
    """
    Get or create global token manager instance.

    Returns:
        OAuth2TokenManager instance
    """
    global _token_manager

    if _token_manager is None:
        _token_manager = OAuth2TokenManager(
            api_key=settings.api.idealista_api_key,
            api_secret=settings.api.idealista_api_secret
        )
        logger.info("Token manager initialized")

    return _token_manager
