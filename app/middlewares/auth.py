from typing import Any, Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, \
    RequestResponseEndpoint

from app.constants import INVALID_TOKEN, RouteType
from app.core import exception_handler, logger, settings
from app.db import DBClient
from app.db.services import UserService


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Any:
        path = request.url.path

        if RouteType.PRIVATE in path or RouteType.ADMIN in path:
            try:
                # token = self._get_bearer_token(request)
                # TODO: validate token and attach user to request.state
                # user = verify_token(token)

                # Todo: remove, using admin by default
                async with DBClient._session_factory() as db:
                    admin = await UserService(db).get_admin()
                    request.state.user = admin
                    if not admin:
                        logger.warning("No admin user found.")
                        raise Exception("No admin user found.")
                return await call_next(request)
            except Exception as exc:
                exception_handler(exc, is_raise=True, logger=logger)

        elif RouteType.INTERNAL in path:
            token = self._get_bearer_token(request)
            if token == settings.INTERNAL_TOKEN:
                return await call_next(request)
            raise HTTPException(status_code=401, detail=INVALID_TOKEN)

        return await call_next(request)

    @staticmethod
    def _get_bearer_token(request: Request) -> str:
        auth: Optional[str] = request.headers.get("authorization")
        if auth and auth.startswith("Bearer ") and len(auth.split(" ")) == 2:
            return auth.split(" ")[1]
        raise HTTPException(status_code=401, detail=INVALID_TOKEN)
