"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

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
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-12">
          <div className="flex items-center justify-between">
            <Link href="/admin" className="text-sm underline">
              &larr; Back to dashboard
            </Link>
            {scenario && (
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="text-sm text-red-600 underline disabled:opacity-50"
              >
                {deleting ? "Deleting..." : "Delete scenario"}
              </button>
            )}
          </div>
          <h1 className="text-2xl font-semibold">Edit scenario</h1>
          {error && <p className="text-sm text-red-600">{error}</p>}
          {scenario ? (
            <ScenarioForm
              initial={scenario}
              submitLabel="Save changes"
              onSubmit={async (input) => {
                await scenariosApi.update(params.id, input);
                router.push("/admin");
              }}
            />
          ) : (
            !error && <p className="text-sm text-neutral-500">Loading...</p>
          )}
        </main>
      )}
    </RoleGuard>
  );
}
