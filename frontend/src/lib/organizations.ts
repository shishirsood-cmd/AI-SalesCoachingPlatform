import { api } from "./api";
import { Organization } from "./auth";

export const organizationsApi = {
  getMine: () => api.get<Organization>("/organizations/me"),
  rotateInviteCode: () => api.post<Organization>("/organizations/me/rotate-invite-code", {}),
};
