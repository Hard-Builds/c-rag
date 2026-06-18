from sqlalchemy import text


class PostgresDefaults:
    @staticmethod
    def UTC_NOW():
        return text("(NOW() AT TIME ZONE 'UTC')")

    @staticmethod
    def UUIDV7():
        return text("uuidv7()")

    @staticmethod
    def GEN_RANDOM_UUID():
        return text("gen_random_uuid()")

    @staticmethod
    def TRUE():
        return text("true")

    @staticmethod
    def FALSE():
        return text("false")
