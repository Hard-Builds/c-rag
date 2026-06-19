from typing import Any

from fastapi.responses import StreamingResponse


class SafeStreamingResponse(StreamingResponse):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        headers = kwargs.get("headers", {})
        headers.setdefault("Content-Encoding", "identity")
        kwargs["headers"] = headers
        super().__init__(*args, **kwargs)
