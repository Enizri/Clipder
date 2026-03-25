import logging
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TwitchOAuth:
    def __init__(self):
        self.client_id = settings.twitch_client_id
        self.client_secret = settings.twitch_client_secret
        self.redirect_uri = settings.twitch_redirect_uri

    def get_authorization_url(self, state: str = "") -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "user:read:follows",
        }
        if state:
            params["state"] = state
        return f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Optional[Dict[str, str]]:
        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return None

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        url = "https://id.twitch.tv/oauth2/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict[str, str]]:
        url = "https://api.twitch.tv/helix/users"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {access_token}",
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json().get("data", [])
            if data:
                user = data[0]
                return {
                    "id": user["id"],
                    "login": user["login"],
                    "display_name": user["display_name"],
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None

    def get_user_follows(self, access_token: str, user_id: str) -> List[Dict[str, str]]:
        url = f"https://api.twitch.tv/helix/users/follows?from_id={user_id}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {access_token}",
        }
        follows = []
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            for follow in data.get("data", []):
                follows.append(
                    {
                        "to_id": follow["to_id"],
                        "to_name": follow["to_name"],
                    }
                )
        except Exception as e:
            logger.error(f"Error getting user follows: {e}")
        return follows

    def search_channels(self, query: str, access_token: str) -> List[Dict[str, str]]:
        url = f"https://api.twitch.tv/helix/search/channels?query={query}"
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {access_token}",
        }
        channels = []
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            for channel in data.get("data", []):
                channels.append(
                    {
                        "id": channel["id"],
                        "name": channel["display_name"],
                        "game_name": channel.get("game_name", ""),
                        "is_live": channel.get("is_live", False),
                    }
                )
        except Exception as e:
            logger.error(f"Error searching channels: {e}")
        return channels
