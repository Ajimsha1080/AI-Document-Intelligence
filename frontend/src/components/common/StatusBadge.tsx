import React from "react";
import { cn } from "@/lib/utils";
import { useApp } from "@/context/AppContext";

export type DocumentStatus = "processing" | "needs_review" | "approved" | "failed";

interface StatusBadgeProps {
  status: DocumentStatus;
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { t } = useApp();

  const config = {
    processing: {
      label: t("statusProcessing"),
      dotClass: "bg-blue-500 animate-pulse",
      containerClass: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20",
    },
    needs_review: {
      label: t("statusNeedsReview"),
      dotClass: "bg-amber-500",
      containerClass: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
    },
    approved: {
      label: t("statusApproved"),
      dotClass: "bg-emerald-500",
      containerClass: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
    },
    failed: {
      label: t("statusFailed"),
      dotClass: "bg-rose-500",
      containerClass: "bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/20",
    },
  }[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold border select-none transition-colors",
        config.containerClass,
        className
      )}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", config.dotClass)} />
      <span>{config.label}</span>
    </span>
  );
}
