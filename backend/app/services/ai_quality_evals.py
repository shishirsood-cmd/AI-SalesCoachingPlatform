import re
from collections import Counter
from typing import Any

import anthropic

from app.core.config import settings
from app.models.evaluation import Evaluation
from app.models.scenario import Scenario
from app.models.session import SimulationSession, Speaker, Turn
from app.services.anthropic_client import get_client

FILLER_WORDS = [
    "um", "umm", "uh", "uhh", "like", "you know", "i mean", "actually",
    "basically", "sort of", "kind of", "so yeah",
]

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "this", "that", "i", "you", "your", "we",
    "our", "to", "of", "in", "on", "for", "and", "or", "but", "it", "with", "at", "as", "be",
    "have", "has", "do", "does", "did", "not", "no", "so", "if", "just",
}

_NAME_PATTERNS = [
    re.compile(r"\bthis is ([A-Z][a-z]+)\b"),
    re.compile(r"\bi'?m ([A-Z][a-z]+)\b"),
    re.compile(r"\bmy name is ([A-Z][a-z]+)\b", re.IGNORECASE),
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


def compute_call_duration(session: SimulationSession) -> dict[str, Any]:
    if session.ended_at is None:
        return {"seconds": None, "note": "Call not yet ended."}
    return {"seconds": round((session.ended_at - session.started_at).total_seconds(), 1)}


def compute_turn_counts(turns: list[Turn]) -> dict[str, Any]:
    rep = sum(1 for t in turns if t.speaker == Speaker.rep)
    ai = sum(1 for t in turns if t.speaker == Speaker.ai_customer)
    return {"rep_turns": rep, "ai_turns": ai, "total_turns": rep + ai}


def compute_question_rate(turns: list[Turn]) -> dict[str, Any]:
    rep_turns = [t for t in turns if t.speaker == Speaker.rep]
    if not rep_turns:
        return {"questions_asked": 0, "rep_turns": 0, "per_turn": 0.0}
    questions = sum(t.content.count("?") for t in rep_turns)
    return {
        "questions_asked": questions,
        "rep_turns": len(rep_turns),
        "per_turn": round(questions / len(rep_turns), 2),
    }


def compute_rep_turn_length_stats(turns: list[Turn]) -> dict[str, Any]:
    rep_word_counts = [len(t.content.split()) for t in turns if t.speaker == Speaker.rep]
    if not rep_word_counts:
        return {"average_words": 0.0, "longest_words": 0, "rep_turns": 0}
    return {
        "average_words": round(sum(rep_word_counts) / len(rep_word_counts), 1),
        "longest_words": max(rep_word_counts),
        "rep_turns": len(rep_word_counts),
    }


def compute_response_latency(turns: list[Turn]) -> dict[str, Any]:
    """Time between the AI customer's turn and the rep's next turn. For voice calls this
    includes speech-to-text processing time, not pure think-time — a noisier signal than
    the other metrics here."""
    deltas = []
    for prev, curr in zip(turns, turns[1:]):
        if prev.speaker == Speaker.ai_customer and curr.speaker == Speaker.rep:
            delta = (curr.created_at - prev.created_at).total_seconds()
            if delta >= 0:
                deltas.append(delta)
    if not deltas:
        return {"average_seconds": None, "samples": 0}
    return {"average_seconds": round(sum(deltas) / len(deltas), 1), "samples": len(deltas)}


def _significant_words(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def compute_objection_coverage(scenario_objections: list[str], turns: list[Turn]) -> dict[str, Any]:
    """Approximate match: an objection counts as "raised" if at least half of its
    significant (non-stopword) words appear somewhere in the AI customer's turns. This is
    a deterministic heuristic, not semantic understanding — paraphrased objections with
    mostly different wording may be missed."""
    ai_text = " ".join(t.content for t in turns if t.speaker == Speaker.ai_customer).lower()
    raised = []
    for objection in scenario_objections:
        sig = _significant_words(objection)
        if not sig:
            continue
        matched = sum(1 for w in sig if w in ai_text)
        if matched / len(sig) >= 0.5:
            raised.append(objection)
    return {
        "configured_count": len(scenario_objections),
        "raised_count": len(raised),
        "raised": raised,
        "note": "Approximate word-overlap match, not semantic — may miss heavily paraphrased objections.",
    }


def compute_customer_name_usage(turns: list[Turn]) -> dict[str, Any]:
    ai_turns = [t for t in turns if t.speaker == Speaker.ai_customer]
    name = None
    if ai_turns:
        for pattern in _NAME_PATTERNS:
            match = pattern.search(ai_turns[0].content)
            if match:
                name = match.group(1)
                break
    if not name:
        return {
            "customer_name_detected": None,
            "used_by_rep": None,
            "note": "Could not reliably extract a customer name from the AI's opening line.",
        }
    rep_text = " ".join(t.content for t in turns if t.speaker == Speaker.rep)
    used = bool(re.search(r"\b" + re.escape(name) + r"\b", rep_text, re.IGNORECASE))
    return {"customer_name_detected": name, "used_by_rep": used}


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


def _build_scorecard_text(evaluation: Evaluation) -> str:
    criteria_lines = "\n".join(
        f"- {c['name']} ({c['score']}/100): {c['feedback']}" for c in evaluation.criteria_scores
    )
    return f"""Overall score: {evaluation.overall_score}/100
Summary: {evaluation.summary}
Per-criterion scores:
{criteria_lines}
Strengths: {"; ".join(evaluation.strengths)}
Areas for improvement: {"; ".join(evaluation.areas_for_improvement)}"""


async def run_transcript_analysis(
    scenario: Scenario, turns: list[Turn], evaluation: Evaluation, session: SimulationSession
) -> tuple[dict[str, Any], str]:
    """Audits the *Call Scorecard* (the rubric-based Evaluation Claude already produced for the
    rep) for whether it accurately and completely reflects transcript-level signals — this does
    not re-grade the rep independently. All metrics below are computed deterministically in code
    (no LLM judgment, so no cost or flakiness); whether the scorecard *appropriately accounted
    for* the core ones, and whether its objection-handling and framework-adherence assessments
    are accurate, is judged by Claude against the actual transcript."""
    talk_time = compute_talk_time_ratio(turns)
    fillers = compute_filler_word_count(turns)
    call_duration = compute_call_duration(session)
    turn_counts = compute_turn_counts(turns)
    question_rate = compute_question_rate(turns)
    turn_length = compute_rep_turn_length_stats(turns)
    response_latency = compute_response_latency(turns)
    objection_coverage = compute_objection_coverage(scenario.objections, turns)
    name_usage = compute_customer_name_usage(turns)
    scorecard_text = _build_scorecard_text(evaluation)

    properties: dict[str, Any] = {
        "talk_time_coverage_score": {
            "type": "number",
            "description": (
                "0-100 — did the scorecard's feedback appropriately account for the actual talk-time "
                "balance below, when it was relevant to do so? Always include this field."
            ),
        },
        "talk_time_coverage_notes": {"type": "string"},
        "filler_word_coverage_score": {
            "type": "number",
            "description": (
                "0-100 — did the scorecard note fluency/filler-word issues if the rep's filler-word "
                "usage below was significant enough to matter? Always include this field."
            ),
        },
        "filler_word_coverage_notes": {"type": "string"},
        "objection_handling_accuracy_score": {
            "type": "number",
            "description": (
                "0-100 — is the scorecard's assessment of how objections were handled accurate and "
                "consistent with what actually happened in the transcript?"
            ),
        },
        "objection_handling_accuracy_notes": {"type": "string"},
    }
    required = [
        "talk_time_coverage_score",
        "talk_time_coverage_notes",
        "filler_word_coverage_score",
        "filler_word_coverage_notes",
        "objection_handling_accuracy_score",
        "objection_handling_accuracy_notes",
    ]
    if scenario.sales_framework:
        properties["framework_adherence_accuracy_score"] = {
            "type": "number",
            "description": (
                f"0-100 — does the scorecard accurately reflect adherence to the "
                f"{scenario.sales_framework} sales framework, even though the rubric may not have an "
                "explicit framework criterion? Always include this field."
            ),
        }
        properties["framework_adherence_accuracy_notes"] = {
            "type": "string",
            "description": "Always include this field, even if brief.",
        }
        required += ["framework_adherence_accuracy_score", "framework_adherence_accuracy_notes"]

    tool = {
        "name": "submit_transcript_analysis",
        "description": (
            "Submit an audit of the AI-generated Call Scorecard's accuracy and completeness — NOT a "
            "fresh grading of the rep. Every required field must be present in every call — never "
            "omit one."
        ),
        "input_schema": {"type": "object", "properties": properties, "required": required},
    }

    framework_line = (
        f"Also check whether the scorecard's assessment reflects adherence to the "
        f"{scenario.sales_framework} sales framework."
        if scenario.sales_framework
        else "No specific sales framework was configured for this scenario — skip framework scoring."
    )
    system_prompt = f"""You are auditing an AI-generated sales call "Call Scorecard" for accuracy and \
completeness. You are NOT re-grading the sales rep yourself — you are checking whether the scorecard \
below correctly and completely reflects what actually happened in the transcript, specifically \
regarding talk-time balance, filler-word/fluency issues, and objection handling. {framework_line}

COMPUTED METRICS (ground truth to check the scorecard against — do not recompute them):
- Rep talk-time: {talk_time["rep_talk_time_pct"]}% of words spoken ({talk_time["rep_words"]} rep words vs \
{talk_time["ai_words"]} customer words)
- Filler words used by the rep: {fillers["total"]} total, {fillers["per_100_words"]} per 100 words \
({fillers["by_word"] or "none detected"})

ADDITIONAL COMPUTED METRICS (context only, not separately scored — mention in your notes only if \
directly relevant to something the scorecard got wrong or missed):
- Call duration: {call_duration["seconds"]} seconds
- Turns: {turn_counts["rep_turns"]} rep, {turn_counts["ai_turns"]} customer
- Rep questions asked: {question_rate["questions_asked"]} ({question_rate["per_turn"]} per rep turn)
- Rep response length: {turn_length["average_words"]} words average, {turn_length["longest_words"]} words longest
- Rep response latency: {response_latency["average_seconds"]} seconds average
- Configured objections actually raised by the AI customer: {objection_coverage["raised_count"]}/\
{objection_coverage["configured_count"]}
- Customer name usage: {"detected name '" + name_usage["customer_name_detected"] + "', used by rep: " + str(name_usage["used_by_rep"]) if name_usage["customer_name_detected"] else "no name reliably detected"}

SCENARIO: {scenario.title}
CONFIGURED OBJECTIONS: {", ".join(scenario.objections) or "none specified"}

TRANSCRIPT:
{_build_transcript(turns)}

CALL SCORECARD TO AUDIT (this is what the rep was actually shown — judge its accuracy, not the rep):
{scorecard_text}"""

    result = await _call_claude_judge(system_prompt, "Audit this scorecard now.", tool)

    scores = {
        "talk_time_ratio": talk_time,
        "filler_words": fillers,
        "call_duration": call_duration,
        "turn_counts": turn_counts,
        "question_rate": question_rate,
        "rep_turn_length": turn_length,
        "response_latency": response_latency,
        "objection_coverage": objection_coverage,
        "customer_name_usage": name_usage,
        "talk_time_coverage_score": result["talk_time_coverage_score"],
        "talk_time_coverage_notes": result["talk_time_coverage_notes"],
        "filler_word_coverage_score": result["filler_word_coverage_score"],
        "filler_word_coverage_notes": result["filler_word_coverage_notes"],
        "objection_handling_accuracy_score": result["objection_handling_accuracy_score"],
        "objection_handling_accuracy_notes": result["objection_handling_accuracy_notes"],
        "framework_adherence_accuracy_score": result.get("framework_adherence_accuracy_score"),
        "framework_adherence_accuracy_notes": result.get("framework_adherence_accuracy_notes"),
        "sales_framework": scenario.sales_framework,
    }
    numeric = [v for k, v in scores.items() if k.endswith("_score") and isinstance(v, (int, float))]
    scores["overall_score"] = round(sum(numeric) / len(numeric), 1) if numeric else 0.0

    summary_parts = [
        result["talk_time_coverage_notes"],
        result["filler_word_coverage_notes"],
        result["objection_handling_accuracy_notes"],
    ]
    if scenario.sales_framework and result.get("framework_adherence_accuracy_notes"):
        summary_parts.append(result["framework_adherence_accuracy_notes"])
    return scores, " ".join(summary_parts)
