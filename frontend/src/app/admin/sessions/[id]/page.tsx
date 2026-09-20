"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AIQualityPanel } from "@/components/AIQualityPanel";
import { RoleGuard } from "@/components/RoleGuard";
import { Scorecard } from "@/components/Scorecard";
import { AIQualityEvals, aiQualityApi } from "@/lib/aiQuality";
import { ApiError } from "@/lib/api";
import { Evaluation, evaluationsApi } from "@/lib/evaluations";
import { SimulationSession, sessionsApi } from "@/lib/sessions";

export default function SessionDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const [session, setSession] = useState<SimulationSession | null>(null);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [aiQuality, setAiQuality] = useState<AIQualityEvals | null>(null);
  const [error, setError] = useState<string | null>(null);

  const repLabel = searchParams.get("rep");
  const scenarioLabel = searchParams.get("scenario");

  useEffect(() => {
    sessionsApi
      .get(params.id)
      .then(setSession)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load call"));
    evaluationsApi
      .get(params.id)
      .then(setEvaluation)
      .catch(() => {});
    aiQualityApi
      .get(params.id)
      .then(setAiQuality)
      .catch(() => {});
  }, [params.id]);

  return (
    <RoleGuard allow={["team_lead"]}>
      {() => (
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 bg-neutral-50 px-4 py-12">
          <div>
            <Link href="/admin" className="text-sm text-indigo-600 hover:text-indigo-700">
              &larr; Back to dashboard
            </Link>
          </div>

          <div>
            <h1 className="text-2xl font-semibold">{repLabel ? `${repLabel}'s call` : "Call detail"}</h1>
            {scenarioLabel && <p className="text-neutral-600">{scenarioLabel}</p>}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          {!session ? (
            !error && <p className="text-sm text-neutral-500">Loading...</p>
          ) : (
            <>
              <div className="flex max-h-96 flex-col gap-3 overflow-y-auto rounded border border-neutral-200 bg-white p-4">
                {session.turns.map((turn) => (
                  <div
                    key={turn.id}
                    className={`max-w-[80%] rounded px-3 py-2 text-sm ${
                      turn.speaker === "rep"
                        ? "self-end bg-indigo-600 text-white"
                        : "self-start bg-neutral-100 text-neutral-900"
                    }`}
                  >
                    {turn.content}
                  </div>
                ))}
              </div>

              {evaluation ? (
                <Scorecard evaluation={evaluation} />
              ) : (
                <p className="text-sm text-neutral-500">
                  This call hasn&apos;t been scored yet — running an AI Quality Eval below will also
                  generate the rep&apos;s scorecard.
                </p>
              )}

              {aiQuality && <AIQualityPanel sessionId={session.id} initial={aiQuality} />}
            </>
          )}
        </main>
      )}
    </RoleGuard>
  );
}
