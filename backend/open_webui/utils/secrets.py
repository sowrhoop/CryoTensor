import base64
import hashlib
import json
import logging
import os
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)


def encryption_feature_enabled() -> bool:
    return os.getenv("ENABLE_LOCAL_ENCRYPTION", "false").lower() == "true"


@lru_cache(maxsize=1)
def _get_secret() -> str | None:
    secret = os.getenv("CONFIG_ENCRYPTION_KEY", "").strip()
    if not secret:
        return None
    return secret


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet | None:
    secret = _get_secret()
    if not secret:
        return None

    # Derive a urlsafe 32-byte key from the provided secret
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)

    try:
        return Fernet(key)
    except Exception as exc:  # pragma: no cover - defensive guard
        log.error("Failed to initialize Fernet instance: %s", exc)
        return None


def encryption_available() -> bool:
    """Return True when encryption is enabled and a key is configured."""

    if not encryption_feature_enabled():
        return False

    return _get_fernet() is not None


def encrypt_sensitive_value(value: Any) -> dict[str, Any]:
    """Encrypt an arbitrary JSON-serializable value."""

    fernet = _get_fernet()
    if not encryption_feature_enabled() or fernet is None:
        raise RuntimeError(
            "CONFIG_ENCRYPTION_KEY must be set to persist sensitive configuration values."
        )

    try:
        payload = json.dumps(value).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unable to serialize sensitive config value: {exc}") from exc

    token = fernet.encrypt(payload).decode("utf-8")
    return {"__encrypted__": "fernet", "token": token, "v": 1}


def decrypt_sensitive_value(value: Any) -> Any:
    """Decrypt a value previously produced by encrypt_sensitive_value."""

    if not isinstance(value, dict) or value.get("__encrypted__") != "fernet":
        return value

    fernet = _get_fernet()
    if fernet is None:
        raise RuntimeError(
            "CONFIG_ENCRYPTION_KEY must be provided to decrypt sensitive configuration values."
        )

    try:
        token = value["token"].encode("utf-8")
        payload = fernet.decrypt(token)
        return json.loads(payload.decode("utf-8"))
    except KeyError as exc:
        raise ValueError("Encrypted sensitive value missing token") from exc
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt sensitive configuration value") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Encrypted sensitive value contains invalid payload") from exc


def mask_sensitive_value(value: Any, visible: int = 4) -> Any:
    """Return a masked representation of the provided secret."""

    if value is None:
        return None

    if isinstance(value, str):
        if not value:
            return ""

        tail = value[-visible:] if visible > 0 else ""
        return f"{'*' * max(len(value) - len(tail), 4)}{tail}"

    if isinstance(value, list):
        return [mask_sensitive_value(item, visible=visible) for item in value]

    if isinstance(value, dict):
        # Avoid mutating the original dict when masking
        return {
            key: mask_sensitive_value(item, visible=visible) for key, item in value.items()
        }

    return "***" if value else value


def summarize_sensitive_value(value: Any) -> str:
    masked = mask_sensitive_value(value)

    if isinstance(masked, list):
        return "[" + ", ".join(str(item) for item in masked) + "]"

    if isinstance(masked, dict):
        return json.dumps(masked)

    return str(masked)


def fingerprint_sensitive_value(value: Any) -> str | None:
    if value in (None, ""):
        return None

    if isinstance(value, (dict, list)):
        canonical = json.dumps(value, sort_keys=True)
    else:
        canonical = str(value)

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
