"use client";

import { useState } from "react";

import { AIQualityEvals, aiQualityApi } from "@/lib/aiQuality";
import { ApiError } from "@/lib/api";

import { DashboardCard } from "./DashboardCard";
import { ScoreRow } from "./ScoreRow";

function IssueList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-green-700">None found.</p>;
  }
  return (
    <ul className="list-inside list-disc text-sm text-red-600">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

export function AIQualityPanel({
  sessionId,
  initial,
}: {
  sessionId: string;
  initial: AIQualityEvals;
}) {
  const [evals, setEvals] = useState<AIQualityEvals>(initial);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasAny = evals.transcript_analysis || evals.roleplay_simulation || evals.coaching_safety;

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      setEvals(await aiQualityApi.run(sessionId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to run AI quality evals");
    } finally {
      setRunning(false);
    }
  }

  return (
    <DashboardCard
      accent="bg-rose-600"
      title="AI Quality"
      action={
        <button
          onClick={handleRun}
          disabled={running}
          className="whitespace-nowrap rounded bg-rose-600 px-4 py-2 text-sm text-white hover:bg-rose-700 disabled:opacity-50"
        >
          {running ? "Running..." : hasAny ? "Re-run evals" : "Run AI Quality Eval"}
        </button>
      }
    >
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!hasAny && !running && (
        <p className="text-sm text-neutral-500">
          Grades the platform&apos;s own AI — not the rep — on transcript analysis accuracy, roleplay
          realism, and coaching feedback safety.
        </p>
      )}

      {evals.transcript_analysis && (
        <div className="flex flex-col gap-3 border-t border-neutral-100 pt-4">
          <h3 className="text-sm font-semibold text-neutral-700">Transcript Analysis</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 text-sm text-neutral-600">
            <div>
              <p className="font-medium text-neutral-800">Talk-time ratio</p>
              <p>
                Rep {evals.transcript_analysis.scores.talk_time_ratio.rep_talk_time_pct}% &middot; AI
                customer {(100 - evals.transcript_analysis.scores.talk_time_ratio.rep_talk_time_pct).toFixed(1)}%
              </p>
              <p className="text-xs text-neutral-400">{evals.transcript_analysis.scores.talk_time_ratio.note}</p>
            </div>
            <div>
              <p className="font-medium text-neutral-800">Filler words (rep)</p>
              <p>
                {evals.transcript_analysis.scores.filler_words.total} total &middot;{" "}
                {evals.transcript_analysis.scores.filler_words.per_100_words} per 100 words
              </p>
            </div>
          </div>
          <ScoreRow
            label="Objection handling"
            score={evals.transcript_analysis.scores.objection_handling_score}
          />
          <p className="text-sm text-neutral-600">{evals.transcript_analysis.scores.objection_handling_notes}</p>
          {evals.transcript_analysis.scores.framework_adherence_score !== null && (
            <>
              <ScoreRow
                label={`Framework adherence${
                  evals.transcript_analysis.scores.sales_framework
                    ? ` (${evals.transcript_analysis.scores.sales_framework})`
                    : ""
                }`}
                score={evals.transcript_analysis.scores.framework_adherence_score}
              />
              <p className="text-sm text-neutral-600">
                {evals.transcript_analysis.scores.framework_adherence_notes}
              </p>
            </>
          )}
        </div>
      )}

      {evals.roleplay_simulation && (
        <div className="flex flex-col gap-3 border-t border-neutral-100 pt-4">
          <h3 className="text-sm font-semibold text-neutral-700">Roleplay Simulation</h3>
          <ScoreRow label="Stayed in character" score={evals.roleplay_simulation.scores.stayed_in_character_score} />
          <ScoreRow label="Realistic pushback" score={evals.roleplay_simulation.scores.realistic_pushback_score} />
          <ScoreRow label="Scenario adherence" score={evals.roleplay_simulation.scores.scenario_adherence_score} />
          <p className="text-sm text-neutral-600">{evals.roleplay_simulation.summary}</p>
        </div>
      )}

      {evals.coaching_safety && (
        <div className="flex flex-col gap-3 border-t border-neutral-100 pt-4">
          <h3 className="text-sm font-semibold text-neutral-700">Coaching Tone &amp; Safety</h3>
          <ScoreRow
            label="Tactical & constructive"
            score={evals.coaching_safety.scores.tactical_constructive_score}
          />
          <ScoreRow label="Hallucination-free" score={evals.coaching_safety.scores.hallucination_free_score} />
          <IssueList items={evals.coaching_safety.scores.hallucination_issues} />
          {evals.coaching_safety.scores.compliance_score !== null && (
            <>
              <ScoreRow label="Compliance" score={evals.coaching_safety.scores.compliance_score} />
              <IssueList items={evals.coaching_safety.scores.compliance_issues} />
            </>
          )}
          <p className="text-sm text-neutral-600">{evals.coaching_safety.summary}</p>
        </div>
      )}
    </DashboardCard>
  );
}
