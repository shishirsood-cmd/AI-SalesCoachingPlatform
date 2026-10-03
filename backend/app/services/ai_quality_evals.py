import re
from typing import Any

import anthropic

from app.core.config import settings
from app.models.evaluation import Evaluation
from app.models.scenario import Scenario
from app.models.session import SimulationSession, Speaker, Turn
from app.services.anthropic_client import get_client
from app.services.call_metrics import compute_call_metrics

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
                model=settings.claude_eval_model,
                max_tokens=4096,
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


def _manual_block(manual_context: list[str]) -> str:
    return "\n\n".join(manual_context) if manual_context else "(no product documentation is available for this organization)"


def _format_call_metrics(call_metrics: dict[str, Any]) -> str:
    if not call_metrics:
        return "(not published on this scorecard)"
    talk_time = call_metrics["talk_time_ratio"]
    fillers = call_metrics["filler_words"]
    turn_length = call_metrics["rep_turn_length"]
    turn_counts = call_metrics["turn_counts"]
    return (
        f"Rep talk-time {talk_time['rep_talk_time_pct']}%; "
        f"filler words {fillers['total']} total ({fillers['per_100_words']} per 100 words); "
        f"{turn_counts['rep_turns']} rep turns / {turn_counts['ai_turns']} customer turns; "
        f"rep response length {turn_length['average_words']} words average, "
        f"{turn_length['longest_words']} words longest"
    )


def _build_scorecard_text(evaluation: Evaluation) -> str:
    criteria_lines = "\n".join(
        f"- {c['name']} ({c['score']}/100): {c['feedback']}" for c in evaluation.criteria_scores
    )
    return f"""Overall score: {evaluation.overall_score}/100
Summary: {evaluation.summary}
Published call metrics: {_format_call_metrics(evaluation.call_metrics)}
Per-criterion scores:
{criteria_lines}
Strengths: {"; ".join(evaluation.strengths)}
Areas for improvement: {"; ".join(evaluation.areas_for_improvement)}"""


