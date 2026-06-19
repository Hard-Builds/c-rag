from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.constants.enums import MessageRoleEnum


# ------- Request models -------
class QueryRequest(BaseModel):
    query: str

class ThreadListRespModel(BaseModel):
    id: UUID
    title: str

    model_config = ConfigDict(from_attributes=True)


class ThreadMessageListRespModel(BaseModel):
    id: UUID
    role: MessageRoleEnum
    content: str

    model_config = ConfigDict(from_attributes=True)
