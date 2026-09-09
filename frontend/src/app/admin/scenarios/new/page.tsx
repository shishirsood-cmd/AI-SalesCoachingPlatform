"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { RoleGuard } from "@/components/RoleGuard";
import { ScenarioForm } from "@/components/ScenarioForm";
import { scenariosApi } from "@/lib/scenarios";

export default function NewScenarioPage() {
  const router = useRouter();

  return (
    <RoleGuard allow={["team_lead"]}>
      {() => (
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-12">
          <div>
            <Link href="/admin" className="text-sm underline">
              &larr; Back to dashboard
            </Link>
          </div>
          <h1 className="text-2xl font-semibold">New scenario</h1>
          <ScenarioForm
            submitLabel="Create scenario"
            onSubmit={async (input) => {
              await scenariosApi.create(input);
              router.push("/admin");
            }}
          />
        </main>
      )}
    </RoleGuard>
  );
}
