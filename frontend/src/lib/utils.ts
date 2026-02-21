import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatKES(amount: number | null | undefined): string {
  if (amount == null) return "N/A";
  return `KES ${amount.toLocaleString("en-KE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function savingsPercent(cheap: number, expensive: number): number {
  if (!expensive || expensive === 0) return 0;
  return Math.round(((expensive - cheap) / expensive) * 100);
}

export function timeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export const STORE_COLORS: Record<string, string> = {
  naivas: "#e30613",
  carrefour: "#004f9f",
  quickmart: "#e8232a",
};
