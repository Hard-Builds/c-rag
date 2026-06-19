from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.models import BaseResponse


class DocumentResp(BaseModel):
    id: UUID
    filename: str
    file_path: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseResponse[List[DocumentResp]]):
    pass
