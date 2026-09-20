import { api } from "./api";

export type UserRole = "team_lead" | "sales_rep";

export interface AuthUser {
  id: string;
  org_id: string;
  name: string;
  email: string;
  role: UserRole;
}

export interface Organization {
  id: string;
  name: string;
  invite_code: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
  organization?: Organization;
}

const TOKEN_KEY = "access_token";
const USER_KEY = "current_user";

function persistSession(res: TokenResponse) {
  localStorage.setItem(TOKEN_KEY, res.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(res.user));
}

export async function registerOrg(input: {
  org_name: string;
  admin_name: string;
  admin_email: string;
  admin_password: string;
}) {
  const res = await api.post<TokenResponse>("/auth/register-org", input);
  persistSession(res);
  return res;
}

export async function signup(input: {
  invite_code: string;
  name: string;
  email: string;
  password: string;
}) {
  const res = await api.post<TokenResponse>("/auth/signup", input);
  persistSession(res);
  return res;
}

export async function login(input: { email: string; password: string }) {
  const res = await api.post<TokenResponse>("/auth/login", input);
  persistSession(res);
  return res;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getCurrentUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as AuthUser) : null;
}

export function isAuthenticated(): boolean {
  return typeof window !== "undefined" && !!localStorage.getItem(TOKEN_KEY);
}
