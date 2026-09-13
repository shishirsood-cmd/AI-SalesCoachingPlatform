"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardCard } from "@/components/DashboardCard";
import { RoleGuard } from "@/components/RoleGuard";
import { ScenarioForm } from "@/components/ScenarioForm";
import { ApiError } from "@/lib/api";
import { Scenario, scenariosApi } from "@/lib/scenarios";

export default function EditScenarioPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    scenariosApi
      .get(params.id)
      .then(setScenario)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load scenario"));
  }, [params.id]);

  async function handleDelete() {
    if (!confirm("Delete this scenario? This can't be undone.")) return;
    setDeleting(true);
    try {
      await scenariosApi.remove(params.id);
      router.push("/admin");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete scenario");
      setDeleting(false);
    }
  }

  return (
    <RoleGuard allow={["team_lead"]}>
      {() => (
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 bg-neutral-50 px-4 py-12">
          <div>
            <Link href="/admin" className="text-sm text-indigo-600 hover:text-indigo-700">
              &larr; Back to dashboard
            </Link>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          {scenario ? (
            <DashboardCard
              accent="bg-violet-600"
              title="Edit scenario"
              action={
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="whitespace-nowrap text-sm text-red-600 hover:text-red-700 disabled:opacity-50"
                >
                  {deleting ? "Deleting..." : "Delete scenario"}
                </button>
              }
            >
              <ScenarioForm
                initial={scenario}
                submitLabel="Save changes"
                onSubmit={async (input) => {
                  await scenariosApi.update(params.id, input);
                  router.push("/admin");
                }}
              />
            </DashboardCard>
          ) : (
            !error && <p className="text-sm text-neutral-500">Loading...</p>
          )}
        </main>
      )}
    </RoleGuard>
  );
}
