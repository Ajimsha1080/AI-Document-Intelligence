import React from "react";
import { cn } from "@/lib/utils";
import { useApp } from "@/context/AppContext";
import { CheckCircle2, Clock, AlertTriangle, XCircle } from "lucide-react";

export type DocumentStatus = "processing" | "needs_review" | "approved" | "failed";

interface StatusBadgeProps {
  status: DocumentStatus;
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({ status, className, showIcon = true }: StatusBadgeProps) {
  const { t } = useApp();

  const config = {
    processing: {
      label: t("statusProcessing"),
      icon: Clock,
      classes: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-900/60",
      dotClass: "bg-blue-500 animate-pulse",
    },
    needs_review: {
      label: t("statusNeedsReview"),
      icon: AlertTriangle,
      classes: "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/60",
      dotClass: "bg-amber-500",
    },
    approved: {
      label: t("statusApproved"),
      icon: CheckCircle2,
      classes: "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60",
      dotClass: "bg-emerald-500",
    },
    failed: {
      label: t("statusFailed"),
      icon: XCircle,
      classes: "bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800/60",
      dotClass: "bg-rose-500",
    },
  }[status];

  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border",
        config.classes,
        className
      )}
    >
      {showIcon && <Icon className="w-3.5 h-3.5" />}
      <span>{config.label}</span>
    </span>
  );
}
