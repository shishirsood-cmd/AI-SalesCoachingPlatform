import re
from collections import Counter
from typing import Any

import anthropic

from app.core.config import settings
from app.models.evaluation import Evaluation
from app.models.scenario import Scenario
from app.models.session import Speaker, Turn
from app.services.anthropic_client import get_client

FILLER_WORDS = [
    "um", "umm", "uh", "uhh", "like", "you know", "i mean", "actually",
    "basically", "sort of", "kind of", "so yeah",
]


def _build_transcript(turns: list[Turn]) -> str:
    return "\n".join(f"{'Sales Rep' if t.speaker == Speaker.rep else 'Customer'}: {t.content}" for t in turns)


def compute_talk_time_ratio(turns: list[Turn]) -> dict[str, Any]:
    rep_words = sum(len(t.content.split()) for t in turns if t.speaker == Speaker.rep)
    ai_words = sum(len(t.content.split()) for t in turns if t.speaker == Speaker.ai_customer)
    total = rep_words + ai_words
    return {
        "rep_words": rep_words,
        "ai_words": ai_words,
        "rep_talk_time_pct": round(100 * rep_words / total, 1) if total else 0.0,
        "note": "Approximated from word count per turn — no audio-duration data is stored.",
    }


def compute_filler_word_count(turns: list[Turn]) -> dict[str, Any]:
    rep_text = " ".join(t.content for t in turns if t.speaker == Speaker.rep).lower()
    rep_word_count = len(rep_text.split()) or 1
    counts: Counter[str] = Counter()
    for phrase in FILLER_WORDS:
        matches = re.findall(r"\b" + re.escape(phrase) + r"\b", rep_text)
        if matches:
            counts[phrase] = len(matches)
    total = sum(counts.values())
    return {
        "total": total,
        "by_word": dict(counts),
        "per_100_words": round(100 * total / rep_word_count, 2),
    }


def _extract_tool_input(response: Any) -> dict[str, Any]:
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Claude did not return a structured evaluation")


_MAX_JUDGE_ATTEMPTS = 2


async def _call_claude_judge(system_prompt: str, user_message: str, tool: dict[str, Any]) -> dict[str, Any]:
    client = get_client()
    required = tool["input_schema"].get("required", [])
    last_missing: list[str] = []

    for attempt in range(_MAX_JUDGE_ATTEMPTS):
        try:
            response = await client.messages.create(
                model=settings.claude_model,
                max_tokens=1200,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
            )
        except anthropic.APIStatusError as exc:
            message = exc.body.get("error", {}).get("message") if isinstance(exc.body, dict) else str(exc)
            raise RuntimeError(f"Claude API error: {message}") from exc
        except anthropic.APIConnectionError as exc:
            raise RuntimeError("Could not reach the Claude API. Check your network connection.") from exc

        result = _extract_tool_input(response)
        missing = [key for key in required if key not in result]
        if not missing:
            return result
        last_missing = missing  # Forced tool-use occasionally omits a required field on
        # complex schemas — silently retry once before surfacing an error to the caller.

    raise RuntimeError(
        f"Claude's evaluation response was missing expected field(s): {', '.join(last_missing)}. Try again."
    )


async def run_transcript_analysis(scenario: Scenario, turns: list[Turn]) -> tuple[dict[str, Any], str]:
    properties: dict[str, Any] = {
        "objection_handling_score": {
            "type": "number",
            "description": "0-100, how well the rep addressed the objections the customer raised",
        },
        "objection_handling_notes": {"type": "string"},
    }
    required = ["objection_handling_score", "objection_handling_notes"]
    if scenario.sales_framework:
        properties["framework_adherence_score"] = {
            "type": "number",
            "description": f"0-100, adherence to the {scenario.sales_framework} sales framework",
        }
        properties["framework_adherence_notes"] = {"type": "string"}
        required += ["framework_adherence_score", "framework_adherence_notes"]

    tool = {
        "name": "submit_transcript_analysis",
        "description": "Submit analysis of objection handling and sales-framework adherence from this call transcript.",
        "input_schema": {"type": "object", "properties": properties, "required": required},
    }

    framework_line = (
        f"Also assess adherence to the {scenario.sales_framework} sales framework."
        if scenario.sales_framework
        else "No specific sales framework was configured for this scenario — skip framework scoring."
    )
    system_prompt = f"""You are an expert sales call analyst. Analyze this transcript for objection handling \
quality — how well the rep addressed the customer's pushback. {framework_line}

SCENARIO: {scenario.title}
CONFIGURED OBJECTIONS: {", ".join(scenario.objections) or "none specified"}

TRANSCRIPT:
{_build_transcript(turns)}"""

    result = await _call_claude_judge(system_prompt, "Analyze this call now.", tool)

    scores = {
        "talk_time_ratio": compute_talk_time_ratio(turns),
        "filler_words": compute_filler_word_count(turns),
        "objection_handling_score": result["objection_handling_score"],
        "objection_handling_notes": result["objection_handling_notes"],
        "framework_adherence_score": result.get("framework_adherence_score"),
        "framework_adherence_notes": result.get("framework_adherence_notes"),
        "sales_framework": scenario.sales_framework,
    }
    summary = result["objection_handling_notes"]
    if scenario.sales_framework and result.get("framework_adherence_notes"):
        summary += " " + result["framework_adherence_notes"]
    return scores, summary


