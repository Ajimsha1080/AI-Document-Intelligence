"use client";

import React, { useState, useEffect } from "react";
import { useApp } from "@/context/AppContext";
import { ExtractedField } from "@/types";
import { api } from "@/lib/api";
import { ArrowLeft, CheckCircle2, AlertTriangle, RotateCw, Check, X } from "lucide-react";

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

  const [detailedDoc, setDetailedDoc] = useState<any>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState<boolean>(false);
  const [isForceModalOpen, setIsForceModalOpen] = useState<boolean>(false);
  const [forceReason, setForceReason] = useState<string>("Manual verification confirmed valid");

  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [rotation, setRotation] = useState<number>(0);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [isRejecting, setIsRejecting] = useState<boolean>(false);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isLoadingFile, setIsLoadingFile] = useState<boolean>(false);

  // Fetch full document details (fields, validation results, pages)
  useEffect(() => {
    if (!doc?.id) return;
    let isMounted = true;
    setIsLoadingDetails(true);

    api.documents.get(doc.id)
      .then((fullDoc) => {
        if (isMounted && fullDoc) {
          setDetailedDoc(fullDoc);
        }
      })
      .catch((err) => {
        console.warn("Could not load full document details:", err);
      })
      .finally(() => {
        if (isMounted) setIsLoadingDetails(false);
      });

    return () => {
      isMounted = false;
    };
  }, [doc?.id]);

  const currentDoc = (detailedDoc && detailedDoc.id === doc?.id) ? detailedDoc : doc;
  const isPdf = currentDoc?.fileName?.toLowerCase().endsWith(".pdf") || false;

  useEffect(() => {
    if (!doc?.id) return;
    let activeUrl: string | null = null;
    let isMounted = true;
    setIsLoadingFile(true);

    api.documents.getFileBlobUrl(doc.id)
      .then((url) => {
        if (!isMounted) {
          URL.revokeObjectURL(url);
          return;
        }
        activeUrl = url;
        setBlobUrl(url);
      })
      .catch((err) => {
        console.warn("Could not load preview blob:", err);
        if (isMounted) setBlobUrl(null);
      })
      .finally(() => {
        if (isMounted) setIsLoadingFile(false);
      });

    return () => {
      isMounted = false;
      if (activeUrl) {
        URL.revokeObjectURL(activeUrl);
      }
    };
  }, [doc?.id]);

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
      await updateDocumentField(currentDoc.id, fieldKey, editValue);
      // Reload full document details to get updated validation results from backend
      try {
        const fullDoc = await api.documents.get(currentDoc.id);
        if (fullDoc) setDetailedDoc(fullDoc);
      } catch {}
      setEditingKey(null);
    } catch (err: any) {
      showToast("error", err.message || "Failed to update field", "تعذر حفظ التعديل");
    }
  };

  // Real validation results from detailed document
  const validationResults = currentDoc.validationResults || (currentDoc.validationErrors || []).map((e: any) => ({
    id: e.id,
    ruleName: e.fieldKey || "Validation Check",
    passed: false,
    severity: e.severity,
    message: e.messageEn,
  }));
  const passedChecksCount = validationResults.filter((c: any) => c.passed).length;
  const failedErrorChecks = validationResults.filter((c: any) => !c.passed && c.severity === "error");

  const hasFailedErrors =
    failedErrorChecks.length > 0 ||
    (currentDoc.validationErrors || []).some((e: any) => e.severity === "error" && !e.isResolved);

  const isApproved = currentDoc.status === "approved";
  const canApprove = (userRole === "admin" || !hasFailedErrors) && !isApproved;

  const handleApprove = async (forceOverride = false) => {
    if (!currentDoc?.id) return;

    if (hasFailedErrors && !forceOverride) {
      if (userRole === "admin") {
        setIsForceModalOpen(true);
        return;
      } else {
        showToast("error", "Cannot approve document with unresolved errors.", "لا يمكن اعتماد المستند مع وجود أخطاء");
        return;
      }
    }

    setIsApproving(true);
    try {
      await approveDocument(currentDoc.id, forceOverride);
      setIsForceModalOpen(false);
      // Reload full document to reflect approved state
      try {
        const fullDoc = await api.documents.get(currentDoc.id);
        if (fullDoc) setDetailedDoc(fullDoc);
      } catch {}

      // Go to next review doc if available
      if (currentIndex < needsReviewList.length - 1) {
        setSelectedDocumentId(needsReviewList[currentIndex + 1].id);
      }
    } catch {
      // Toast notification is already handled by approveDocument in AppContext
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    if (!currentDoc?.id) return;
    setIsRejecting(true);
    try {
      await rejectDocument(currentDoc.id);
      if (currentIndex < needsReviewList.length - 1) {
        setSelectedDocumentId(needsReviewList[currentIndex + 1].id);
      }
    } catch {
      // Toast notification is already handled by rejectDocument in AppContext
    } finally {
      setIsRejecting(false);
    }
  };

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
            {currentDoc.fileName}
          </span>
          <span className="text-xs text-zinc-400 font-medium">{currentDoc.referenceNumber}</span>
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              currentDoc.status === "approved"
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : currentDoc.status === "needs_review"
                ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                : "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300"
            }`}
          >
            {currentDoc.status.replace("_", " ")}
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

          {/* Canvas Area with Real Document & Bounding Boxes */}
          <div className="flex-1 p-6 flex items-center justify-center overflow-auto min-h-[440px] bg-zinc-50/50 dark:bg-zinc-950/40">
            {isLoadingFile ? (
              <div className="text-xs text-zinc-400 animate-pulse">Loading sovereign document...</div>
            ) : isPdf && blobUrl ? (
              <object
                data={blobUrl}
                type="application/pdf"
                style={{ visibility: isForceModalOpen ? "hidden" : "visible" }}
                className="w-full h-full min-h-[500px] rounded-lg border border-zinc-200 dark:border-zinc-800 shadow-sm"
              >
                <iframe
                  src={blobUrl}
                  title={currentDoc.fileName}
                  className="w-full h-full min-h-[500px] rounded-lg border-0"
                />
              </object>
            ) : blobUrl ? (
              <div
                style={{ transform: `rotate(${rotation}deg)` }}
                className="relative inline-block max-w-full rounded-xl shadow-xl overflow-hidden transition-transform duration-200 select-none border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900"
              >
                <img
                  src={blobUrl}
                  alt={currentDoc.fileName}
                  className="max-w-full max-h-[600px] object-contain block"
                />
                {/* Real field bounding box overlays */}
                {(currentDoc.fields || []).map((field: any) => {
                  if (!field.bbox) return null;
                  const isSelected = activeFieldKey === field.key;
                  return (
                    <div
                      key={field.id}
                      onClick={() => setActiveFieldKey(field.key)}
                      style={{
                        position: "absolute",
                        left: `${field.bbox.x}%`,
                        top: `${field.bbox.y}%`,
                        width: `${field.bbox.width}%`,
                        height: `${field.bbox.height}%`,
                      }}
                      className={`cursor-pointer transition border rounded-xs ${
                        isSelected
                          ? "border-2 border-zinc-900 bg-zinc-900/20 ring-2 ring-zinc-900/30 z-20 dark:border-zinc-100 dark:bg-zinc-100/20"
                          : "border border-zinc-400/80 bg-zinc-400/10 hover:bg-zinc-400/25 z-10"
                      }`}
                      title={`${field.nameEn}: ${field.value || "Not found"}`}
                    />
                  );
                })}
              </div>
            ) : (
              <div className="text-xs text-zinc-400 p-8 border border-dashed border-zinc-300 dark:border-zinc-700 rounded-xl text-center">
                <span>Preview unavailable for this document.</span>
              </div>
            )}
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
                    Validation Checks Require Attention
                  </span>
                  <div className="text-[11px] text-amber-800 dark:text-amber-300 mt-0.5 space-y-1">
                    {(failedErrorChecks.length > 0 ? failedErrorChecks : (currentDoc.validationErrors || [])).map((err: any, i: number) => (
                      <p key={i} className="leading-relaxed">
                        • {err.message || err.messageEn || err.fieldKey || err.ruleName}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 pt-1">
                {currentDoc.fields?.find((f: any) => f.key === "id_number") && (
                  <button
                    type="button"
                    onClick={() => {
                      const idF = currentDoc.fields?.find((f: any) => f.key === "id_number");
                      if (idF) startEdit(idF);
                    }}
                    className="px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 text-xs font-medium hover:bg-zinc-100 dark:hover:bg-zinc-800"
                  >
                    Edit field
                  </button>
                )}
              </div>
            </div>
          ) : isApproved ? (
            <div className="m-4 p-4 rounded-xl bg-zinc-100 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 flex items-center gap-2 text-zinc-900 dark:text-zinc-100 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4 text-zinc-900 dark:text-zinc-100 shrink-0" />
              <span>Approved · Webhook dispatched & logged into sovereign audit trail.</span>
            </div>
          ) : null}

          {/* Fields List */}
          <div className="px-4 py-2 border-b border-zinc-100 dark:border-zinc-800/80 flex items-center justify-between text-xs">
            <span className="font-bold text-zinc-900 dark:text-zinc-100">Extracted Fields</span>
            <span className="text-zinc-400 text-[11px]">Click to highlight & edit</span>
          </div>

          <div className="flex-1 overflow-y-auto p-3 divide-y divide-zinc-100 dark:divide-zinc-800/60">
            {isLoadingDetails && !detailedDoc ? (
              <div className="p-8 text-center text-xs text-zinc-400 animate-pulse">
                Loading sovereign field extractions...
              </div>
            ) : (currentDoc.fields || []).length === 0 ? (
              <div className="p-8 text-center text-xs text-zinc-400">
                No fields extracted for this document.
              </div>
            ) : (
              (currentDoc.fields || []).map((field: any) => {
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
                      className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        field.isCorrected
                          ? "bg-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                          : confPct >= 85
                          ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
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
                        className="flex-1 px-2.5 py-1 text-xs border border-zinc-300 dark:border-zinc-700 rounded-md bg-white dark:bg-zinc-900 outline-hidden focus:ring-1 focus:ring-zinc-900 font-medium"
                      />
                      <button
                        type="button"
                        onClick={() => saveEdit(field.key)}
                        className="p-1.5 bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 rounded hover:opacity-90"
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
                      <span className="font-semibold text-sm text-zinc-900 dark:text-zinc-100 truncate">
                        {field.value || <span className="text-zinc-400 italic text-xs">Not found</span>}
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
            }))}
          </div>

          {/* Validation Checks Summary */}
          <div className="p-4 bg-zinc-50 dark:bg-zinc-950/60 border-t border-zinc-200 dark:border-zinc-800 flex flex-col gap-2 text-xs">
            <div className="flex items-center justify-between font-bold text-zinc-700 dark:text-zinc-300">
              <span>Validation Results</span>
              <span className="font-medium text-zinc-400">
                {passedChecksCount} / {validationResults.length} Passed
              </span>
            </div>
            {validationResults.length === 0 ? (
              <span className="text-zinc-400 text-[11px]">No validation checks run.</span>
            ) : (
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {validationResults.map((chk: any, i: number) => (
                  <div key={chk.id || i} className="flex flex-col gap-0.5 text-[11px] p-1.5 rounded-sm bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800">
                    <div className="flex items-center justify-between">
                      <span className="text-zinc-700 dark:text-zinc-300 font-medium flex items-center gap-1.5">
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${chk.passed ? "bg-zinc-900 dark:bg-zinc-100" : chk.severity === "warning" ? "bg-amber-500" : "bg-rose-500"}`} />
                        {chk.ruleName}
                      </span>
                      <span className={`font-semibold text-[10px] uppercase ${chk.passed ? "text-zinc-900 dark:text-zinc-100" : chk.severity === "warning" ? "text-amber-600" : "text-rose-600"}`}>
                        {chk.passed ? "Passed" : chk.severity === "warning" ? "Warning" : "Failed"}
                      </span>
                    </div>
                    {chk.message && (
                      <p className="text-[10px] text-zinc-500 dark:text-zinc-400 pl-3">
                        {chk.message}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action Footer (Approve / Reject Buttons) */}
          <div className="p-4 bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800 flex flex-col gap-2.5">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleReject}
                disabled={isRejecting}
                className="flex-1 py-2.5 px-4 rounded-xl border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30 hover:bg-rose-100 font-semibold text-xs transition disabled:opacity-50 cursor-pointer"
              >
                Reject Document
              </button>
              <button
                type="button"
                onClick={() => handleApprove(false)}
                disabled={isApproving || !canApprove}
                className={`flex-[2] py-2.5 px-4 rounded-xl font-semibold text-xs transition shadow-xs flex items-center justify-center gap-2 ${
                  isApproved
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 cursor-default"
                    : canApprove
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 hover:opacity-90 cursor-pointer"
                    : "bg-zinc-200 dark:bg-zinc-800 text-zinc-400 cursor-not-allowed"
                }`}
              >
                <Check className="w-4 h-4" />
                <span>{isApproved ? "Approved" : canApprove ? (hasFailedErrors ? "Force Approve (Admin)" : "Approve Document") : "Resolve Issues to Approve"}</span>
              </button>
            </div>
            <div className="flex items-center justify-between text-[10px] text-zinc-400 font-medium">
              <span>Hotkeys: <strong>A</strong> Approve · <strong>R</strong> Reject · <strong>E</strong> Edit</span>
              <span>Sovereign Enforced</span>
            </div>
          </div>
        </section>
      </div>

      {/* Admin Force Approval Modal */}
      {isForceModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
          <div
            className="w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl p-6 text-zinc-900 dark:text-zinc-100 flex flex-col gap-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-bold text-sm sm:text-base">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span>Admin Force Approval</span>
              </div>
              <button
                type="button"
                onClick={() => setIsForceModalOpen(false)}
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-zinc-500 leading-relaxed">
              This document has {failedErrorChecks.length || 1} unresolved error validation check(s). As an administrator, you can override validation and approve this document. This action will be permanently logged in the sovereign audit trail.
            </p>

            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300 space-y-1">
              <span className="font-semibold block text-[11px] uppercase tracking-wider text-rose-800 dark:text-rose-200">
                Failed Validation Checks:
              </span>
              {(failedErrorChecks.length > 0 ? failedErrorChecks : (currentDoc.validationErrors || [])).map((chk: any, idx: number) => (
                <div key={idx} className="flex items-start gap-1.5 text-[11px]">
                  <span className="font-bold">•</span>
                  <span>{chk.ruleName || chk.fieldKey || "Validation Check"}: {chk.message || chk.messageEn || "Failed rule check"}</span>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                Audit Reason for Exception Approval
              </label>
              <input
                type="text"
                value={forceReason}
                onChange={(e) => setForceReason(e.target.value)}
                placeholder="e.g. Manual verification confirmed valid"
                className="w-full px-3 py-2 text-xs border border-zinc-300 dark:border-zinc-700 rounded-lg bg-zinc-50 dark:bg-zinc-800 focus:outline-hidden focus:ring-1 focus:ring-zinc-900 dark:focus:ring-zinc-100"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setIsForceModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-zinc-200 dark:border-zinc-800 text-xs font-semibold text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isApproving || !forceReason.trim()}
                onClick={() => handleApprove(true)}
                className="px-4 py-2 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 text-xs font-semibold hover:opacity-90 transition disabled:opacity-50 flex items-center gap-1.5 shadow-xs cursor-pointer"
              >
                {isApproving ? "Approving..." : "Confirm Force Approval"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
