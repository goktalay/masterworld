"""Deprem adaptörleri için ortak saat yardımcısı (modül adı '_' ile başladığı için adaptör sayılmaz)."""
from datetime import datetime, timezone


def iso_ts(s):
    """ISO 8601 (Z'li ya da saat dilimsiz = UTC) → unix sn; okunamazsa None."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).strip().replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def utc_str(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
