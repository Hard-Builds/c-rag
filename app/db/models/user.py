import uuid

import uuid6
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.enums import UserRole
from app.db.client import Base
from app.db.models.defaults import PostgresDefaults


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid6.uuid7,
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(
        String, nullable=False, default=UserRole.USER
    )
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=PostgresDefaults.UTC_NOW(),
    )

