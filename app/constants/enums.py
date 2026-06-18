from enum import StrEnum, auto


class RouteType(StrEnum):
    ADMIN = auto()
    PUBLIC = auto()
    PRIVATE = auto()
    INTERNAL = auto()
