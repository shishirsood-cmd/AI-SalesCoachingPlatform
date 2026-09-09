import { api } from "./api";

export type SessionStatus = "active" | "completed";
export type Speaker = "rep" | "ai_customer";

export interface Turn {
  id: string;
  turn_index: number;
  speaker: Speaker;
  content: string;
  created_at: string;
}

export interface SimulationSession {
  id: string;
  scenario_id: string;
  rep_id: string;
  status: SessionStatus;
  started_at: string;
  ended_at: string | null;
  turns: Turn[];
  audio_base64: string | null;
}

export const sessionsApi = {
  list: () => api.get<SimulationSession[]>("/sessions"),
  get: (id: string) => api.get<SimulationSession>(`/sessions/${id}`),
  start: (scenarioId: string, opts?: { voice?: boolean }) =>
    api.post<SimulationSession>(`/sessions${opts?.voice ? "?voice=true" : ""}`, {
      scenario_id: scenarioId,
    }),
  sendMessage: (id: string, content: string) =>
    api.post<SimulationSession>(`/sessions/${id}/messages`, { content }),
  sendVoiceMessage: (id: string, audio: Blob) =>
    api.upload<SimulationSession>(`/sessions/${id}/voice-messages`, audio, "recording.webm"),
  end: (id: string) => api.post<SimulationSession>(`/sessions/${id}/end`, {}),
};
