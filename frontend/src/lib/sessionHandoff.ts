import { SimulationSession } from "./sessions";

// One-shot handoff for passing a freshly-created session (including its
// opening-line audio, which the backend only returns inline on creation) from
// the scenario picker to the call page, without re-fetching or re-synthesizing.
const key = (id: string) => `session-handoff:${id}`;

export function stashSession(session: SimulationSession) {
  try {
    sessionStorage.setItem(key(session.id), JSON.stringify(session));
  } catch {
    // sessionStorage unavailable (private mode, etc.) — the call page will
    // just fetch fresh and skip the opening-line audio playback.
  }
}

export function takeStashedSession(id: string): SimulationSession | null {
  try {
    const raw = sessionStorage.getItem(key(id));
    if (!raw) return null;
    sessionStorage.removeItem(key(id));
    return JSON.parse(raw) as SimulationSession;
  } catch {
    return null;
  }
}
