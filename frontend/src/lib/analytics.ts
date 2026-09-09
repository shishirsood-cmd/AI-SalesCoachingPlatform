import { api } from "./api";

export interface ProgressEntry {
  session_id: string;
  scenario_title: string;
  completed_at: string;
  overall_score: number;
}

export interface MyProgress {
  entries: ProgressEntry[];
  average_score: number | null;
}

export interface RepStat {
  rep_id: string;
  rep_name: string;
  sessions_completed: number;
  average_score: number;
}

export interface ScenarioStat {
  scenario_id: string;
  title: string;
  attempts: number;
  average_score: number;
}

export interface CriterionStat {
  name: string;
  average_score: number;
  sample_count: number;
}

export interface TeamAnalytics {
  total_evaluated_sessions: number;
  average_score: number | null;
  by_rep: RepStat[];
  by_scenario: ScenarioStat[];
  by_criterion: CriterionStat[];
}

export const analyticsApi = {
  myProgress: () => api.get<MyProgress>("/analytics/my-progress"),
  team: () => api.get<TeamAnalytics>("/analytics/team"),
};
