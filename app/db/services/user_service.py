from app.constants.enums import UserRole
from app.db.models.user import User
from app.db.services.base import BaseDB


class UserService(BaseDB[User]):
    def __init__(self, db):
        super().__init__(db, User)

    async def get_by_email(self, email: str):
        return await self.get_by_filter(email=email)

    async def get_admin(self):
        return await self.get_by_filter(role=UserRole.ADMIN)