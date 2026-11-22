"use client";

import React, { useState } from "react";
import { useApp } from "@/context/AppContext";
import { DocumentStatus } from "@/types";
import { ArrowUpRight, CheckCircle2, AlertCircle, FileText, ChevronRight, Trash2 } from "lucide-react";

export function CommandCenterScreen() {
  const {
    documents,
    selectedDocumentId,
    setSelectedDocumentId,
    setCurrentScreen,
    language,
    userRole,
    deleteDocument,
    showToast,
    setIsUploadModalOpen,
  } = useApp();

  const [activeTab, setActiveTab] = useState<"all" | DocumentStatus>("all");

  const selectedDoc = documents.find((d) => d.id === selectedDocumentId) || documents[0];

  const totalCount = documents.length;
  const needsReviewDocs = documents.filter((d) => d.status === "needs_review");
  const approvedDocs = documents.filter((d) => d.status === "approved");
  const processingDocs = documents.filter((d) => d.status === "processing");
  const failedDocs = documents.filter((d) => d.status === "failed");

  const straightThroughRate = totalCount > 0 ? Math.round((approvedDocs.length / totalCount) * 100) : 92;

  const filteredDocuments = documents.filter((d) => {
    if (activeTab === "all") return true;
    return d.status === activeTab;
  });

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case "approved":
        return {
          dot: "bg-emerald-500",
          text: language === "ar" ? "معتمد" : "Approved",
          chip: "text-emerald-700 bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800",
        };
      case "needs_review":
        return {
          dot: "bg-amber-500",
          text: language === "ar" ? "بحاجة للمراجعة" : "Needs review",
          chip: "text-amber-800 bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800",
        };
      case "processing":
        return {
          dot: "bg-blue-500 animate-pulse",
          text: language === "ar" ? "قيد المعالجة" : "Processing",
          chip: "text-blue-700 bg-blue-50 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800",
        };
      default:
        return {
          dot: "bg-rose-500",
          text: language === "ar" ? "مرفوض" : "Rejected",
          chip: "text-rose-700 bg-rose-50 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800",
        };
    }
  };

  const handleOpenReview = (docId: string) => {
    setSelectedDocumentId(docId);
    setCurrentScreen("review");
  };

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to hard delete this document and all extracted data?")) {
      try {
        await deleteDocument(docId);
        showToast("success", "Document deleted successfully", "تم حذف المستند بنجاح");
      } catch (err: any) {
        showToast("error", err.message || "Failed to delete document", "تعذر حذف المستند");
      }
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Top Banner / Metrics Cards (Matching v2/Command.dc.html) */}
      <section className="grid grid-cols-2 md:grid-cols-4 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 divide-x divide-y md:divide-y-0 divide-zinc-200 dark:divide-zinc-800 shadow-xs overflow-hidden">
        <div className="p-4 flex flex-col gap-1.5">
          <span className="text-xs text-zinc-500 font-medium">Total Ingested</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">{totalCount}</span>
            <div className="flex items-end gap-1 h-5" aria-hidden="true">
              {[40, 65, 45, 80, 95, 60, 85].map((h, i) => (
                <span key={i} className="w-1 bg-emerald-500/80 rounded-t" style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>
          <span className="text-[11px] text-zinc-400">All tenant documents</span>
        </div>

        <div className="p-4 flex flex-col gap-1.5">
          <span className="text-xs text-zinc-500 font-medium">Needs Review</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold tracking-tight text-amber-600 dark:text-amber-400">
              {needsReviewDocs.length}
            </span>
            <div className="flex items-end gap-1 h-5" aria-hidden="true">
              {[80, 50, 90, 70, 60, 85, 90].map((h, i) => (
                <span key={i} className="w-1 bg-amber-500/80 rounded-t" style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>
          <span className="text-[11px] text-zinc-400">Awaiting human review</span>
        </div>

        <div className="p-4 flex flex-col gap-1.5">
          <span className="text-xs text-zinc-500 font-medium">Straight-Through</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">{straightThroughRate}%</span>
            <div className="flex items-end gap-1 h-5" aria-hidden="true">
              {[70, 75, 80, 85, 90, 88, 92].map((h, i) => (
                <span key={i} className="w-1 bg-emerald-500/80 rounded-t" style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>
          <span className="text-[11px] text-zinc-400">Zero touch auto-approved</span>
        </div>

        <div className="p-4 flex flex-col gap-1.5">
          <span className="text-xs text-zinc-500 font-medium">Avg Processing P95</span>
          <div className="flex items-baseline justify-between">
            <span className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">1.8s</span>
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full">
              In-Country
            </span>
          </div>
          <span className="text-[11px] text-zinc-400">Zero foreign egress</span>
        </div>
      </section>

      {/* Main Workspace Split: Table + Side Sheet */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Left Column: Documents Table */}
        <div className="flex-1 w-full flex flex-col gap-3 min-w-0">
          {/* Filter Bar & Hotkey Hints */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1 p-1 bg-zinc-100 dark:bg-zinc-800/80 rounded-lg text-xs font-medium">
              {[
                { id: "all", label: "All", count: totalCount },
                { id: "needs_review", label: "Needs Review", count: needsReviewDocs.length },
                { id: "approved", label: "Approved", count: approvedDocs.length },
                { id: "processing", label: "Processing", count: processingDocs.length },
                { id: "failed", label: "Rejected", count: failedDocs.length },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id as any)}
                  className={`px-3 py-1.5 rounded-md transition flex items-center gap-1.5 ${
                    activeTab === t.id
                      ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-50 shadow-xs font-semibold"
                      : "text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
                  }`}
                >
                  <span>{t.label}</span>
                  <span className="text-[11px] font-mono text-zinc-400">{t.count}</span>
                </button>
              ))}
            </div>

            <div className="hidden sm:flex items-center gap-2 text-xs text-zinc-400">
              <span className="font-mono bg-white dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-800">J</span>
              <span className="font-mono bg-white dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-800">K</span>
              <span>navigate</span>
              <span className="font-mono bg-white dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-800">↵</span>
              <span>open</span>
            </div>
          </div>

          {/* Table Container */}
          <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 overflow-hidden shadow-xs">
            <div className="grid grid-cols-12 gap-3 px-4 py-2.5 text-xs font-semibold text-zinc-500 bg-zinc-50 dark:bg-zinc-950/60 border-b border-zinc-200 dark:border-zinc-800">
              <span className="col-span-5">Document</span>
              <span className="col-span-3">Status</span>
              <span className="col-span-2">Confidence</span>
              <span className="col-span-2 text-end">Action</span>
            </div>

            <div className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {filteredDocuments.length === 0 ? (
                <div className="p-12 text-center text-zinc-400 text-sm flex flex-col items-center gap-2">
                  <FileText className="w-8 h-8 text-zinc-300 dark:text-zinc-700" />
                  <span>No documents found in this status.</span>
                  <button
                    onClick={() => setIsUploadModalOpen(true)}
                    className="mt-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:underline"
                  >
                    + Upload your first document
                  </button>
                </div>
              ) : (
                filteredDocuments.map((doc) => {
                  const statusInfo = getStatusBadge(doc.status);
                  const isSelected = selectedDoc?.id === doc.id;
                  const confPct = Math.round((doc.overallConfidence || 0) * 100);

                  return (
                    <div
                      key={doc.id}
                      onClick={() => setSelectedDocumentId(doc.id)}
                      className={`grid grid-cols-12 gap-3 px-4 py-3 items-center text-xs cursor-pointer transition ${
                        isSelected
                          ? "bg-zinc-50 dark:bg-zinc-800/60 border-s-2 border-emerald-600 dark:border-emerald-400"
                          : "hover:bg-zinc-50/60 dark:hover:bg-zinc-800/30"
                      }`}
                    >
                      {/* Document Name & Type */}
                      <div className="col-span-5 flex flex-col min-w-0">
                        <span className="font-semibold text-zinc-900 dark:text-zinc-100 truncate">
                          {doc.fileName}
                        </span>
                        <span className="text-[11px] text-zinc-400 font-mono truncate">
                          {doc.referenceNumber} · {doc.documentTypeNameEn}
                        </span>
                      </div>

                      {/* Status */}
                      <div className="col-span-3 flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${statusInfo.dot}`} />
                        <span className="font-medium text-zinc-700 dark:text-zinc-300">
                          {statusInfo.text}
                        </span>
                      </div>

                      {/* Confidence Bar & Pct */}
                      <div className="col-span-2 flex items-center gap-2">
                        <div className="flex-1 bg-zinc-200 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden hidden sm:block">
                          <div
                            className={`h-full rounded-full ${
                              confPct >= 85
                                ? "bg-emerald-500"
                                : confPct >= 65
                                ? "bg-amber-500"
                                : "bg-rose-500"
                            }`}
                            style={{ width: `${confPct}%` }}
                          />
                        </div>
                        <span className="font-mono text-zinc-500 text-[11px]">{confPct}%</span>
                      </div>

                      {/* Quick Action Button */}
                      <div className="col-span-2 flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleOpenReview(doc.id)}
                          className="px-2.5 py-1 rounded-md bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-semibold hover:opacity-90 transition text-[11px] flex items-center gap-1"
                        >
                          Review
                          <ArrowUpRight className="w-3 h-3" />
                        </button>
                        {userRole === "admin" && (
                          <button
                            type="button"
                            onClick={(e) => handleDelete(doc.id, e)}
                            className="p-1 text-zinc-400 hover:text-rose-600 transition"
                            title="Delete document"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Selected Document Side Sheet (Matching v2/Command.dc.html) */}
        {selectedDoc && (
          <aside className="w-full lg:w-80 shrink-0 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-900 p-5 flex flex-col gap-4 shadow-xs sticky top-20">
            <div className="flex flex-col gap-1">
              <span className="text-[11px] font-mono text-zinc-400">{selectedDoc.referenceNumber}</span>
              <h3 className="font-bold text-base text-zinc-900 dark:text-zinc-100 truncate">
                {selectedDoc.fileName}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getStatusBadge(selectedDoc.status).chip}`}>
                  {getStatusBadge(selectedDoc.status).text}
                </span>
                <span className="text-xs text-zinc-500">{selectedDoc.documentTypeNameEn}</span>
              </div>
            </div>

            {/* Validation Callout / Alert */}
            {selectedDoc.validationErrors && selectedDoc.validationErrors.length > 0 ? (
              <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-xs flex flex-col gap-1">
                <span className="font-bold flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                  {selectedDoc.validationErrors.length} Issue(s) Requiring Attention
                </span>
                <span className="text-amber-800 dark:text-amber-300 text-[11px] leading-relaxed">
                  {selectedDoc.validationErrors[0].messageEn}
                </span>
              </div>
            ) : (
              <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>All sovereign compliance and format rules passed.</span>
              </div>
            )}

            {/* Extracted Fields Summary */}
            <div className="flex flex-col border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden text-xs divide-y divide-zinc-100 dark:divide-zinc-800">
              {(selectedDoc.fields || []).slice(0, 4).map((f) => (
                <div key={f.id} className="p-2.5 flex items-center justify-between gap-2">
                  <span className="text-zinc-500">{f.nameEn}</span>
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100 font-mono truncate max-w-[140px]">
                    {f.value || "null"}
                  </span>
                </div>
              ))}
            </div>

            {/* Timeline */}
            <div className="flex flex-col gap-2 text-xs">
              <span className="font-semibold text-zinc-500 text-[11px] uppercase tracking-wider">Audit Timeline</span>
              <div className="space-y-1.5 text-[11px] text-zinc-500 font-mono">
                <div className="flex gap-2">
                  <span className="text-zinc-400">10:42</span>
                  <span>Uploaded via sovereign ingest</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-zinc-400">10:43</span>
                  <span>OCR extracted 7 fields</span>
                </div>
                <div className="flex gap-2">
                  <span className="text-zinc-400">10:44</span>
                  <span>Rules engine evaluated checks</span>
                </div>
              </div>
            </div>

            {/* CTA Button */}
            <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800">
              <button
                type="button"
                onClick={() => handleOpenReview(selectedDoc.id)}
                className="w-full py-2.5 px-4 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-semibold text-xs hover:opacity-90 transition flex items-center justify-center gap-1.5 shadow-xs"
              >
                <span>Open in Review Workspace</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
