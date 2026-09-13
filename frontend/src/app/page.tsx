"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getCurrentUser, isAuthenticated } from "@/lib/auth";

const STEPS = [
  {
    title: "Build the scenario",
    body: "Team leads write the customer persona and objections, set the evaluation rubric, and upload product manuals to ground the AI in real facts.",
  },
  {
    title: "Practice the call",
    body: "Reps have a real voice conversation with an AI customer that raises objections naturally and references the uploaded product docs when it's relevant.",
  },
  {
    title: "Get scored, improve",
    body: "Every call ends with a scorecard: an overall score, per-criterion feedback tied to what was actually said, and clear next steps.",
  },
];

export default function Home() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) {
      const user = getCurrentUser();
      router.replace(user?.role === "team_lead" ? "/admin" : "/practice");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setChecked(true);
  }, [router]);

  if (!checked) return null;

  return (
    <main className="flex flex-1 flex-col">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 px-4 py-4 sm:px-6 sm:py-6">
        <span className="whitespace-nowrap text-base font-semibold tracking-tight sm:text-lg">
          Sales Coaching Platform
        </span>
        <nav className="flex shrink-0 items-center gap-3 text-sm sm:gap-6">
          <Link href="/login" className="whitespace-nowrap text-neutral-600 hover:text-neutral-900">
            Log in
          </Link>
          <Link
            href="/register-org"
            className="whitespace-nowrap rounded bg-neutral-900 px-3 py-2 font-medium text-white hover:bg-neutral-800 sm:px-4"
          >
            Get started
          </Link>
        </nav>
      </header>

      <section className="mx-auto flex w-full max-w-3xl flex-col items-center gap-6 px-6 py-20 text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-neutral-900 sm:text-5xl">
          Get new reps closing deals faster
        </h1>
        <p className="max-w-2xl text-lg text-neutral-600">
          Practice sales calls with an AI customer that objects, pushes back, and remembers the
          conversation — grounded in your own product docs. Every call ends with specific,
          evidence-based feedback against the rubric your team defines.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/register-org"
            className="rounded bg-neutral-900 px-5 py-3 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Set up your organization
          </Link>
          <Link
            href="/signup"
            className="rounded border border-neutral-300 px-5 py-3 text-sm font-medium text-neutral-700 hover:border-neutral-400"
          >
            Join with an invite code
          </Link>
        </div>
      </section>

      <section className="border-t border-neutral-100 bg-neutral-50">
        <div className="mx-auto grid w-full max-w-5xl grid-cols-1 gap-10 px-6 py-16 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <div key={step.title} className="flex flex-col gap-2">
              <span className="text-sm font-medium text-neutral-400">{`0${i + 1}`}</span>
              <h2 className="text-lg font-semibold text-neutral-900">{step.title}</h2>
              <p className="text-sm text-neutral-600">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-5xl grid-cols-1 gap-8 px-6 py-16 sm:grid-cols-2">
        <div className="flex flex-col gap-3 rounded border border-neutral-200 p-6">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">
            For team leads
          </h3>
          <p className="text-neutral-700">
            Build a library of scenarios your reps actually face, set the rubric they&apos;re
            scored against, and see where the whole team is strongest and weakest — by rep, by
            scenario, and by skill.
          </p>
        </div>
        <div className="flex flex-col gap-3 rounded border border-neutral-200 p-6">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">
            For sales reps
          </h3>
          <p className="text-neutral-700">
            Get ready for real calls before you&apos;re on one. Practice as many times as you
            need, hear how you sound, and track your score improving over time.
          </p>
        </div>
      </section>

      <footer className="border-t border-neutral-100 px-6 py-8 text-center text-sm text-neutral-400">
        <Link href="/login" className="hover:text-neutral-600">
          Already have an account? Log in
        </Link>
      </footer>
    </main>
  );
}