async def run_roleplay_simulation_eval(scenario: Scenario, turns: list[Turn]) -> tuple[dict[str, Any], str]:
    tool = {
        "name": "submit_roleplay_eval",
        "description": "Submit an evaluation of how well the AI customer persona performed in this simulated call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stayed_in_character_score": {
                    "type": "number",
                    "description": "0-100 — did the AI ever break character, mention being an AI, or coach the rep?",
                },
                "realistic_pushback_score": {
                    "type": "number",
                    "description": "0-100 — did objections feel like a real customer rather than scripted or robotic?",
                },
                "scenario_adherence_score": {
                    "type": "number",
                    "description": (
                        "0-100 — did the AI raise the configured objections and match the "
                        "persona, difficulty, and call type?"
                    ),
                },
                "notes": {"type": "string"},
            },
            "required": [
                "stayed_in_character_score",
                "realistic_pushback_score",
                "scenario_adherence_score",
                "notes",
            ],
        },
    }

    system_prompt = f"""You are an AI QA reviewer grading the *simulated customer persona* in this training \
call transcript — NOT the sales rep. Judge only the "Customer" turns.

SCENARIO: {scenario.title} ({scenario.call_type.value}, {scenario.difficulty.value} difficulty)
CONFIGURED PERSONA: {scenario.persona_description}
CONFIGURED OBJECTIONS THE PERSONA SHOULD RAISE: {", ".join(scenario.objections) or "none specified"}

TRANSCRIPT:
{_build_transcript(turns)}"""

    result = await _call_claude_judge(system_prompt, "Evaluate the AI customer persona now.", tool)
    scores = {
        k: result[k]
        for k in ("stayed_in_character_score", "realistic_pushback_score", "scenario_adherence_score")
    }
    scores["overall_score"] = round(sum(scores.values()) / len(scores), 1)
    return scores, result["notes"]


async def run_coaching_safety_eval(
    scenario: Scenario,
    turns: list[Turn],
    evaluation: Evaluation,
    compliance_guidelines: str | None,
) -> tuple[dict[str, Any], str]:
    properties: dict[str, Any] = {
        "tactical_constructive_score": {
            "type": "number",
            "description": "0-100 — is the feedback specific and actionable rather than generic?",
        },
        "hallucination_free_score": {
            "type": "number",
            "description": "0-100 — 100 means every claim in the feedback is supported by the transcript",
        },
        "hallucination_issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Specific feedback claims not actually supported by the transcript. Always include this "
                "field — use an empty array if there are none."
            ),
        },
        "notes": {"type": "string"},
    }
    required = ["tactical_constructive_score", "hallucination_free_score", "hallucination_issues", "notes"]
    if compliance_guidelines:
        properties["compliance_score"] = {
            "type": "number",
            "description": (
                "0-100 — adherence to the enterprise compliance guidelines given. Always include this "
                "field; use 100 if there are no issues."
            ),
        }
        properties["compliance_issues"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "Always include this field. Use an empty array if there are no issues.",
        }
        required += ["compliance_score", "compliance_issues"]

    tool = {
        "name": "submit_coaching_safety_eval",
        "description": (
            "Submit an evaluation of the quality and safety of the coaching feedback given to the rep. "
            "Every required field must be present in every call, even when the score is perfect or there "
            "are no issues to report — use 0/empty-array in that case, never omit the field."
        ),
        "input_schema": {"type": "object", "properties": properties, "required": required},
    }

    compliance_block = (
        f"ENTERPRISE COMPLIANCE GUIDELINES (check the feedback against these): {compliance_guidelines}"
        if compliance_guidelines
        else "No enterprise compliance guidelines were configured — skip compliance scoring."
    )
    feedback_text = (
        f"Summary: {evaluation.summary}\n"
        f"Strengths: {'; '.join(evaluation.strengths)}\n"
        f"Areas for improvement: {'; '.join(evaluation.areas_for_improvement)}\n"
        f"Per-criterion feedback: {'; '.join(c['feedback'] for c in evaluation.criteria_scores)}"
    )

    system_prompt = f"""You are an AI QA reviewer grading the *coaching feedback* an evaluator AI generated \
for a sales rep after a practice call — NOT the rep's or customer's performance directly. Cross-check every \
claim the feedback makes against what actually happened in the transcript.

{compliance_block}

TRANSCRIPT:
{_build_transcript(turns)}

COACHING FEEDBACK GIVEN TO THE REP:
{feedback_text}"""

    result = await _call_claude_judge(system_prompt, "Evaluate this coaching feedback now.", tool)
    scores: dict[str, Any] = {
        "tactical_constructive_score": result["tactical_constructive_score"],
        "hallucination_free_score": result["hallucination_free_score"],
        "hallucination_issues": result["hallucination_issues"],
        "compliance_score": result.get("compliance_score"),
        "compliance_issues": result.get("compliance_issues", []),
    }
    numeric = [v for k, v in scores.items() if k.endswith("_score") and isinstance(v, (int, float))]
    scores["overall_score"] = round(sum(numeric) / len(numeric), 1) if numeric else 0.0
    return scores, result["notes"]
