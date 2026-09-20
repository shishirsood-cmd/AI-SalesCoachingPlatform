"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardCard } from "@/components/DashboardCard";
import { InviteCode } from "@/components/InviteCode";
import { KnowledgeBase } from "@/components/KnowledgeBase";
import { RecentCalls } from "@/components/RecentCalls";
import { RoleGuard } from "@/components/RoleGuard";
import { TeamAnalytics } from "@/components/TeamAnalytics";
import { ApiError } from "@/lib/api";
import { logout } from "@/lib/auth";
import { Scenario, scenariosApi } from "@/lib/scenarios";

const DIFFICULTY_STYLES: Record<Scenario["difficulty"], string> = {
  easy: "bg-green-100 text-green-800",
  medium: "bg-amber-100 text-amber-800",
  hard: "bg-red-100 text-red-800",
};

export default function AdminPage() {
  const router = useRouter();
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    scenariosApi
      .list()
      .then(setScenarios)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load scenarios"));
  }, []);

  return (
    <RoleGuard allow={["team_lead"]}>
      {(user) => (
        <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 bg-neutral-50 px-4 py-12">
          <div className="flex items-center justify-between">
            <h1 className="flex items-center gap-2 text-2xl font-semibold">
              <span className="h-2.5 w-2.5 rounded-full bg-gradient-to-br from-indigo-600 to-amber-500" />
              Team Lead Dashboard
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
          <p className="text-neutral-600">Welcome, {user.name}.</p>

          <InviteCode />

          <DashboardCard
            accent="bg-violet-600"
            title="Scenarios"
            action={
              <Link
                href="/admin/scenarios/new"
                className="whitespace-nowrap text-sm text-indigo-600 hover:text-indigo-700"
              >
                + New scenario
              </Link>
            }
          >
            {error && <p className="text-sm text-red-600">{error}</p>}
            {scenarios.length === 0 ? (
              <p className="text-sm text-neutral-500">
                No scenarios yet. Create one to start building your reps&apos; practice library.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {scenarios.map((s) => (
                  <li key={s.id}>
                    <Link
                      href={`/admin/scenarios/${s.id}`}
                      className="flex items-center justify-between rounded border border-neutral-200 px-3 py-2 hover:border-violet-300"
                    >
                      <div>
                        <p className="text-sm font-medium">{s.title}</p>
                        <p className="text-xs text-neutral-500">
                          {s.call_type === "cold_call" ? "Cold call" : "Support"} &middot;{" "}
                          {s.rubric_criteria.length} rubric criteria
                        </p>
                      </div>
                      <span className={`rounded px-2 py-0.5 text-xs ${DIFFICULTY_STYLES[s.difficulty]}`}>
                        {s.difficulty}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </DashboardCard>

          <TeamAnalytics />

          <RecentCalls />

          <KnowledgeBase />
        </main>
      )}
    </RoleGuard>
  );
}
