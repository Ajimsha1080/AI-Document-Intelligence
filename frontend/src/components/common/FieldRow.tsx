import React, { useState, useEffect } from "react";
import { ExtractedField } from "@/types";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { useApp } from "@/context/AppContext";
import { cn } from "@/lib/utils";
import { Crosshair, Check, RotateCcw, AlertTriangle, Lock } from "lucide-react";

interface FieldRowProps {
  field: ExtractedField;
  docId: string;
}

export function FieldRow({ field, docId }: FieldRowProps) {
  const {
    activeFieldKey,
    setActiveFieldKey,
    updateDocumentField,
    piiMasked,
    language,
    t,
  } = useApp();

  const [isEditing, setIsEditing] = useState(false);
  const [val, setVal] = useState(field.value);

  useEffect(() => {
    setVal(field.value);
  }, [field.value]);

  const isActive = activeFieldKey === field.key;

  const handleSave = () => {
    updateDocumentField(docId, field.key, val);
    setIsEditing(false);
  };

  const handleRestore = () => {
    setVal(field.originalValue);
    updateDocumentField(docId, field.key, field.originalValue);
    setIsEditing(false);
  };

  const isSensitive = field.key.includes("id_number") || field.key.includes("trn");
  const displayVal = piiMasked && isSensitive && !isEditing
    ? field.value.replace(/\d(?=\d{4})/g, "*")
    : val;

  return (
    <div
      onClick={() => setActiveFieldKey(field.key)}
      className={cn(
        "p-3 rounded-lg border transition-all text-xs space-y-2 cursor-pointer",
        isActive
          ? "bg-emerald-50/50 dark:bg-emerald-950/30 border-emerald-500 ring-1 ring-emerald-500 shadow-sm"
          : "bg-card border-border hover:border-slate-300 dark:hover:border-slate-700"
      )}
    >
      {/* Header: Name & Badges */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="font-bold text-foreground truncate">
            {language === "ar" ? field.nameAr : field.nameEn}
          </span>
          {field.required && (
            <span className="text-rose-500 text-xs font-bold" title="Required Field">
              *
            </span>
          )}
          {isSensitive && piiMasked && (
            <span title="PII Masked">
              <Lock className="w-3 h-3 text-muted-foreground" />
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <ConfidenceBadge score={field.confidence} showLabel={false} />

          <button
            onClick={(e) => {
              e.stopPropagation();
              setActiveFieldKey(field.key);
            }}
            className="p-1 rounded text-muted-foreground hover:text-primary hover:bg-secondary transition-all"
            title={t("actionJumpToSource")}
          >
            <Crosshair className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Value Input / Display */}
      <div className="flex items-center gap-2">
        {isEditing ? (
          <div className="flex items-center gap-1.5 w-full">
            <input
              type="text"
              value={val}
              onChange={(e) => setVal(e.target.value)}
              className="flex-1 px-2.5 py-1 text-xs rounded border border-primary bg-background text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSave();
                if (e.key === "Escape") setIsEditing(false);
              }}
            />
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSave();
              }}
              className="px-2 py-1 rounded bg-primary text-primary-foreground font-semibold flex items-center gap-1 text-[11px]"
            >
              <Check className="w-3 h-3" />
              <span>{language === "ar" ? "حفظ" : "Save"}</span>
            </button>
          </div>
        ) : (
          <div
            onClick={(e) => {
              e.stopPropagation();
              setIsEditing(true);
            }}
            className="flex-1 px-2.5 py-1.5 rounded bg-secondary/50 hover:bg-secondary font-mono text-foreground font-medium truncate border border-transparent hover:border-border transition-all flex items-center justify-between"
            title="Click to edit value"
          >
            <span className="truncate">{displayVal}</span>
            <span className="text-[10px] text-muted-foreground opacity-60 ms-2">Edit</span>
          </div>
        )}
      </div>

      {/* Validation Warnings & Audit Diff */}
      <div className="flex items-center justify-between text-[11px] pt-1">
        {field.validationError ? (
          <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400 font-semibold">
            <AlertTriangle className="w-3 h-3" />
            <span>{field.validationError}</span>
          </span>
        ) : (
          <span className="text-muted-foreground text-[10px]">
            {field.section.toUpperCase()}
          </span>
        )}

        {field.isCorrected && (
          <div className="flex items-center gap-1.5 text-[10px] text-amber-700 dark:text-amber-400 font-medium">
            <span className="line-through opacity-70">Orig: {field.originalValue}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleRestore();
              }}
              className="text-muted-foreground hover:text-foreground underline flex items-center gap-0.5"
              title="Restore original extracted value"
            >
              <RotateCcw className="w-2.5 h-2.5" />
              <span>Restore</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
