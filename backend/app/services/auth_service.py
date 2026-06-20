from ..core.security import hash_password, verify_password
from ..models.user import User
from ..repositories.user_repository import UserRepository


class AuthService:
    @staticmethod
    async def register(
        repo: UserRepository,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        return await repo.create(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
        )

    @staticmethod
    async def authenticate(
        repo: UserRepository, email: str, password: str
    ) -> User | None:
        user = await repo.get_by_email(email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
