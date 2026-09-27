"use client";

import { Evaluation } from "@/lib/evaluations";
import { barColor, scoreColor } from "@/lib/scoreColor";

export function Scorecard({ evaluation }: { evaluation: Evaluation }) {
  return (
    <div className="flex flex-col gap-6 rounded border border-neutral-200 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Call scorecard</h2>
        <div className={`text-3xl font-bold ${scoreColor(evaluation.overall_score)}`}>
          {Math.round(evaluation.overall_score)}
          <span className="text-base font-normal text-neutral-400">/100</span>
        </div>
      </div>

      <p className="text-sm text-neutral-700">{evaluation.summary}</p>

      {evaluation.call_metrics && Object.keys(evaluation.call_metrics).length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold text-neutral-700">Call metrics</h3>
          <div className="grid grid-cols-2 gap-3 rounded border border-neutral-100 bg-neutral-50 p-3 text-sm text-neutral-600 sm:grid-cols-4">
            <div>
              <p className="text-xs text-neutral-400">Talk-time ratio</p>
              <p className="font-medium text-neutral-800">
                {evaluation.call_metrics.talk_time_ratio.rep_talk_time_pct}% rep
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-400">Filler words</p>
              <p className="font-medium text-neutral-800">
                {evaluation.call_metrics.filler_words.total} total (
                {evaluation.call_metrics.filler_words.per_100_words}/100w)
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-400">Turns</p>
              <p className="font-medium text-neutral-800">
                {evaluation.call_metrics.turn_counts.rep_turns} rep /{" "}
                {evaluation.call_metrics.turn_counts.ai_turns} customer
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-400">Rep response length</p>
              <p className="font-medium text-neutral-800">
                {evaluation.call_metrics.rep_turn_length.average_words}w avg /{" "}
                {evaluation.call_metrics.rep_turn_length.longest_words}w longest
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-400">Call duration</p>
              <p className="font-medium text-neutral-800">
                {evaluation.call_metrics.call_duration.seconds !== null
                  ? `${evaluation.call_metrics.call_duration.seconds}s`
                  : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs text-neutral-400">Rep response latency</p>
              <p className="font-medium text-neutral-800">
                {evaluation.call_metrics.response_latency.average_seconds !== null
                  ? `${evaluation.call_metrics.response_latency.average_seconds}s avg`
                  : "—"}
              </p>
            </div>
            <div className="col-span-2">
              <p className="text-xs text-neutral-400">Rep speaking pace</p>
              <p className="font-medium text-neutral-800">
                {evaluation.call_metrics.speaking_pace.words_per_minute !== null
                  ? `${evaluation.call_metrics.speaking_pace.words_per_minute} wpm`
                  : "—"}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {evaluation.criteria_scores.map((c) => (
          <div key={c.name} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{c.name}</span>
              <span className={scoreColor(c.score)}>{Math.round(c.score)}/100</span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-100">
              <div
                className={`h-full rounded-full ${barColor(c.score)}`}
                style={{ width: `${Math.max(0, Math.min(100, c.score))}%` }}
              />
            </div>
            <p className="text-sm text-neutral-600">{c.feedback}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold text-green-700">Strengths</h3>
          <ul className="flex flex-col gap-1 text-sm text-neutral-700">
            {evaluation.strengths.map((s, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-green-600">+</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold text-amber-700">Areas for improvement</h3>
          <ul className="flex flex-col gap-1 text-sm text-neutral-700">
            {evaluation.areas_for_improvement.map((s, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-amber-600">&rarr;</span>
                {s}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
