"use client";

import { useState } from "react";

import { ApiError } from "@/lib/api";
import { CallType, Difficulty, RubricCriterion, ScenarioInput } from "@/lib/scenarios";

const emptyCriterion: RubricCriterion = { name: "", description: "", weight: 0 };

export function ScenarioForm({
  initial,
  onSubmit,
  submitLabel,
}: {
  initial?: ScenarioInput;
  onSubmit: (input: ScenarioInput) => Promise<void>;
  submitLabel: string;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [personaDescription, setPersonaDescription] = useState(initial?.persona_description ?? "");
  const [objections, setObjections] = useState<string[]>(initial?.objections ?? [""]);
  const [difficulty, setDifficulty] = useState<Difficulty>(initial?.difficulty ?? "medium");
  const [callType, setCallType] = useState<CallType>(initial?.call_type ?? "cold_call");
  const [criteria, setCriteria] = useState<RubricCriterion[]>(
    initial?.rubric_criteria ?? [{ ...emptyCriterion }]
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const weightTotal = criteria.reduce((sum, c) => sum + (Number(c.weight) || 0), 0);

  function updateObjection(index: number, value: string) {
    setObjections((prev) => prev.map((o, i) => (i === index ? value : o)));
  }

  function updateCriterion(index: number, field: keyof RubricCriterion, value: string) {
    setCriteria((prev) =>
      prev.map((c, i) =>
        i === index ? { ...c, [field]: field === "weight" ? Number(value) : value } : c
      )
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (Math.abs(weightTotal - 100) > 0.01) {
      setError(`Rubric weights must sum to 100 (currently ${weightTotal}).`);
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        title,
        persona_description: personaDescription,
        objections: objections.map((o) => o.trim()).filter(Boolean),
        difficulty,
        call_type: callType,
        rubric_criteria: criteria.filter((c) => c.name.trim()),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">Title</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="rounded border border-neutral-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">Customer persona</label>
        <textarea
          value={personaDescription}
          onChange={(e) => setPersonaDescription(e.target.value)}
          required
          rows={3}
          placeholder="Who is the AI playing? Personality, role, industry, prior context..."
          className="rounded border border-neutral-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      <div className="flex gap-4">
        <div className="flex flex-1 flex-col gap-1">
          <label className="text-sm font-medium">Difficulty</label>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as Difficulty)}
            className="rounded border border-neutral-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        <div className="flex flex-1 flex-col gap-1">
          <label className="text-sm font-medium">Call type</label>
          <select
            value={callType}
            onChange={(e) => setCallType(e.target.value as CallType)}
            className="rounded border border-neutral-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="cold_call">Cold call</option>
            <option value="support">Support</option>
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium">Objections the AI should raise</label>
        {objections.map((o, i) => (
          <div key={i} className="flex gap-2">
            <input
              value={o}
              onChange={(e) => updateObjection(i, e.target.value)}
              placeholder="e.g. We don't have budget this quarter"
              className="flex-1 rounded border border-neutral-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={() => setObjections((prev) => prev.filter((_, idx) => idx !== i))}
              className="px-2 text-neutral-500 hover:text-red-600"
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => setObjections((prev) => [...prev, ""])}
          className="self-start text-sm text-indigo-600 hover:text-indigo-700"
        >
          + Add objection
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between">
          <label className="text-sm font-medium">Evaluation rubric</label>
          <span className={weightTotal === 100 ? "text-sm text-neutral-500" : "text-sm text-red-600"}>
            Weights total: {weightTotal}/100
          </span>
        </div>
        {criteria.map((c, i) => (
          <div key={i} className="flex flex-col gap-2 rounded border border-neutral-200 p-3">
            <div className="flex gap-2">
              <input
                value={c.name}
                onChange={(e) => updateCriterion(i, "name", e.target.value)}
                placeholder="Criterion name (e.g. Empathy)"
                className="flex-1 rounded border border-neutral-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <input
                type="number"
                value={c.weight}
                onChange={(e) => updateCriterion(i, "weight", e.target.value)}
                placeholder="Weight %"
                className="w-24 rounded border border-neutral-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={() => setCriteria((prev) => prev.filter((_, idx) => idx !== i))}
                className="px-2 text-neutral-500 hover:text-red-600"
              >
                Remove
              </button>
            </div>
            <input
              value={c.description}
              onChange={(e) => updateCriterion(i, "description", e.target.value)}
              placeholder="What does scoring well on this look like?"
              className="rounded border border-neutral-300 px-3 py-2 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        ))}
        <button
          type="button"
          onClick={() => setCriteria((prev) => [...prev, { ...emptyCriterion }])}
          className="self-start text-sm text-indigo-600 hover:text-indigo-700"
        >
          + Add criterion
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="self-start rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {submitting ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}
