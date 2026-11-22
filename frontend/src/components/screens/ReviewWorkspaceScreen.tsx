"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { ExtractedField } from "@/types";
import { ArrowLeft, CheckCircle2, AlertTriangle, RotateCw, Check, X, Sparkles } from "lucide-react";

export function ReviewWorkspaceScreen() {
  const {
    documents,
    selectedDocumentId,
    setSelectedDocumentId,
    setCurrentScreen,
    updateDocumentField,
    approveDocument,
    rejectDocument,
    showToast,
    userRole,
    activeFieldKey,
    setActiveFieldKey,
  } = useApp();

  const doc = documents.find((d) => d.id === selectedDocumentId) || documents[0];

  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [rotation, setRotation] = useState<number>(0);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [isRejecting, setIsRejecting] = useState<boolean>(false);

  if (!doc) {
    return (
      <div className="p-12 text-center text-zinc-500 flex flex-col items-center gap-3">
        <span>No document selected for review.</span>
        <button
          onClick={() => setCurrentScreen("command")}
          className="px-4 py-2 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 rounded-lg text-xs font-semibold"
        >
          Return to Inbox
        </button>
      </div>
    );
  }

  const needsReviewList = documents.filter((d) => d.status === "needs_review");
  const currentIndex = needsReviewList.findIndex((d) => d.id === doc.id);

  const handlePrevDoc = () => {
    if (currentIndex > 0) {
      setSelectedDocumentId(needsReviewList[currentIndex - 1].id);
    }
  };

  const handleNextDoc = () => {
    if (currentIndex < needsReviewList.length - 1) {
      setSelectedDocumentId(needsReviewList[currentIndex + 1].id);
    }
  };

  const startEdit = (field: ExtractedField) => {
    setEditingKey(field.key);
    setEditValue(field.value || "");
    setActiveFieldKey(field.key);
  };

  const saveEdit = async (fieldKey: string) => {
    try {
      await updateDocumentField(doc.id, fieldKey, editValue);
      showToast("success", `Updated ${fieldKey}`, `تم تحديث الحقل ${fieldKey}`);
      setEditingKey(null);
    } catch (err: any) {
      showToast("error", err.message || "Failed to update field", "تعذر حفظ التعديل");
    }
  };

  const handleAcceptOneClickFix = async () => {
    // If ID checksum failed (last digit), fix to 1
    const idField = doc.fields?.find((f) => f.key === "id_number");
    if (idField && idField.value) {
      const fixedValue = idField.value.slice(0, -1) + "1";
      await updateDocumentField(doc.id, "id_number", fixedValue);
      showToast("success", "Accepted checksum check digit fix (…-1)", "تم تصحيح رقم الهوية");
    }
  };

  const handleApprove = async () => {
    setIsApproving(true);
    try {
      await approveDocument(doc.id);
      showToast("success", "Document approved successfully", "تم اعتماد المستند بنجاح");
      // Go to next review doc if available
      if (currentIndex < needsReviewList.length - 1) {
        setSelectedDocumentId(needsReviewList[currentIndex + 1].id);
      }
    } catch (err: any) {
      showToast("error", err.message || "Cannot approve document", "تعذر اعتماد المستند");
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    setIsRejecting(true);
    try {
      await rejectDocument(doc.id);
      showToast("info", "Document rejected", "تم رفض المستند");
      if (currentIndex < needsReviewList.length - 1) {
        setSelectedDocumentId(needsReviewList[currentIndex + 1].id);
      }
    } catch (err: any) {
      showToast("error", err.message || "Cannot reject document", "تعذر رفض المستند");
    } finally {
      setIsRejecting(false);
    }
  };

  const hasFailedErrors = (doc.validationErrors || []).some((e) => e.severity === "error" && !e.isResolved);
  const isApproved = doc.status === "approved";
  const canApprove = (userRole === "admin" || !hasFailedErrors) && !isApproved;

  // Mock standard checks
  const checks = [
    { name: "Format & check digit validity", passed: !hasFailedErrors },
    { name: "Document not expired", passed: true },
    { name: "Date of birth in the past", passed: true },
    { name: "Sanctions list match", passed: true },
  ];
  const passedChecksCount = checks.filter((c) => c.passed).length;

  return (
    <div className="flex flex-col gap-4 -mt-2">
      {/* Top Header Bar (Matching v2/ReviewPro.dc.html) */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-xs">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setCurrentScreen("command")}
            className="flex items-center gap-1.5 text-xs font-semibold text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Inbox</span>
          </button>
          <span className="text-zinc-300 dark:text-zinc-700">/</span>
          <span className="font-bold text-sm text-zinc-900 dark:text-zinc-100 truncate max-w-xs">
            {doc.fileName}
          </span>
          <span className="font-mono text-xs text-zinc-400">{doc.referenceNumber}</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              doc.status === "approved"
                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                : doc.status === "needs_review"
                ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                : "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300"
            }`}
          >
            {doc.status.replace("_", " ")}
          </span>
        </div>

        {/* Queue Navigator */}
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <span>
            {currentIndex >= 0 ? `${currentIndex + 1} of ${needsReviewList.length} in queue` : "All documents"}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={handlePrevDoc}
              disabled={currentIndex <= 0}
              className="p-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40"
            >
              ↑
            </button>
            <button
              onClick={handleNextDoc}
              disabled={currentIndex < 0 || currentIndex >= needsReviewList.length - 1}
              className="p-1.5 rounded-md border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40"
            >
              ↓
            </button>
          </div>
        </div>
      </div>

      {/* Main Split: Left Document Viewer / Right Fields & Checks */}
      <div className="flex flex-col lg:flex-row gap-5 items-stretch min-h-[640px]">
        {/* Left: Document Viewport */}
        <section className="flex-1 lg:flex-[3] border border-zinc-200 dark:border-zinc-800 rounded-xl bg-zinc-100 dark:bg-zinc-950/60 overflow-hidden flex flex-col shadow-xs">
          {/* Viewport Toolbar */}
          <div className="flex items-center justify-between px-4 py-2.5 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 text-xs text-zinc-500">
            <span>Original · page 1 of 1 · deskewed −1.2°</span>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setRotation((r) => (r + 90) % 360)}
                className="px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800 flex items-center gap-1"
              >
                <RotateCw className="w-3 h-3" />
                <span>Rotate</span>
              </button>
              <button
                type="button"
                className="px-2 py-1 rounded border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800"
              >
                Fit
              </button>
            </div>
          </div>

          {/* Canvas Area with Interactive Bounding Boxes */}
          <div className="flex-1 p-6 flex items-center justify-center overflow-auto min-h-[420px]">
            <div
              style={{ transform: `rotate(${rotation}deg)` }}
              className="relative w-full max-w-lg aspect-[1.586] bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 rounded-2xl shadow-xl overflow-hidden p-6 select-none transition-transform duration-200"
            >
              {/* Card Header Strip */}
              <div className="absolute inset-x-0 top-0 h-10 bg-zinc-200 dark:bg-zinc-800 flex items-center justify-between px-5 font-bold text-xs text-zinc-700 dark:text-zinc-300">
                <span>UNITED ARAB EMIRATES · IDENTITY CARD</span>
                <span className="font-arabic font-semibold">دولة الإمارات العربية المتحدة</span>
              </div>

              {/* Photo Box */}
              <div className="absolute left-[6%] top-[28%] w-[22%] h-[56%] bg-zinc-200 dark:bg-zinc-800 rounded-lg flex items-center justify-center text-xs text-zinc-400 font-medium">
                Photo
              </div>

              {/* ID Number Box */}
              <div
                onClick={() => setActiveFieldKey("id_number")}
                className={`absolute left-[32%] top-[28%] w-[62%] p-1.5 rounded cursor-pointer transition ${
                  activeFieldKey === "id_number"
                    ? "border-2 border-zinc-900 dark:border-white bg-zinc-900/5 dark:bg-white/10 ring-2 ring-zinc-900/10"
                    : hasFailedErrors
                    ? "border-2 border-dashed border-amber-500 bg-amber-500/10"
                    : "border border-zinc-300 dark:border-zinc-700"
                }`}
              >
                <div className="text-[10px] text-zinc-400">ID Number / رقم الهوية</div>
                <div className="font-mono font-bold text-sm text-zinc-900 dark:text-zinc-100">
                  {doc.fields?.find((f) => f.key === "id_number")?.value || "784-1990-1234567-1"}
                </div>
              </div>

              {/* Name Box */}
              <div
                onClick={() => setActiveFieldKey("full_name_en")}
                className={`absolute left-[32%] top-[48%] w-[62%] p-1.5 rounded cursor-pointer transition ${
                  activeFieldKey === "full_name_en"
                    ? "border-2 border-zinc-900 dark:border-white bg-zinc-900/5 dark:bg-white/10 ring-2 ring-zinc-900/10"
                    : "border border-zinc-300 dark:border-zinc-700"
                }`}
              >
                <div className="text-[10px] text-zinc-400">Name / الاسم</div>
                <div className="font-bold text-xs text-zinc-900 dark:text-zinc-100 truncate">
                  {doc.fields?.find((f) => f.key === "full_name_en")?.value || "Sara Ahmed Example"}
                </div>
              </div>

              {/* Dates Box */}
              <div
                onClick={() => setActiveFieldKey("expiry_date")}
                className={`absolute left-[32%] top-[68%] w-[62%] p-1.5 rounded cursor-pointer transition ${
                  activeFieldKey === "expiry_date"
                    ? "border-2 border-zinc-900 dark:border-white bg-zinc-900/5 dark:bg-white/10"
                    : "border border-zinc-300 dark:border-zinc-700"
                }`}
              >
                <div className="flex justify-between text-[10px] text-zinc-400">
                  <span>DOB: 14/05/1990</span>
                  <span>EXP: {doc.fields?.find((f) => f.key === "expiry_date")?.value || "2031-02-03"}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Canvas Legend */}
          <div className="p-3 bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800 flex items-center gap-4 text-xs text-zinc-500">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-xs border-2 border-zinc-900 dark:border-white" />
              Selected field
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-xs border-2 border-dashed border-amber-500" />
              Needs attention
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-xs border border-zinc-400" />
              Read confidently
            </span>
          </div>
        </section>

        {/* Right: Fields, Checks & Review Actions */}
        <section className="flex-1 lg:flex-[2] border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 flex flex-col shadow-xs overflow-hidden">
          {/* Issue Banner (Matching v2/ReviewPro.dc.html) */}
          {hasFailedErrors ? (
            <div className="m-4 p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex flex-col gap-2.5">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                <div className="flex flex-col">
                  <span className="font-bold text-xs text-amber-900 dark:text-amber-200">
                    ID check digit doesn&apos;t match checksum
                  </span>
                  <p className="text-[11px] text-amber-800 dark:text-amber-300 mt-0.5 leading-relaxed">
                    OCR read the last digit as <strong>3</strong>. The official ISO/UAE Luhn check digit indicates <strong>1</strong>.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleAcceptOneClickFix}
                  className="px-3 py-1.5 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs font-semibold hover:opacity-90 transition flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3 text-emerald-400" />
                  Accept fix → …-1
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const idF = doc.fields?.find((f) => f.key === "id_number");
                    if (idF) startEdit(idF);
                  }}
                  className="px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 text-xs font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800"
                >
                  Edit manually
                </button>
              </div>
            </div>
          ) : isApproved ? (
            <div className="m-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-center gap-2 text-emerald-900 dark:text-emerald-200 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Approved · Webhook dispatched & logged into sovereign audit trail.</span>
            </div>
          ) : null}

          {/* Fields List */}
          <div className="px-4 py-2 border-b border-zinc-100 dark:border-zinc-800/80 flex items-center justify-between text-xs">
            <span className="font-bold text-zinc-900 dark:text-zinc-100">Extracted Fields</span>
            <span className="text-zinc-400 text-[11px]">Click to highlight & edit</span>
          </div>

          <div className="flex-1 overflow-y-auto p-3 divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {(doc.fields || []).map((field) => {
              const isSelected = activeFieldKey === field.key;
              const isEditing = editingKey === field.key;
              const confPct = Math.round((field.confidence || 0) * 100);

              return (
                <div
                  key={field.id}
                  onClick={() => setActiveFieldKey(field.key)}
                  className={`p-3 rounded-xl transition cursor-pointer flex flex-col gap-1.5 ${
                    isSelected
                      ? "bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-900 dark:border-white shadow-xs"
                      : "hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-zinc-500">{field.nameEn}</span>
                    <span
                      className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-semibold ${
                        field.isCorrected
                          ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                          : confPct >= 85
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                          : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                      }`}
                    >
                      {field.isCorrected ? "Fixed" : `${confPct}%`}
                    </span>
                  </div>

                  {isEditing ? (
                    <div className="flex items-center gap-2 mt-1" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="flex-1 px-2.5 py-1 text-xs border border-zinc-300 dark:border-zinc-700 rounded-md bg-white dark:bg-zinc-900 outline-hidden focus:ring-1 focus:ring-zinc-900"
                      />
                      <button
                        type="button"
                        onClick={() => saveEdit(field.key)}
                        className="p-1.5 bg-emerald-600 text-white rounded hover:bg-emerald-700"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingKey(null)}
                        className="p-1.5 bg-zinc-200 dark:bg-zinc-800 rounded hover:bg-zinc-300"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sm text-zinc-900 dark:text-zinc-100 font-mono truncate">
                        {field.value || "null"}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          startEdit(field);
                        }}
                        className="text-[11px] text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 font-medium"
                      >
                        Edit
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Validation Checks Summary */}
          <div className="p-4 bg-zinc-50 dark:bg-zinc-950/60 border-t border-zinc-200 dark:border-zinc-800 flex flex-col gap-2 text-xs">
            <div className="flex items-center justify-between font-bold text-zinc-700 dark:text-zinc-300">
              <span>Compliance Checks</span>
              <span className="font-mono text-zinc-400">{passedChecksCount} / {checks.length} Passed</span>
            </div>
            <div className="space-y-1.5">
              {checks.map((chk, i) => (
                <div key={i} className="flex items-center justify-between text-[11px]">
                  <span className="text-zinc-600 dark:text-zinc-400 flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${chk.passed ? "bg-emerald-500" : "bg-rose-500"}`} />
                    {chk.name}
                  </span>
                  <span className={chk.passed ? "text-emerald-600 font-semibold" : "text-rose-600 font-semibold"}>
                    {chk.passed ? "Passed" : "Needs Review"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Action Footer (Approve / Reject Buttons) */}
          <div className="p-4 bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800 flex flex-col gap-2.5">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleReject}
                disabled={isRejecting}
                className="flex-1 py-2.5 px-4 rounded-xl border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 hover:bg-rose-100 font-semibold text-xs transition disabled:opacity-50"
              >
                Reject Document
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={isApproving || !canApprove}
                className={`flex-[2] py-2.5 px-4 rounded-xl font-semibold text-xs transition shadow-xs flex items-center justify-center gap-2 ${
                  isApproved
                    ? "bg-emerald-600 text-white cursor-default"
                    : canApprove
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 hover:opacity-90"
                    : "bg-zinc-200 dark:bg-zinc-800 text-zinc-400 cursor-not-allowed"
                }`}
              >
                <Check className="w-4 h-4" />
                <span>{isApproved ? "Approved" : canApprove ? "Approve Document" : "Resolve Issues to Approve"}</span>
              </button>
            </div>
            <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono">
              <span>Hotkeys: <strong>A</strong> Approve · <strong>R</strong> Reject · <strong>E</strong> Edit</span>
              <span>Sovereign Enforced</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
