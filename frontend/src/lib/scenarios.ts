import { api } from "./api";

export type Difficulty = "easy" | "medium" | "hard";
export type CallType = "cold_call" | "support";

export interface RubricCriterion {
  name: string;
  description: string;
  weight: number;
}

export interface Scenario {
  id: string;
  org_id: string;
  created_by: string;
  title: string;
  persona_description: string;
  objections: string[];
  difficulty: Difficulty;
  call_type: CallType;
  rubric_criteria: RubricCriterion[];
  created_at: string;
  updated_at: string;
}

export type ScenarioInput = Omit<Scenario, "id" | "org_id" | "created_by" | "created_at" | "updated_at">;

export const scenariosApi = {
  list: () => api.get<Scenario[]>("/scenarios"),
  get: (id: string) => api.get<Scenario>(`/scenarios/${id}`),
  create: (input: ScenarioInput) => api.post<Scenario>("/scenarios", input),
  update: (id: string, input: ScenarioInput) => api.put<Scenario>(`/scenarios/${id}`, input),
  remove: (id: string) => api.del<void>(`/scenarios/${id}`),
};
