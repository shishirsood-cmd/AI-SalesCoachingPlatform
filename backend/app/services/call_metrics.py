import re
from collections import Counter
from typing import Any

from app.models.session import Speaker, SimulationSession, Turn

FILLER_WORDS = [
    "um", "umm", "uh", "uhh", "like", "you know", "i mean", "actually",
    "basically", "sort of", "kind of", "so yeah",
]


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
        return {"average_words": 0.0, "longest_words": 0, "stdev_words": 0.0, "rep_turns": 0}
    average = sum(rep_word_counts) / len(rep_word_counts)
    variance = sum((w - average) ** 2 for w in rep_word_counts) / len(rep_word_counts)
    return {
        "average_words": round(average, 1),
        "longest_words": max(rep_word_counts),
        "stdev_words": round(variance**0.5, 1),
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
        return {"average_seconds": None, "max_seconds": None, "samples": 0}
    return {
        "average_seconds": round(sum(deltas) / len(deltas), 1),
        "max_seconds": round(max(deltas), 1),
        "samples": len(deltas),
    }


def compute_speaking_pace(session: SimulationSession, turns: list[Turn]) -> dict[str, Any]:
    """Rep's words per minute of call time. Since call duration includes the customer's
    speaking time too, this is a rough pace proxy, not the rep's true words-per-minute
    while actually talking."""
    if session.ended_at is None:
        return {"words_per_minute": None, "note": "Call not yet ended."}
    minutes = (session.ended_at - session.started_at).total_seconds() / 60
    rep_words = sum(len(t.content.split()) for t in turns if t.speaker == Speaker.rep)
    if minutes <= 0:
        return {"words_per_minute": None, "note": "Call duration too short to compute a rate."}
    return {"words_per_minute": round(rep_words / minutes, 1)}


def compute_talk_time_trend(turns: list[Turn]) -> dict[str, Any]:
    """Rep talk-time % in the first half vs. second half of the call (split by turn count,
    not elapsed time or word count) — shows whether the rep faded out or took over as the
    call went on."""
    if len(turns) < 2:
        return {
            "first_half_rep_pct": None,
            "second_half_rep_pct": None,
            "note": "Call too short to split into halves.",
        }

    def rep_pct(subset: list[Turn]) -> float:
        rep_words = sum(len(t.content.split()) for t in subset if t.speaker == Speaker.rep)
        ai_words = sum(len(t.content.split()) for t in subset if t.speaker == Speaker.ai_customer)
        total = rep_words + ai_words
        return round(100 * rep_words / total, 1) if total else 0.0

    mid = len(turns) // 2
    return {
        "first_half_rep_pct": rep_pct(turns[:mid]),
        "second_half_rep_pct": rep_pct(turns[mid:]),
    }


def compute_call_metrics(session: SimulationSession, turns: list[Turn]) -> dict[str, Any]:
    """Bundles every deterministic, code-computed call metric into one dict. Used both to
    publish a mandatory 'Call metrics' section on the rep-facing Call Scorecard (so it isn't
    graded on metrics it was never given), and as the ground truth for the Transcript
    Analysis AI Quality Eval."""
    return {
        "talk_time_ratio": compute_talk_time_ratio(turns),
        "filler_words": compute_filler_word_count(turns),
        "call_duration": compute_call_duration(session),
        "turn_counts": compute_turn_counts(turns),
        "question_rate": compute_question_rate(turns),
        "rep_turn_length": compute_rep_turn_length_stats(turns),
        "response_latency": compute_response_latency(turns),
        "speaking_pace": compute_speaking_pace(session, turns),
        "talk_time_trend": compute_talk_time_trend(turns),
    }
