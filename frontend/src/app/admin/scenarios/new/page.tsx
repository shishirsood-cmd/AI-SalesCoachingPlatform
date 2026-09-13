"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { DashboardCard } from "@/components/DashboardCard";
import { RoleGuard } from "@/components/RoleGuard";
import { ScenarioForm } from "@/components/ScenarioForm";
import { scenariosApi } from "@/lib/scenarios";

export default function NewScenarioPage() {
  const router = useRouter();

  return (
    <RoleGuard allow={["team_lead"]}>
      {() => (
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 bg-neutral-50 px-4 py-12">
          <div>
            <Link href="/admin" className="text-sm text-indigo-600 hover:text-indigo-700">
              &larr; Back to dashboard
            </Link>
          </div>
          <DashboardCard accent="bg-violet-600" title="New scenario">
            <ScenarioForm
              submitLabel="Create scenario"
              onSubmit={async (input) => {
                await scenariosApi.create(input);
                router.push("/admin");
              }}
            />
          </DashboardCard>
        </main>
      )}
    </RoleGuard>
  );
}
