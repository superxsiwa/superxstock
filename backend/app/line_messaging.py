import base64
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet

from app.core.security import SECRET_KEY


class LineMessagingError(Exception):
    pass


def encrypt_channel_access_token(token: str) -> str:
    key = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest())
    return Fernet(key).encrypt(token.encode()).decode()


def decrypt_channel_access_token(encrypted_token: str) -> str:
    key = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest())
    return Fernet(key).decrypt(encrypted_token.encode()).decode()


def send_line_message(channel_access_token: str, line_user_id: str, text: str) -> None:
    payload = json.dumps({
        "to": line_user_id,
        "messages": [{"type": "text", "text": text}],
    }).encode()
    request = Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={
            "Authorization": f"Bearer {channel_access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10):
            return
    except HTTPError as error:
        raise LineMessagingError(f"LINE Messaging API returned HTTP {error.code}.") from error
    except URLError as error:
        raise LineMessagingError("Could not connect to LINE Messaging API.") from error