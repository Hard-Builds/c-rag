from enum import StrEnum, auto


class RouteType(StrEnum):
    ADMIN = auto()
    PUBLIC = auto()
    PRIVATE = auto()
    INTERNAL = auto()


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class MessageRoleEnum(StrEnum):
    HUMAN = "human"
    AI = "ai"
