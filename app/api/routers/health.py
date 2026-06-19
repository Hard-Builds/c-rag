from fastapi import APIRouter
from app.api.models import BaseResponse

health_router = APIRouter()


@health_router.get("/health", response_model=BaseResponse)
def health_check() -> BaseResponse:
    return BaseResponse(status=200, message="OK")
