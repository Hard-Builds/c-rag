import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core import logger, request_id_ctx_var


class APITraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
        request_id_ctx_var.set(request_id)

        start = time.time()
        response = await call_next(request)
        response.headers["X-Trace-Id"] = request_id

        user_id = getattr(getattr(request.state, "user", None), "id", None)
        logger.info(
            f"API Trace | user={user_id} method={request.method} "
            f"path={request.url.path} status={response.status_code} "
            f"duration={time.time() - start:.3f}s id={request_id}"
        )
        return response
