"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiError } from "@/lib/api";
import { registerOrg } from "@/lib/auth";

export default function RegisterOrgPage() {
  const router = useRouter();
  const [orgName, setOrgName] = useState("");
  const [adminName, setAdminName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [inviteCode, setInviteCode] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await registerOrg({
        org_name: orgName,
        admin_name: adminName,
        admin_email: email,
        admin_password: password,
      });
      setInviteCode(res.organization?.invite_code ?? null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  if (inviteCode) {
    return (
      <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 px-4">
        <h1 className="text-2xl font-semibold">You&apos;re set up</h1>
        <p className="text-sm text-neutral-600">
          Share this invite code with your sales reps so they can sign up:
        </p>
        <code className="rounded bg-neutral-100 px-3 py-2 text-lg font-mono">{inviteCode}</code>
        <button
          onClick={() => router.push("/admin")}
          className="rounded bg-neutral-900 px-3 py-2 text-white"
        >
          Go to dashboard
        </button>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-4">
      <h1 className="text-2xl font-semibold">Set up your organization</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <input
          placeholder="Organization name"
          value={orgName}
          onChange={(e) => setOrgName(e.target.value)}
          required
          className="rounded border border-neutral-300 px-3 py-2"
        />
        <input
          placeholder="Your name"
          value={adminName}
          onChange={(e) => setAdminName(e.target.value)}
          required
          className="rounded border border-neutral-300 px-3 py-2"
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="rounded border border-neutral-300 px-3 py-2"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          className="rounded border border-neutral-300 px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-neutral-900 px-3 py-2 text-white disabled:opacity-50"
        >
          {loading ? "Creating..." : "Create organization"}
        </button>
      </form>
    </main>
  );
}
