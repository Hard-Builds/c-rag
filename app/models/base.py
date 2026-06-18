from typing import Generic, Optional, TypeVar

from fastapi import status
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    status: int = status.HTTP_200_OK
    message: str
    payload: Optional[T] = None
