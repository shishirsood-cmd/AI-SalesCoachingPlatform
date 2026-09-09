import uuid

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.scenario import Scenario
from app.models.session import Speaker, Turn
from app.services.anthropic_client import get_client
from app.services.retrieval import retrieve_relevant_chunks


def build_system_prompt(scenario: Scenario, rag_context: list[str]) -> str:
    objections = "\n".join(f"- {o}" for o in scenario.objections) or "- (none specified)"
    context_block = (
        "\n\n".join(rag_context)
        if rag_context
        else "(no product documentation available — do not invent specifics)"
    )
    call_type_note = (
        "Cold call — you did not initiate this call and are not expecting it."
        if scenario.call_type.value == "cold_call"
        else "Support call — you are a customer with an ongoing issue reaching out for help."
    )

    return f"""You are role-playing as a customer in a sales training simulation. A sales rep is \
practicing their pitch and objection handling on you. Stay fully in character as the customer at \
all times: never break character, never mention that you are an AI, never coach the rep, never \
narrate stage directions.

CUSTOMER PERSONA:
{scenario.persona_description}

CALL TYPE: {call_type_note}
DIFFICULTY: {scenario.difficulty.value}

OBJECTIONS TO RAISE: Weave these into the conversation naturally, one at a time, in response to \
what the rep says — don't list them all at once:
{objections}

RELEVANT PRODUCT INFORMATION (only reference this if it's relevant to what the rep says; don't \
volunteer it unprompted, and don't invent facts beyond what's here):
{context_block}

Respond the way a real person speaks on a call: conversational, concise (1-4 sentences), with \
natural hesitation or emotion where appropriate for the persona and difficulty level."""


async def generate_ai_turn(
    db: AsyncSession,
    org_id: uuid.UUID,
    scenario: Scenario,
    history: list[Turn],
) -> str:
    query = history[-1].content if history else scenario.persona_description
    rag_context = await retrieve_relevant_chunks(db, org_id, query)
    system_prompt = build_system_prompt(scenario, rag_context)

    messages = [
        {"role": "user" if t.speaker == Speaker.rep else "assistant", "content": t.content}
        for t in history
    ]
    if not messages:
        messages = [{"role": "user", "content": "(The call has just connected. Begin as the customer.)"}]

    client = get_client()
    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=300,
            system=system_prompt,
            messages=messages,
        )
    except anthropic.APIStatusError as exc:
        message = exc.body.get("error", {}).get("message") if isinstance(exc.body, dict) else str(exc)
        raise RuntimeError(f"Claude API error: {message}") from exc
    except anthropic.APIConnectionError as exc:
        raise RuntimeError("Could not reach the Claude API. Check your network connection.") from exc

    return "".join(block.text for block in response.content if block.type == "text").strip()
