"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardCard } from "@/components/DashboardCard";
import { RoleGuard } from "@/components/RoleGuard";
import { ApiError } from "@/lib/api";
import { MyProgress, analyticsApi } from "@/lib/analytics";
import { logout } from "@/lib/auth";
import { scoreColor } from "@/lib/scoreColor";
import { Scenario, scenariosApi } from "@/lib/scenarios";
import { stashSession } from "@/lib/sessionHandoff";
import { sessionsApi } from "@/lib/sessions";

const DIFFICULTY_STYLES: Record<Scenario["difficulty"], string> = {
  easy: "bg-green-100 text-green-800",
  medium: "bg-amber-100 text-amber-800",
  hard: "bg-red-100 text-red-800",
};

export default function PracticePage() {
  const router = useRouter();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [progress, setProgress] = useState<MyProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<string | null>(null);

  useEffect(() => {
    scenariosApi
      .list()
      .then(setScenarios)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load scenarios"));
    analyticsApi.myProgress().then(setProgress).catch(() => {});
  }, []);

  async function handleStart(scenarioId: string) {
    setError(null);
    setStartingId(scenarioId);
    try {
      const session = await sessionsApi.start(scenarioId, { voice: true });
      stashSession(session);
      router.push(`/practice/session/${session.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start session");
      setStartingId(null);
    }
  }

  return (
    <RoleGuard allow={["sales_rep"]}>
      {(user) => (
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 bg-neutral-50 px-4 py-12">
          <div className="flex items-center justify-between">
            <h1 className="flex items-center gap-2 text-2xl font-semibold">
              <span className="h-2.5 w-2.5 rounded-full bg-gradient-to-br from-indigo-600 to-amber-500" />
              Practice
            </h1>
            <button
              onClick={() => {
                logout();
                router.push("/login");
              }}
              className="text-sm text-neutral-500 hover:text-neutral-900"
            >
              Log out
            </button>
          </div>
          <p className="text-neutral-600">Welcome, {user.name}. Pick a scenario to start a practice call.</p>

          {progress && progress.entries.length > 0 && (
            <DashboardCard
              accent="bg-amber-500"
              title="Your progress"
              action={
                progress.average_score !== null && (
                  <span className={`whitespace-nowrap text-lg font-bold ${scoreColor(progress.average_score)}`}>
                    {Math.round(progress.average_score)}
                    <span className="text-xs font-normal text-neutral-400">/100 avg</span>
                  </span>
                )
              }
            >
              <div className="flex flex-wrap gap-2">
                {progress.entries.map((e) => (
                  <div
                    key={e.session_id}
                    title={`${e.scenario_title} — ${new Date(e.completed_at).toLocaleDateString()}`}
                    className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-medium text-white ${
                      e.overall_score >= 80
                        ? "bg-green-600"
                        : e.overall_score >= 60
                          ? "bg-amber-500"
                          : "bg-red-500"
                    }`}
                  >
                    {Math.round(e.overall_score)}
                  </div>
                ))}
              </div>
            </DashboardCard>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          <DashboardCard accent="bg-violet-600" title="Scenarios">
            {scenarios.length === 0 ? (
              <p className="text-sm text-neutral-500">
                No scenarios available yet — ask your team lead to create one.
              </p>
            ) : (
              <ul className="flex flex-col gap-4">
                {scenarios.map((s) => (
                  <li key={s.id} className="rounded border border-neutral-200 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{s.title}</p>
                        <p className="text-sm text-neutral-500">
                          {s.call_type === "cold_call" ? "Cold call" : "Support"} &middot;{" "}
                          <span
                            className={`rounded px-1.5 py-0.5 text-xs ${DIFFICULTY_STYLES[s.difficulty]}`}
                          >
                            {s.difficulty}
                          </span>
                        </p>
                      </div>
                      <button
                        onClick={() => handleStart(s.id)}
                        disabled={startingId === s.id}
                        className="shrink-0 rounded bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
                      >
                        {startingId === s.id ? "Starting..." : "Start practice call"}
                      </button>
                    </div>

                    <div className="mt-4 flex flex-col gap-4 border-t border-neutral-100 pt-4 text-sm">
                      <div>
                        <h3 className="mb-1 font-semibold text-neutral-700">Who you&apos;ll be talking to</h3>
                        <p className="text-neutral-600">{s.persona_description}</p>
                      </div>

                      {s.objections.length > 0 && (
                        <div>
                          <h3 className="mb-1 font-semibold text-neutral-700">
                            Objections you may need to handle
                          </h3>
                          <ul className="list-inside list-disc text-neutral-600">
                            {s.objections.map((o, i) => (
                              <li key={i}>{o}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div>
                        <h3 className="mb-1 font-semibold text-neutral-700">How you&apos;ll be scored</h3>
                        <ul className="flex flex-col gap-1 text-neutral-600">
                          {s.rubric_criteria.map((c) => (
                            <li key={c.name}>
                              <span className="font-medium text-neutral-800">{c.name}</span>{" "}
                              <span className="text-xs text-neutral-400">({c.weight}%)</span>
                              {c.description && <span> &mdash; {c.description}</span>}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </DashboardCard>
        </main>
      )}
    </RoleGuard>
  );
}
