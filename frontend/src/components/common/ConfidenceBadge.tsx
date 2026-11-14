import React from "react";
import { cn, toArabicIndicDigits } from "@/lib/utils";
import { useApp } from "@/context/AppContext";
import { ShieldCheck, ShieldAlert, AlertCircle } from "lucide-react";

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
      icon: ShieldCheck,
      classes: "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60",
    },
    medium: {
      label: t("confidenceMedium"),
      icon: ShieldAlert,
      classes: "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60",
    },
    low: {
      label: t("confidenceLow"),
      icon: AlertCircle,
      classes: "bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60 font-semibold",
    },
  }[variant];

  const Icon = config.icon;
  const displayScore = useArabicDigits
    ? `${toArabicIndicDigits(normalized)}%`
    : `${normalized}%`;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border",
        config.classes,
        className
      )}
      title={`${config.label} (${displayScore})`}
    >
      <Icon className="w-3.5 h-3.5" />
      <span className="font-mono font-semibold">{displayScore}</span>
      {showLabel && <span className="opacity-80 hidden sm:inline">• {config.label}</span>}
    </span>
  );
}
