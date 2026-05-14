from sqlmodel.ext.asyncio.session import AsyncSession
from database.models.users import Users
from .auth_shemas import RegisterRequest


class AuthenticationServies:
    session: AsyncSession

    def __init__(self, session: AsyncSession):
        self.session = session

    async def Register(self, req: RegisterRequest) -> Users:
        
