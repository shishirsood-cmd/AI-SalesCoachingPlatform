import { api } from "./api";

export type DocStatus = "processing" | "ready" | "failed";

export interface KnowledgeDoc {
  id: string;
  filename: string;
  status: DocStatus;
  error_message: string | null;
  created_at: string;
  chunk_count: number;
}

export const knowledgeApi = {
  list: () => api.get<KnowledgeDoc[]>("/knowledge"),
  upload: (file: File) => api.upload<KnowledgeDoc>("/knowledge/upload", file, file.name),
  remove: (id: string) => api.del<void>(`/knowledge/${id}`),
};
