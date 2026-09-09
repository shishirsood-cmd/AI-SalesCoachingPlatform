import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.evaluation import Evaluation
from app.models.scenario import Scenario
from app.models.session import SimulationSession
from app.models.user import User, UserRole
from app.schemas.analytics import (
    CriterionStat,
    MyProgressOut,
    ProgressEntry,
    RepStat,
    ScenarioStat,
    TeamAnalyticsOut,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _average(scores: list[float]) -> float:
    return round(sum(scores) / len(scores), 1) if scores else 0.0


@router.get("/my-progress", response_model=MyProgressOut)
async def my_progress(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MyProgressOut:
    rows = (
        await db.execute(
            select(Evaluation, SimulationSession, Scenario)
            .join(SimulationSession, Evaluation.session_id == SimulationSession.id)
            .join(Scenario, SimulationSession.scenario_id == Scenario.id)
            .where(SimulationSession.rep_id == user.id, SimulationSession.org_id == user.org_id)
            .order_by(Evaluation.created_at.asc())
        )
    ).all()

    entries = [
        ProgressEntry(
            session_id=session.id,
            scenario_title=scenario.title,
            completed_at=evaluation.created_at,
            overall_score=evaluation.overall_score,
        )
        for evaluation, session, scenario in rows
    ]
    average = round(sum(e.overall_score for e in entries) / len(entries), 1) if entries else None
    return MyProgressOut(entries=entries, average_score=average)


@router.get("/team", response_model=TeamAnalyticsOut)
async def team_analytics(
    user: User = Depends(require_role(UserRole.team_lead)), db: AsyncSession = Depends(get_db)
) -> TeamAnalyticsOut:
    rows = (
        await db.execute(
            select(Evaluation, SimulationSession, Scenario, User)
            .join(SimulationSession, Evaluation.session_id == SimulationSession.id)
            .join(Scenario, SimulationSession.scenario_id == Scenario.id)
            .join(User, SimulationSession.rep_id == User.id)
            .where(SimulationSession.org_id == user.org_id)
        )
    ).all()

    scores_by_rep: dict[uuid.UUID, list[float]] = defaultdict(list)
    rep_names: dict[uuid.UUID, str] = {}
    scores_by_scenario: dict[uuid.UUID, list[float]] = defaultdict(list)
    scenario_titles: dict[uuid.UUID, str] = {}
    scores_by_criterion: dict[str, list[float]] = defaultdict(list)

    for evaluation, session, scenario, rep in rows:
        scores_by_rep[rep.id].append(evaluation.overall_score)
        rep_names[rep.id] = rep.name
        scores_by_scenario[scenario.id].append(evaluation.overall_score)
        scenario_titles[scenario.id] = scenario.title
        for c in evaluation.criteria_scores:
            scores_by_criterion[c["name"]].append(c["score"])

    total = len(rows)
    overall_average = _average([evaluation.overall_score for evaluation, *_ in rows]) if total else None

    by_rep = sorted(
        (
            RepStat(rep_id=rid, rep_name=rep_names[rid], sessions_completed=len(scores), average_score=_average(scores))
            for rid, scores in scores_by_rep.items()
        ),
        key=lambda r: r.average_score,
    )
    by_scenario = sorted(
        (
            ScenarioStat(
                scenario_id=sid, title=scenario_titles[sid], attempts=len(scores), average_score=_average(scores)
            )
            for sid, scores in scores_by_scenario.items()
        ),
        key=lambda s: s.average_score,
    )
    by_criterion = sorted(
        (
            CriterionStat(name=name, average_score=_average(scores), sample_count=len(scores))
            for name, scores in scores_by_criterion.items()
        ),
        key=lambda c: c.average_score,
    )

    return TeamAnalyticsOut(
        total_evaluated_sessions=total,
        average_score=overall_average,
        by_rep=by_rep,
        by_scenario=by_scenario,
        by_criterion=by_criterion,
    )
