"use client";

import { barColor, scoreColor } from "@/lib/scoreColor";

export function ScoreRow({
  label,
  sublabel,
  score,
}: {
  label: string;
  sublabel?: string;
  score: number;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">
          {label}
          {sublabel && <span className="ml-2 text-xs font-normal text-neutral-500">{sublabel}</span>}
        </span>
        <span className={scoreColor(score)}>{Math.round(score)}/100</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
        <div
          className={`h-full rounded-full ${barColor(score)}`}
          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
        />
      </div>
    </div>
  );
}
