import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import get_settings
from ....core.dependencies import get_current_user, get_db
from ....core.security import create_access_token, create_refresh_token, decode_token
from ....repositories.user_repository import UserRepository
from ....schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut
from ....services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _set_tokens(response: Response, user_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        "access_token",
        create_access_token(user_id),
        httponly=True,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        secure=not settings.debug,
    )
    response.set_cookie(
        "refresh_token",
        create_refresh_token(user_id),
        httponly=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        secure=not settings.debug,
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    if await repo.get_by_email(body.email):
        raise HTTPException(status_code=409, detail="Email already registered.")
    user = await AuthService.register(repo, body.email, body.password, body.full_name)
    await db.commit()
    _set_tokens(response, user.id)
    logger.info(f"New user registered: {user.email}")
    return AuthResponse(user=UserOut.model_validate(user), message="Account created.")


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await AuthService.authenticate(repo, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    _set_tokens(response, user.id)
    return AuthResponse(user=UserOut.model_validate(user), message="Login successful.")


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token",  samesite="lax")
    response.delete_cookie("refresh_token", samesite="lax")
    return {"message": "Logged out."}


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token.")
    user_id = decode_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    user = await UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found.")
    _set_tokens(response, user.id)
    return AuthResponse(user=UserOut.model_validate(user), message="Token refreshed.")
