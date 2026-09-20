import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.scenario import Scenario
from app.models.user import User, UserRole
from app.schemas.scenario import ScenarioCreate, ScenarioOut, ScenarioUpdate

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


async def _get_org_scenario(scenario_id: uuid.UUID, user: User, db: AsyncSession) -> Scenario:
    scenario = await db.get(Scenario, scenario_id)
    if scenario is None or scenario.org_id != user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return scenario


@router.get("", response_model=list[ScenarioOut])
async def list_scenarios(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Scenario]:
    result = await db.scalars(
        select(Scenario).where(Scenario.org_id == user.org_id).order_by(Scenario.created_at.desc())
    )
    return list(result.all())


@router.get("/{scenario_id}", response_model=ScenarioOut)
async def get_scenario(
    scenario_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Scenario:
    return await _get_org_scenario(scenario_id, user, db)


@router.post("", response_model=ScenarioOut, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    payload: ScenarioCreate,
    user: User = Depends(require_role(UserRole.team_lead)),
    db: AsyncSession = Depends(get_db),
) -> Scenario:
    scenario = Scenario(
        org_id=user.org_id,
        created_by=user.id,
        title=payload.title,
        persona_description=payload.persona_description,
        objections=payload.objections,
        difficulty=payload.difficulty,
        call_type=payload.call_type,
        rubric_criteria=[c.model_dump() for c in payload.rubric_criteria],
        sales_framework=payload.sales_framework,
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return scenario


@router.put("/{scenario_id}", response_model=ScenarioOut)
async def update_scenario(
    scenario_id: uuid.UUID,
    payload: ScenarioUpdate,
    user: User = Depends(require_role(UserRole.team_lead)),
    db: AsyncSession = Depends(get_db),
) -> Scenario:
    scenario = await _get_org_scenario(scenario_id, user, db)
    scenario.title = payload.title
    scenario.persona_description = payload.persona_description
    scenario.objections = payload.objections
    scenario.difficulty = payload.difficulty
    scenario.call_type = payload.call_type
    scenario.rubric_criteria = [c.model_dump() for c in payload.rubric_criteria]
    scenario.sales_framework = payload.sales_framework
    await db.commit()
    await db.refresh(scenario)
    return scenario


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: uuid.UUID,
    user: User = Depends(require_role(UserRole.team_lead)),
    db: AsyncSession = Depends(get_db),
) -> None:
    scenario = await _get_org_scenario(scenario_id, user, db)
    await db.delete(scenario)
    await db.commit()
