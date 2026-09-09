"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { TeamAnalytics as TeamAnalyticsData, analyticsApi } from "@/lib/analytics";
import { scoreColor } from "@/lib/scoreColor";

import { ScoreRow } from "./ScoreRow";

export function TeamAnalytics() {
  const [data, setData] = useState<TeamAnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    analyticsApi
      .team()
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load analytics"));
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return null;

  if (data.total_evaluated_sessions === 0) {
    return (
      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">Team analytics</h2>
        <p className="text-sm text-neutral-500">
          No completed, scored calls yet — once reps finish practice calls, team-wide performance
          shows up here.
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Team analytics</h2>
        {data.average_score !== null && (
          <span className={`text-lg font-bold ${scoreColor(data.average_score)}`}>
            {Math.round(data.average_score)}
            <span className="text-xs font-normal text-neutral-400">
              /100 avg &middot; {data.total_evaluated_sessions} calls scored
            </span>
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-neutral-700">Weakest skills</h3>
          {data.by_criterion.map((c) => (
            <ScoreRow key={c.name} label={c.name} sublabel={`${c.sample_count} scored`} score={c.average_score} />
          ))}
        </div>

        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-neutral-700">By rep</h3>
          {data.by_rep.map((r) => (
            <ScoreRow
              key={r.rep_id}
              label={r.rep_name}
              sublabel={`${r.sessions_completed} calls`}
              score={r.average_score}
            />
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold text-neutral-700">By scenario</h3>
        {data.by_scenario.map((s) => (
          <ScoreRow key={s.scenario_id} label={s.title} sublabel={`${s.attempts} attempts`} score={s.average_score} />
        ))}
      </div>
    </section>
  );
}
