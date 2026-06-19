from datetime import datetime, timezone


class DateTimeUtils:
    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)
