"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthUser, UserRole, getCurrentUser, isAuthenticated } from "@/lib/auth";

export function RoleGuard({
  allow,
  children,
}: {
  allow: UserRole[];
  children: (user: AuthUser) => React.ReactNode;
}) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null | "checking">("checking");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    const current = getCurrentUser();
    if (!current || !allow.includes(current.role)) {
      router.replace("/");
      return;
    }
    // localStorage is only readable client-side, so this state can't be computed
    // during the initial (server) render — it must be set after mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUser(current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (user === "checking" || user === null) {
    return <div className="p-8 text-sm text-neutral-500">Loading...</div>;
  }

  return <>{children(user)}</>;
}
