from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    OrganizationOut,
    RegisterOrgRequest,
    SignupRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register-org", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_org(payload: RegisterOrgRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await db.scalar(select(User).where(User.email == payload.admin_email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    org = Organization(name=payload.org_name)
    db.add(org)
    await db.flush()

    admin = User(
        org_id=org.id,
        name=payload.admin_name,
        email=payload.admin_email,
        hashed_password=hash_password(payload.admin_password),
        role=UserRole.team_lead,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    await db.refresh(org)

    token = create_access_token(admin.id, org.id, admin.role.value)
    return TokenResponse(access_token=token, user=admin, organization=OrganizationOut.model_validate(org))


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    org = await db.scalar(select(Organization).where(Organization.invite_code == payload.invite_code))
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code")

    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        org_id=org.id,
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole.sales_rep,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, org.id, user.role.value)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user.id, user.org_id, user.role.value)
    return TokenResponse(access_token=token, user=user)