async def run_transcript_analysis(
    scenario: Scenario,
    turns: list[Turn],
    evaluation: Evaluation,
    session: SimulationSession,
    manual_context: list[str],
) -> tuple[dict[str, Any], str]:
    """Audits the *Call Scorecard* (the rubric-based Evaluation Claude already produced for the
    rep) across three dimensions — NOT a re-grading of the rep. All transcript-level metrics
    below are computed deterministically in code (no LLM judgment, so no cost or flakiness) and
    given to Claude as ground truth; Claude only judges whether the scorecard represents them
    (and the rep's tone/objectivity of feedback) accurately."""
    call_metrics = compute_call_metrics(session, turns)
    talk_time = call_metrics["talk_time_ratio"]
    fillers = call_metrics["filler_words"]
    call_duration = call_metrics["call_duration"]
    turn_counts = call_metrics["turn_counts"]
    question_rate = call_metrics["question_rate"]
    turn_length = call_metrics["rep_turn_length"]
    response_latency = call_metrics["response_latency"]
    speaking_pace = call_metrics["speaking_pace"]
    talk_time_trend = call_metrics["talk_time_trend"]
    objection_coverage = compute_objection_coverage(scenario.objections, turns)
    name_usage = compute_customer_name_usage(turns)
    scorecard_text = _build_scorecard_text(evaluation)
    other_criteria = ", ".join(c["name"] for c in scenario.rubric_criteria) or "(none configured)"

    tool = {
        "name": "submit_transcript_analysis",
        "description": (
            "Submit a 3-part audit of the AI-generated Call Scorecard's accuracy and "
            "completeness — NOT a fresh grading of the rep. All 6 fields are always required, "
            "even when a score is a perfect 100 — never omit one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics_accuracy_score": {
                    "type": "number",
                    "description": (
                        "0-100 — how accurately and completely does the scorecard reflect the "
                        "computed metrics below (talk-time balance, filler words, turn counts, "
                        "response length)? Weigh factually wrong claims heavily; weigh omitted "
                        "context that wasn't very relevant lightly. Always include this field."
                    ),
                },
                "metrics_accuracy_notes": {"type": "string"},
                "tone_confidence_score": {
                    "type": "number",
                    "description": (
                        "0-100 — based on the rep's actual word choice and phrasing in the "
                        "transcript (hedging language like 'I think'/'maybe', filler, assertive "
                        "vs. tentative statements — a TEXT-BASED PROXY, not real vocal/audio "
                        "analysis, since no audio is available), does the scorecard's "
                        "characterization of the rep's tone, confidence, and assertiveness match "
                        "what the transcript actually shows? Always include this field."
                    ),
                },
                "tone_confidence_notes": {
                    "type": "string",
                    "description": (
                        "State what tone/confidence you infer from the transcript's wording, and "
                        "whether the scorecard's characterization matches it. Always include this "
                        "field."
                    ),
                },
                "feedback_objectivity_score": {
                    "type": "number",
                    "description": (
                        "0-100 — for the scenario's OTHER rubric criteria (i.e. everything besides "
                        "raw metrics/tone — e.g. value reinforcement, discovery, closing), is the "
                        "scorecard's feedback objective and evidence-backed (specific quotes or "
                        "concrete moments from the transcript) rather than vague, generic, or "
                        "unsupported? Always include this field."
                    ),
                },
                "feedback_objectivity_notes": {"type": "string"},
            },
            "required": [
                "metrics_accuracy_score",
                "metrics_accuracy_notes",
                "tone_confidence_score",
                "tone_confidence_notes",
                "feedback_objectivity_score",
                "feedback_objectivity_notes",
            ],
        },
    }

    framework_line = (
        f"When judging feedback objectivity, also check whether the scorecard's framework-adherence "
        f"commentary (the configured sales framework is {scenario.sales_framework}) is objective and "
        f"evidence-backed, not just asserted."
        if scenario.sales_framework
        else ""
    )
    system_prompt = f"""You are auditing an AI-generated sales call "Call Scorecard" for accuracy and \
completeness. You are NOT re-grading the sales rep yourself — you are checking whether the scorecard \
below correctly and completely reflects what actually happened in the transcript, across three \
dimensions: (1) the computed metrics, (2) the rep's tone/confidence as evident from their wording, \
and (3) whether feedback on the scenario's other rubric criteria is objective and evidence-backed \
rather than vague. {framework_line}

COMPUTED METRICS (ground truth to check the scorecard against — do not recompute them):
- Rep talk-time: {talk_time["rep_talk_time_pct"]}% of words spoken ({talk_time["rep_words"]} rep words vs \
{talk_time["ai_words"]} customer words)
- Filler words used by the rep: {fillers["total"]} total, {fillers["per_100_words"]} per 100 words \
({fillers["by_word"] or "none detected"})
- Call duration: {call_duration["seconds"]} seconds
- Turns: {turn_counts["rep_turns"]} rep, {turn_counts["ai_turns"]} customer
- Rep questions asked: {question_rate["questions_asked"]} ({question_rate["per_turn"]} per rep turn)
- Rep response length: {turn_length["average_words"]} words average (std dev {turn_length["stdev_words"]}), \
{turn_length["longest_words"]} words longest
- Rep response latency: {response_latency["average_seconds"]} seconds average, \
{response_latency["max_seconds"]} seconds longest single pause
- Rep speaking pace: {speaking_pace["words_per_minute"]} words/minute
- Rep talk-time trend: {talk_time_trend["first_half_rep_pct"]}% in the first half of the call vs \
{talk_time_trend["second_half_rep_pct"]}% in the second half
- Configured objections actually raised by the AI customer: {objection_coverage["raised_count"]}/\
{objection_coverage["configured_count"]}
- Customer name usage: {"detected name '" + name_usage["customer_name_detected"] + "', used by rep: " + str(name_usage["used_by_rep"]) if name_usage["customer_name_detected"] else "no name reliably detected"}

SCENARIO: {scenario.title}
SCENARIO'S RUBRIC CRITERIA: {other_criteria}

PRODUCT MANUAL EXCERPTS (ground truth for this product). Use them to check every statement the \
scorecard makes about product facts or about what the manual says: a scorecard claim that a rep's \
product statement was right or wrong is only accurate if the excerpts support it, and a scorecard \
claim about the manual's contents that the excerpts do not support is an inaccuracy. If no \
documentation is available, do not penalize the scorecard for product-fact claims you cannot verify:
{_manual_block(manual_context)}

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
        "speaking_pace": speaking_pace,
        "talk_time_trend": talk_time_trend,
        "metrics_accuracy_score": result["metrics_accuracy_score"],
        "metrics_accuracy_notes": result["metrics_accuracy_notes"],
        "tone_confidence_score": result["tone_confidence_score"],
        "tone_confidence_notes": result["tone_confidence_notes"],
        "feedback_objectivity_score": result["feedback_objectivity_score"],
        "feedback_objectivity_notes": result["feedback_objectivity_notes"],
        "sales_framework": scenario.sales_framework,
    }
    summary = " ".join(
        [result["metrics_accuracy_notes"], result["tone_confidence_notes"], result["feedback_objectivity_notes"]]
    )
    return scores, summary


async def run_customer_persona_eval(
    scenario: Scenario, turns: list[Turn], manual_context: list[str]
) -> tuple[dict[str, Any], str]:
    """Grades the AI customer persona itself — NOT the rep or the scorecard — on whether it
    stayed in character and actually raised the configured objections during the call."""
    objection_coverage = compute_objection_coverage(scenario.objections, turns)

    tool = {
        "name": "submit_customer_persona_eval",
        "description": (
            "Submit an evaluation of the AI customer persona's fidelity to the scenario. Both "
            "fields are always required, even when a score is a perfect 100 — never omit one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "stayed_in_character_score": {
                    "type": "number",
                    "description": (
                        "0-100 — did the AI customer ever break character, mention being an AI, "
                        "coach the rep, or narrate stage directions? 100 means fully in character "
                        "throughout. Always include this field."
                    ),
                },
                "stayed_in_character_notes": {"type": "string"},
                "raised_objections_score": {
                    "type": "number",
                    "description": (
                        "0-100 — of the configured objections, how many did the AI customer "
                        "actually raise naturally during the call (see the word-overlap-based "
                        "count below as a rough signal, but judge from the actual transcript "
                        "wording, since paraphrased objections can be missed by that heuristic)? "
                        "100 means all configured objections were raised naturally. Always "
                        "include this field."
                    ),
                },
                "raised_objections_notes": {"type": "string"},
            },
            "required": [
                "stayed_in_character_score",
                "stayed_in_character_notes",
                "raised_objections_score",
                "raised_objections_notes",
            ],
        },
    }

    system_prompt = f"""You are an AI QA reviewer grading the *simulated customer persona* in this training \
