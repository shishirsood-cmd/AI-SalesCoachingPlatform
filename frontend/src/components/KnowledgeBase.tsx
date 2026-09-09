"use client";

import { useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 3000;

import { ApiError } from "@/lib/api";
import { KnowledgeDoc, knowledgeApi } from "@/lib/knowledge";

const STATUS_STYLES: Record<KnowledgeDoc["status"], string> = {
  processing: "bg-amber-100 text-amber-800",
  ready: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export function KnowledgeBase() {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const docsRef = useRef<KnowledgeDoc[]>([]);

  useEffect(() => {
    docsRef.current = docs;
  }, [docs]);

  async function refresh() {
    try {
      setDocs(await knowledgeApi.list());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load knowledge base");
    }
  }

  useEffect(() => {
    // Initial fetch on mount, then poll only while a doc is still processing.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
    const interval = setInterval(() => {
      if (docsRef.current.some((d) => d.status === "processing")) refresh();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      await knowledgeApi.upload(file);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDelete(id: string) {
    try {
      await knowledgeApi.remove(id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Knowledge base</h2>
        <label className="cursor-pointer text-sm underline">
          {uploading ? "Uploading..." : "+ Upload manual (.pdf, .txt)"}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt"
            onChange={handleFileChange}
            disabled={uploading}
            className="hidden"
          />
        </label>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {docs.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No manuals uploaded yet. Upload product docs to ground AI conversations in real facts.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {docs.map((doc) => (
            <li
              key={doc.id}
              className="flex items-center justify-between rounded border border-neutral-200 px-3 py-2"
            >
              <div>
                <p className="text-sm font-medium">{doc.filename}</p>
                {doc.status === "failed" && doc.error_message && (
                  <p className="text-xs text-red-600">{doc.error_message}</p>
                )}
                {doc.status === "ready" && (
                  <p className="text-xs text-neutral-500">{doc.chunk_count} chunks indexed</p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className={`rounded px-2 py-0.5 text-xs ${STATUS_STYLES[doc.status]}`}>
                  {doc.status}
                </span>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="text-sm text-neutral-500 hover:text-red-600"
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
