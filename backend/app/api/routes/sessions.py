import base64
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.evaluation import Evaluation
from app.models.scenario import Scenario
from app.models.session import SessionStatus, SimulationSession, Speaker, Turn
from app.models.user import User
from app.schemas.evaluation import EvaluationOut
from app.schemas.session import MessageIn, SessionCreate, SessionOut, TurnOut
from app.services.conversation import generate_ai_turn
from app.services.evaluation import compute_overall_score, evaluate_session
from app.services.voice import synthesize_speech, transcribe_audio

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _maybe_synthesize(text: str) -> str | None:
    """Best-effort TTS: voice is an enhancement, so a synthesis failure shouldn't
    block the conversation — the rep can still read the reply as text."""
    try:
        audio = await synthesize_speech(text)
    except RuntimeError:
        return None
    return base64.b64encode(audio).decode()


async def _turns_for(session_id: uuid.UUID, db: AsyncSession) -> list[Turn]:
    result = await db.scalars(select(Turn).where(Turn.session_id == session_id).order_by(Turn.turn_index))
    return list(result.all())


async def _get_own_session(session_id: uuid.UUID, user: User, db: AsyncSession) -> SimulationSession:
    session = await db.get(SimulationSession, session_id)
    if session is None or session.org_id != user.org_id or session.rep_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _session_out(session: SimulationSession, db: AsyncSession) -> SessionOut:
    turns = await _turns_for(session.id, db)
    out = SessionOut.model_validate(session)
    out.turns = [TurnOut.model_validate(t) for t in turns]
    return out


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[SessionOut]:
    sessions = (
        await db.scalars(
            select(SimulationSession)
            .where(SimulationSession.org_id == user.org_id, SimulationSession.rep_id == user.id)
            .order_by(SimulationSession.started_at.desc())
        )
    ).all()
    return [await _session_out(s, db) for s in sessions]


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> SessionOut:
    session = await _get_own_session(session_id, user, db)
    return await _session_out(session, db)


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    voice: bool = Query(False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    scenario = await db.get(Scenario, payload.scenario_id)
    if scenario is None or scenario.org_id != user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

    session = SimulationSession(org_id=user.org_id, scenario_id=scenario.id, rep_id=user.id)
    db.add(session)
    await db.flush()

    try:
        opening_line = await generate_ai_turn(db, user.org_id, scenario, history=[])
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    db.add(Turn(session_id=session.id, turn_index=0, speaker=Speaker.ai_customer, content=opening_line))
    await db.commit()

    out = await _session_out(session, db)
    if voice:
        out.audio_base64 = await _maybe_synthesize(opening_line)
    return out


@router.post("/{session_id}/messages", response_model=SessionOut)
async def send_message(
    session_id: uuid.UUID,
    payload: MessageIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session = await _get_own_session(session_id, user, db)
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This call has ended")

    scenario = await db.get(Scenario, session.scenario_id)
    history = await _turns_for(session.id, db)

    rep_turn = Turn(
        session_id=session.id, turn_index=len(history), speaker=Speaker.rep, content=payload.content
    )
    db.add(rep_turn)
    await db.flush()
    history.append(rep_turn)

    try:
        reply = await generate_ai_turn(db, user.org_id, scenario, history=history)
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    db.add(
        Turn(
            session_id=session.id,
            turn_index=len(history),
            speaker=Speaker.ai_customer,
            content=reply,
        )
    )
    await db.commit()
    return await _session_out(session, db)


@router.post("/{session_id}/voice-messages", response_model=SessionOut)
async def send_voice_message(
    session_id: uuid.UUID,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    session = await _get_own_session(session_id, user, db)
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This call has ended")

    audio_bytes = await file.read()
    if len(audio_bytes) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Recording too large")

    try:
        transcript = await transcribe_audio(audio_bytes, file.content_type or "audio/webm")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not detect any speech in that recording — try again",
        )

    scenario = await db.get(Scenario, session.scenario_id)
    history = await _turns_for(session.id, db)

    rep_turn = Turn(session_id=session.id, turn_index=len(history), speaker=Speaker.rep, content=transcript)
    db.add(rep_turn)
    await db.flush()
    history.append(rep_turn)

    try:
        reply = await generate_ai_turn(db, user.org_id, scenario, history=history)
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    db.add(
        Turn(session_id=session.id, turn_index=len(history), speaker=Speaker.ai_customer, content=reply)
    )
    await db.commit()

    out = await _session_out(session, db)
    out.audio_base64 = await _maybe_synthesize(reply)
    return out


@router.post("/{session_id}/end", response_model=SessionOut)
async def end_session(
    session_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> SessionOut:
    session = await _get_own_session(session_id, user, db)
    session.status = SessionStatus.completed
    session.ended_at = datetime.now(timezone.utc)
    await db.commit()
    return await _session_out(session, db)


@router.post("/{session_id}/evaluation", response_model=EvaluationOut)
async def create_evaluation(
    session_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Evaluation:
    session = await _get_own_session(session_id, user, db)
    if session.status != SessionStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="End the call before requesting an evaluation"
        )

    existing = await db.scalar(select(Evaluation).where(Evaluation.session_id == session.id))
    if existing is not None:
        return existing

    turns = await _turns_for(session.id, db)
    if not any(t.speaker == Speaker.rep for t in turns):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="There's nothing to evaluate — the rep didn't say anything on this call",
        )

    scenario = await db.get(Scenario, session.scenario_id)

    try:
        result = await evaluate_session(scenario, turns)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    overall_score = compute_overall_score(scenario.rubric_criteria, result["criteria"])
    evaluation = Evaluation(
        session_id=session.id,
        overall_score=overall_score,
        criteria_scores=result["criteria"],
        strengths=result["strengths"],
        areas_for_improvement=result["areas_for_improvement"],
        summary=result["summary"],
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


@router.get("/{session_id}/evaluation", response_model=EvaluationOut)
async def get_evaluation(
    session_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Evaluation:
    session = await _get_own_session(session_id, user, db)
    evaluation = await db.scalar(select(Evaluation).where(Evaluation.session_id == session.id))
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No evaluation yet")
    return evaluation
