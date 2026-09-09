import anthropic

from app.core.config import settings
from app.models.scenario import Scenario
from app.models.session import Speaker, Turn
from app.services.anthropic_client import get_client

EVALUATION_TOOL = {
    "name": "submit_evaluation",
    "description": (
        "Submit a structured evaluation of the sales rep's performance on this call, "
        "scored against the given rubric criteria."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "criteria": {
                "type": "array",
                "description": (
                    "One entry per rubric criterion, in the same order and using the "
                    "exact same names as given in the rubric."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "score": {
                            "type": "number",
                            "description": "0-100, how well the rep performed on this criterion",
                        },
                        "feedback": {
                            "type": "string",
                            "description": (
                                "1-2 sentences of specific, actionable feedback referencing "
                                "what the rep actually said"
                            ),
                        },
                    },
                    "required": ["name", "score", "feedback"],
                },
            },
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 specific things the rep did well, with evidence from the call",
            },
            "areas_for_improvement": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 specific, actionable things the rep should improve",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence overall summary of the rep's performance on this call",
            },
        },
        "required": ["criteria", "strengths", "areas_for_improvement", "summary"],
    },
}


def _build_transcript(turns: list[Turn]) -> str:
    lines = [f"{'Sales Rep' if t.speaker == Speaker.rep else 'Customer'}: {t.content}" for t in turns]
    return "\n".join(lines)


def _build_system_prompt(scenario: Scenario, turns: list[Turn]) -> str:
    criteria_desc = "\n".join(
        f"- {c['name']} (weight {c['weight']}%): {c.get('description', '')}"
        for c in scenario.rubric_criteria
    )
    return f"""You are an expert sales coaching evaluator. Score the sales rep's performance on the \
call transcript below against the given rubric. Be specific and evidence-based — reference what the \
rep actually said, not generic advice. Be fair but rigorous: a score of 100 should be reserved for \
genuinely excellent execution, not just adequate performance.

SCENARIO: {scenario.title} ({scenario.call_type.value}, {scenario.difficulty.value} difficulty)
CUSTOMER PERSONA: {scenario.persona_description}

RUBRIC CRITERIA:
{criteria_desc}

TRANSCRIPT:
{_build_transcript(turns)}"""


async def evaluate_session(scenario: Scenario, turns: list[Turn]) -> dict:
    system_prompt = _build_system_prompt(scenario, turns)
    client = get_client()

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": "Evaluate this call now."}],
            tools=[EVALUATION_TOOL],
            tool_choice={"type": "tool", "name": "submit_evaluation"},
        )
    except anthropic.APIStatusError as exc:
        message = exc.body.get("error", {}).get("message") if isinstance(exc.body, dict) else str(exc)
        raise RuntimeError(f"Claude API error: {message}") from exc
    except anthropic.APIConnectionError as exc:
        raise RuntimeError("Could not reach the Claude API. Check your network connection.") from exc

    for block in response.content:
        if block.type == "tool_use":
            return _sanitize_result(block.input)

    raise RuntimeError("Claude did not return a structured evaluation")


def _strip_stray_quote(text: str) -> str:
    """Claude's tool-call output occasionally appends a stray trailing quote
    character to free-text fields (observed on `summary` specifically). Strip
    it defensively rather than relying on prompting alone to prevent it."""
    text = text.strip()
    if text.endswith('"') and text.count('"') % 2 == 1:
        text = text[:-1].rstrip()
    return text


def _sanitize_result(result: dict) -> dict:
    result["summary"] = _strip_stray_quote(result["summary"])
    result["strengths"] = [_strip_stray_quote(s) for s in result["strengths"]]
    result["areas_for_improvement"] = [_strip_stray_quote(s) for s in result["areas_for_improvement"]]
    for criterion in result["criteria"]:
        criterion["feedback"] = _strip_stray_quote(criterion["feedback"])
    return result


def compute_overall_score(rubric_criteria: list[dict], scored_criteria: list[dict]) -> float:
    weight_by_name = {c["name"].strip().lower(): c["weight"] for c in rubric_criteria}
    weighted_sum = 0.0
    weight_total = 0.0
    for c in scored_criteria:
        weight = weight_by_name.get(str(c["name"]).strip().lower())
        if weight is None:
            continue
        weighted_sum += c["score"] * weight
        weight_total += weight

    if weight_total == 0:
        scores = [c["score"] for c in scored_criteria]
        return round(sum(scores) / len(scores), 1) if scores else 0.0

    return round(weighted_sum / weight_total, 1)