call transcript — NOT the sales rep. Judge only the "Customer" turns, on (1) whether it stayed fully in \
character and (2) whether it actually raised the configured objections.

SCENARIO: {scenario.title} ({scenario.call_type.value}, {scenario.difficulty.value} difficulty)
CONFIGURED PERSONA: {scenario.persona_description}
CONFIGURED OBJECTIONS THE PERSONA SHOULD RAISE: {", ".join(scenario.objections) or "none specified"}

DETERMINISTIC OBJECTION-COVERAGE CHECK (word-overlap heuristic, a rough signal only — \
{objection_coverage["raised_count"]}/{objection_coverage["configured_count"]} objections matched; \
may miss heavily paraphrased ones): {objection_coverage["raised"] or "none matched"}

PRODUCT MANUAL EXCERPTS (the only product facts the persona was allowed to rely on; it was told \
not to invent facts beyond them). If the Customer states product facts that contradict or go beyond \
these excerpts, deduct from stayed_in_character_score and say so in its notes. If no documentation is \
available, do not penalize product-fact statements you cannot verify:
{_manual_block(manual_context)}

TRANSCRIPT:
{_build_transcript(turns)}"""

    result = await _call_claude_judge(system_prompt, "Evaluate the AI customer persona now.", tool)

    scores = {
        "objection_coverage": objection_coverage,
        "stayed_in_character_score": result["stayed_in_character_score"],
        "stayed_in_character_notes": result["stayed_in_character_notes"],
        "raised_objections_score": result["raised_objections_score"],
        "raised_objections_notes": result["raised_objections_notes"],
    }
    summary = " ".join([result["stayed_in_character_notes"], result["raised_objections_notes"]])
    return scores, summary
