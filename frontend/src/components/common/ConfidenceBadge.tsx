import React from "react";
import { cn, toArabicIndicDigits } from "@/lib/utils";
import { useApp } from "@/context/AppContext";

interface ConfidenceBadgeProps {
  score: number; // 0 to 1 or 0 to 100
  showLabel?: boolean;
  className?: string;
}

export function ConfidenceBadge({ score, showLabel = true, className }: ConfidenceBadgeProps) {
  const { useArabicDigits, t } = useApp();

  const normalized = score <= 1 ? Math.round(score * 100) : Math.round(score);

  let variant: "high" | "medium" | "low" = "high";
  if (normalized < 75) {
    variant = "low";
  } else if (normalized < 90) {
    variant = "medium";
  }

  const config = {
    high: {
      label: t("confidenceHigh"),
      dotClass: "bg-emerald-500",
      classes: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
    },
    medium: {
      label: t("confidenceMedium"),
      dotClass: "bg-amber-500",
      classes: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
    },
    low: {
      label: t("confidenceLow"),
      dotClass: "bg-rose-500",
      classes: "bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/20",
    },
  }[variant];

  const displayScore = useArabicDigits
    ? `${toArabicIndicDigits(normalized)}%`
    : `${normalized}%`;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-mono font-medium border select-none",
        config.classes,
        className
      )}
      title={`${config.label} (${displayScore})`}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", config.dotClass)} />
      <span className="font-semibold">{displayScore}</span>
      {showLabel && <span className="opacity-75 hidden sm:inline font-sans font-normal text-[10px]">· {config.label}</span>}
    </span>
  );
}
