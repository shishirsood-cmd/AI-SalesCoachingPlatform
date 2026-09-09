import { api } from "./api";

export interface CriterionScore {
  name: string;
  score: number;
  feedback: string;
}

export interface Evaluation {
  id: string;
  session_id: string;
  overall_score: number;
  criteria_scores: CriterionScore[];
  strengths: string[];
  areas_for_improvement: string[];
  summary: string;
  created_at: string;
}

export const evaluationsApi = {
  get: (sessionId: string) => api.get<Evaluation>(`/sessions/${sessionId}/evaluation`),
  create: (sessionId: string) => api.post<Evaluation>(`/sessions/${sessionId}/evaluation`, {}),
};
