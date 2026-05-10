"""Google OAuth deployment guidance helpers.

For Streamlit deployments, the recommended production pattern is to terminate
Google OAuth at a trusted edge layer such as Google Cloud IAP, oauth2-proxy, or
a managed platform auth gateway, then pass only authorized traffic to Streamlit.
"""

from __future__ import annotations

from src.auth.auth_config import AuthConfig


def google_oauth_configured(config: AuthConfig) -> bool:
    """Return whether Google OAuth variables are present."""

    return bool(config.google_client_id and config.google_client_secret)

