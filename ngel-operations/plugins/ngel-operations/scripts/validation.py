"""Shared offline validation; does not establish external authorization."""
from datetime import datetime, timezone


def validate_timezone(value):
    # These fixed zones work on Windows without installing a tzdata dependency.
    if value in ("UTC", "Asia/Singapore", "Asia/Shanghai"):
        return
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(value)
    except (ImportError, ValueError, KeyError, TypeError) as error:
        raise ValueError("Unknown or unavailable IANA timezone; use UTC, Asia/Singapore, Asia/Shanghai or install system timezone data") from error


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO 8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def knowledge_errors(entry, now=None):
    now = now or datetime.now(timezone.utc)
    errors = []
    if entry.get("auto_reply_allowed") is not True:
        return errors
    approved = entry.get("approved_answer", {})
    if (entry.get("status") != "verified" or not isinstance(approved, dict)
        or not all(isinstance(approved.get(lang), str) and approved[lang].strip() for lang in ("zh-CN", "en"))
        or not isinstance(entry.get("verified_by"), str) or not entry["verified_by"].strip()):
        errors.append("automatic reply lacks bilingual verification")
    try:
        verified = timestamp(entry.get("verified_at"))
        expires = timestamp(entry.get("expires_at"))
        if not verified <= now < expires:
            errors.append("knowledge is expired or verification is in the future")
        if expires <= verified:
            errors.append("expiry must follow verification")
    except (ValueError, TypeError):
        errors.append("knowledge requires valid timezone-aware verification and expiry timestamps")
    return errors
