"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { scoreColor } from "@/lib/scoreColor";
import { OrgSessionSummary, sessionsApi } from "@/lib/sessions";

import { DashboardCard } from "./DashboardCard";

export function RecentCalls() {
  const [sessions, setSessions] = useState<OrgSessionSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    sessionsApi
      .listForTeam()
      .then(setSessions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load calls"));
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;

  const completed = sessions.filter((s) => s.status === "completed").slice(0, 10);

  return (
    <DashboardCard accent="bg-sky-600" title="Recent calls">
      {completed.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No completed calls yet — once reps finish practice calls, they&apos;ll show up here for
          you to review.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {completed.map((s) => (
            <li key={s.id}>
              <Link
                href={`/admin/sessions/${s.id}?rep=${encodeURIComponent(s.rep_name)}&scenario=${encodeURIComponent(s.scenario_title)}`}
                className="flex items-center justify-between rounded border border-neutral-200 px-3 py-2 hover:border-sky-300"
              >
                <div>
                  <p className="text-sm font-medium">{s.rep_name}</p>
                  <p className="text-xs text-neutral-500">
                    {s.scenario_title} &middot; {new Date(s.started_at).toLocaleDateString()}
                  </p>
                </div>
                {s.overall_score !== null && (
                  <span className={`text-sm font-semibold ${scoreColor(s.overall_score)}`}>
                    {Math.round(s.overall_score)}/100
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </DashboardCard>
  );
}
