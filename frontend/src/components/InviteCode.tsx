"use client";

import { useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import { Organization } from "@/lib/auth";
import { organizationsApi } from "@/lib/organizations";

import { DashboardCard } from "./DashboardCard";

export function InviteCode() {
  const [org, setOrg] = useState<Organization | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rotating, setRotating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [guidelines, setGuidelines] = useState("");
  const [savingGuidelines, setSavingGuidelines] = useState(false);
  const [guidelinesSaved, setGuidelinesSaved] = useState(false);

  useEffect(() => {
    organizationsApi
      .getMine()
      .then((data) => {
        setOrg(data);
        setGuidelines(data.compliance_guidelines ?? "");
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load organization"));
  }, []);

  async function handleRotate() {
    if (!confirm("Generate a new invite code? The old code will stop working immediately.")) return;
    setRotating(true);
    setError(null);
    try {
      setOrg(await organizationsApi.rotateInviteCode());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate a new code");
    } finally {
      setRotating(false);
    }
  }

  async function handleCopy() {
    if (!org) return;
    try {
      await navigator.clipboard.writeText(org.invite_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable — the code is still visible to copy manually.
    }
  }

  async function handleSaveGuidelines() {
    setSavingGuidelines(true);
    setError(null);
    try {
      setOrg(await organizationsApi.updateComplianceGuidelines(guidelines.trim() || null));
      setGuidelinesSaved(true);
      setTimeout(() => setGuidelinesSaved(false), 1500);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save compliance guidelines");
    } finally {
      setSavingGuidelines(false);
    }
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!org) return null;

  return (
    <DashboardCard accent="bg-indigo-600" title="Organization">
      <div className="flex flex-col gap-2">
        <p className="text-sm text-neutral-600">
          Share this code with sales reps so they can sign up under {org.name}.
        </p>
        <div className="flex items-center gap-2">
          <code className="rounded bg-neutral-100 px-3 py-2 font-mono text-lg">{org.invite_code}</code>
          <button onClick={handleCopy} className="text-sm text-indigo-600 hover:text-indigo-700">
            {copied ? "Copied!" : "Copy"}
          </button>
          <button
            onClick={handleRotate}
            disabled={rotating}
            className="text-sm text-indigo-600 hover:text-indigo-700 disabled:opacity-50"
          >
            {rotating ? "Generating..." : "Generate new code"}
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-2 border-t border-neutral-100 pt-4">
        <label className="text-sm font-medium">Compliance guidelines (optional)</label>
        <p className="text-xs text-neutral-500">
          Free-text enterprise constraints — e.g. no unapproved discounts, no discriminatory
          language. Checked by the Coaching Safety AI Quality Eval; leave blank to skip.
        </p>
        <textarea
          value={guidelines}
          onChange={(e) => setGuidelines(e.target.value)}
          rows={2}
          className="rounded border border-neutral-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <button
          onClick={handleSaveGuidelines}
          disabled={savingGuidelines}
          className="self-start rounded bg-indigo-50 px-3 py-1.5 text-sm text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
        >
          {savingGuidelines ? "Saving..." : guidelinesSaved ? "Saved!" : "Save guidelines"}
        </button>
      </div>
    </DashboardCard>
  );
}
