"use client";

import { ReactNode } from "react";

export function DashboardCard({
  accent,
  title,
  action,
  children,
}: {
  accent: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm">
      <div className={`h-1 w-full ${accent}`} />
      <div className="flex flex-col gap-3 p-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-neutral-900">{title}</h2>
          {action}
        </div>
        {children}
      </div>
    </section>
  );
}
