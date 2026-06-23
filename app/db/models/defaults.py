from sqlalchemy import text


class PostgresDefaults:
    @staticmethod
    def UTC_NOW():
        return text("(NOW() AT TIME ZONE 'UTC')")


