export function scoreColor(score: number): string {
  if (score >= 80) return "text-green-700";
  if (score >= 60) return "text-amber-700";
  return "text-red-700";
}

export function barColor(score: number): string {
  if (score >= 80) return "bg-green-600";
  if (score >= 60) return "bg-amber-500";
  return "bg-red-500";
}
