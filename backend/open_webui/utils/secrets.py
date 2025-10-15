import hashlib
import json
from typing import Any


def encryption_feature_enabled() -> bool:
    return False


def encryption_available() -> bool:
    return False


def encrypt_sensitive_value(value: Any) -> Any:
    return value


def decrypt_sensitive_value(value: Any) -> Any:
    return value


def mask_sensitive_value(value: Any, visible: int = 4) -> Any:
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
