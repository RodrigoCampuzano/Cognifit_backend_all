from __future__ import annotations

from datetime import timedelta


class DataRetentionPolicy:
    raw_audio_ttl = timedelta(days=30)
    audit_log_min_retention = timedelta(days=365 * 5)
    report_url_ttl = timedelta(hours=24)
