"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { RoleGuard } from "@/components/RoleGuard";
import { Scorecard } from "@/components/Scorecard";
import { ApiError } from "@/lib/api";
import { Evaluation, evaluationsApi } from "@/lib/evaluations";
import { takeStashedSession } from "@/lib/sessionHandoff";
import { SimulationSession, sessionsApi } from "@/lib/sessions";
import { useMicRecorder } from "@/lib/useMicRecorder";

export default function PracticeSessionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [session, setSession] = useState<SimulationSession | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [ending, setEnding] = useState(false);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const evalTriggeredRef = useRef<string | null>(null);

  const { status: micStatus, error: micError, start: startRecording, stop: stopRecording } =
    useMicRecorder(async (blob) => {
      if (!session) return;
      setError(null);
      try {
        const updated = await sessionsApi.sendVoiceMessage(session.id, blob);
        setSession(updated);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to send recording");
      }
    });

  useEffect(() => {
    const stashed = takeStashedSession(params.id);
    if (stashed) {
      // Freshly created session handed off from the scenario picker — already
      // includes the opening line's audio, so skip an extra fetch.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSession(stashed);
      return;
    }
    sessionsApi
      .get(params.id)
      .then(setSession)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load call"));
  }, [params.id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.turns.length]);

  useEffect(() => {
    if (session?.status !== "completed" || evalTriggeredRef.current === session.id) return;
    evalTriggeredRef.current = session.id;
    setEvalLoading(true);
    evaluationsApi
      .create(session.id)
      .then(setEvaluation)
      .catch((err) => setEvalError(err instanceof ApiError ? err.message : "Failed to generate evaluation"))
      .finally(() => setEvalLoading(false));
  }, [session?.status, session?.id]);

  useEffect(() => {
    if (session?.audio_base64 && audioRef.current) {
      audioRef.current.src = `data:audio/mpeg;base64,${session.audio_base64}`;
      audioRef.current.play().catch(() => {
        // Autoplay can be blocked before the first user interaction — the rep
        // can still read the reply, and the next reply will play normally.
      });
    }
  }, [session?.audio_base64]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim() || !session) return;
    setError(null);
    setSending(true);
    const content = draft;
    setDraft("");
    try {
      const updated = await sessionsApi.sendMessage(session.id, content);
      setSession(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send message");
      setDraft(content);
    } finally {
      setSending(false);
    }
  }

  async function handleEnd() {
    if (!session) return;
    setEnding(true);
    try {
      const updated = await sessionsApi.end(session.id);
      setSession(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to end call");
    } finally {
      setEnding(false);
    }
  }

  return (
    <RoleGuard allow={["sales_rep"]}>
      {() => (
        <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-4 px-4 py-8">
          <audio ref={audioRef} className="hidden" />
          <div className="flex items-center justify-between">
            <Link href="/practice" className="text-sm underline">
              &larr; Back to scenarios
            </Link>
            {session?.status === "active" && (
              <button
                onClick={handleEnd}
                disabled={ending}
                className="text-sm text-red-600 underline disabled:opacity-50"
              >
                {ending ? "Ending..." : "End call"}
              </button>
            )}
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {micError && <p className="text-sm text-red-600">{micError}</p>}

          {!session ? (
            !error && <p className="text-sm text-neutral-500">Loading...</p>
          ) : (
            <>
              {session.status === "completed" && !evaluation && (
                <p className="rounded bg-neutral-100 px-3 py-2 text-sm text-neutral-600">
                  This call has ended.
                </p>
              )}

              <div className="flex max-h-96 flex-col gap-3 overflow-y-auto rounded border border-neutral-200 p-4">
                {session.turns.map((turn) => (
                  <div
                    key={turn.id}
                    className={`max-w-[80%] rounded px-3 py-2 text-sm ${
                      turn.speaker === "rep"
                        ? "self-end bg-neutral-900 text-white"
                        : "self-start bg-neutral-100 text-neutral-900"
                    }`}
                  >
                    {turn.content}
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>

              {session.status === "active" && (
                <div className="flex flex-col gap-2">
                  <button
                    onClick={micStatus === "recording" ? stopRecording : startRecording}
                    disabled={micStatus === "processing"}
                    className={`rounded px-4 py-3 text-sm font-medium text-white disabled:opacity-50 ${
                      micStatus === "recording" ? "bg-red-600" : "bg-neutral-900"
                    }`}
                  >
                    {micStatus === "recording"
                      ? "⏹ Stop & send"
                      : micStatus === "processing"
                        ? "Transcribing..."
                        : "🎤 Start speaking"}
                  </button>

                  <form onSubmit={handleSend} className="flex gap-2">
                    <input
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      placeholder="...or type your response"
                      disabled={sending}
                      className="flex-1 rounded border border-neutral-300 px-3 py-2 text-sm"
                    />
                    <button
                      type="submit"
                      disabled={sending || !draft.trim()}
                      className="rounded bg-neutral-100 px-4 py-2 text-sm disabled:opacity-50"
                    >
                      {sending ? "..." : "Send"}
                    </button>
                  </form>
                </div>
              )}

              {session.status === "completed" && (
                <>
                  {evalLoading && (
                    <p className="text-sm text-neutral-500">Generating your scorecard...</p>
                  )}
                  {evalError && <p className="text-sm text-red-600">{evalError}</p>}
                  {evaluation && <Scorecard evaluation={evaluation} />}

                  <button
                    onClick={() => router.push("/practice")}
                    className="self-start rounded bg-neutral-900 px-4 py-2 text-sm text-white"
                  >
                    Practice another scenario
                  </button>
                </>
              )}
            </>
          )}
        </main>
      )}
    </RoleGuard>
  );
}
