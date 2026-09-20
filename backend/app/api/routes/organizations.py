from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.organization import Organization, _generate_invite_code
from app.models.user import User, UserRole
from app.schemas.auth import OrganizationOut

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=OrganizationOut)
async def get_my_organization(
    user: User = Depends(require_role(UserRole.team_lead)), db: AsyncSession = Depends(get_db)
) -> Organization:
    return await db.get(Organization, user.org_id)


@router.post("/me/rotate-invite-code", response_model=OrganizationOut)
async def rotate_invite_code(
    user: User = Depends(require_role(UserRole.team_lead)), db: AsyncSession = Depends(get_db)
) -> Organization:
    org = await db.get(Organization, user.org_id)
    org.invite_code = _generate_invite_code()
    await db.commit()
    await db.refresh(org)
    return org
