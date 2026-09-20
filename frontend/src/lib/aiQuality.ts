import { api } from "./api";

export type AIQualityEvalType = "transcript_analysis";

export interface AIQualityEval {
  id: string;
  session_id: string;
  eval_type: AIQualityEvalType;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  scores: Record<string, any>;
  summary: string;
  created_at: string;
}

export interface AIQualityEvals {
  transcript_analysis: AIQualityEval | null;
}

export const aiQualityApi = {
  get: (sessionId: string) => api.get<AIQualityEvals>(`/sessions/${sessionId}/ai-quality-evals`),
  run: (sessionId: string) => api.post<AIQualityEvals>(`/sessions/${sessionId}/ai-quality-evals`, {}),
};
