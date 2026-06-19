from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.models import BaseResponse
from app.constants import DocumentStatusEnum


class DocumentResp(BaseModel):
    id: UUID
    filename: str
    file_path: str
    uploaded_at: datetime
    updated_at: datetime
    status: DocumentStatusEnum
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseResponse[List[DocumentResp]]):
    pass
