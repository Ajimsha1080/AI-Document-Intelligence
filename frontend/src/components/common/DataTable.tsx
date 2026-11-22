"use client";

import React, { useState, useMemo } from "react";
import { useApp } from "@/context/AppContext";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import { formatDateBilingual } from "@/lib/utils";
import {
  Search,
  Trash2,
  CheckCircle2,
  Eye,
  FileSpreadsheet,
  FileCode,
  FolderOpen,
} from "lucide-react";

export function DataTable() {
  const {
    documents,
    setSelectedDocumentId,
    setCurrentScreen,
    deleteDocument,
    bulkApproveDocuments,
    bulkDeleteDocuments,
    language,
    showToast,
    addAuditLog,
    userRole,
    currentUser,
  } = useApp();

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [confidenceFilter, setConfidenceFilter] = useState<string>("all");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Filtered dataset
  const filtered = useMemo(() => {
    return documents.filter((doc) => {
      // Search
      const searchMatch =
        !searchTerm ||
        doc.fileName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.referenceNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.documentTypeNameEn.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.documentTypeNameAr.includes(searchTerm);

      // Status
      const statusMatch = statusFilter === "all" || doc.status === statusFilter;

      // Type
      const typeMatch = typeFilter === "all" || doc.documentType === typeFilter;

      // Confidence
      let confMatch = true;
      if (confidenceFilter === "high") confMatch = doc.overallConfidence >= 0.90;
      if (confidenceFilter === "medium")
        confMatch = doc.overallConfidence >= 0.75 && doc.overallConfidence < 0.90;
      if (confidenceFilter === "low") confMatch = doc.overallConfidence < 0.75;

      return searchMatch && statusMatch && typeMatch && confMatch;
    });
  }, [documents, searchTerm, statusFilter, typeFilter, confidenceFilter]);

  // Bulk Selection
  const toggleSelectAll = () => {
    if (selectedIds.length === filtered.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filtered.map((d) => d.id));
    }
  };

  const toggleSelectOne = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Export functions
  const handleExportJSON = () => {
    const docsToExport = documents.filter((d) =>
      selectedIds.length > 0 ? selectedIds.includes(d.id) : true
    );
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(docsToExport, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `uae_doc_intelligence_export_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    addAuditLog({
      actorName: currentUser?.name || "User",
      actorEmail: currentUser?.email || "",
      actorRole: userRole.toUpperCase(),
      action: "DOCUMENT_EXPORTED",
      detailsEn: `Exported ${docsToExport.length} documents as JSON payload`,
      detailsAr: `تم تصوير وتصدير ${docsToExport.length} مستندات بصيغة JSON`,
    });

    showToast("success", `Exported ${docsToExport.length} documents (JSON)!`, `تم تصدير ${docsToExport.length} مستندات بنجاح!`);
  };

  const handleExportCSV = () => {
    const docsToExport = documents.filter((d) =>
      selectedIds.length > 0 ? selectedIds.includes(d.id) : true
    );
    const headers = ["Reference", "FileName", "DocType", "Status", "Confidence", "UploadedAt"];
    const rows = docsToExport.map((d) => [
      d.referenceNumber,
      `"${d.fileName}"`,
      `"${d.documentTypeNameEn}"`,
      d.status,
      `${Math.round(d.overallConfidence * 100)}%`,
      d.uploadedAt,
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `uae_doc_intelligence_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();

    addAuditLog({
      actorName: currentUser?.name || "User",
      actorEmail: currentUser?.email || "",
      actorRole: userRole.toUpperCase(),
      action: "DOCUMENT_EXPORTED",
      detailsEn: `Exported ${docsToExport.length} documents as CSV spreadsheet`,
      detailsAr: `تم تصوير وتصدير ${docsToExport.length} مستندات بصيغة CSV`,
    });

    showToast("success", `Exported ${docsToExport.length} documents (CSV)!`, `تم تصدير ${docsToExport.length} مستندات (CSV)!`);
  };

  return (
    <div className="space-y-4">
      {/* Document Management Center Header */}
      <div className="p-5 rounded-2xl border border-border/80 bg-card shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-primary" />
            <h1 className="text-base font-bold text-foreground">
              {language === "ar" ? "مركز إدارة المستندات والأرشيف السيادي" : "Document Management Center"}
            </h1>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {language === "ar"
              ? "إدارة وتصفية وتصدير جميع وثائق الهوية والتراخيص التجارية والفواتير المصنفة محلياً"
              : "Search, filter, review, and export all sovereign in-country classified documents."}
          </p>
        </div>

        {/* Action Buttons: Export JSON & Export CSV */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleExportCSV}
            className="px-3 py-1.5 rounded-lg border border-border/80 bg-secondary/60 hover:bg-secondary font-semibold text-foreground text-xs flex items-center gap-1.5 transition shadow-xs"
            title="Export CSV"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>Export CSV</span>
          </button>
          <button
            onClick={handleExportJSON}
            className="px-3 py-1.5 rounded-lg border border-border/80 bg-secondary/60 hover:bg-secondary font-semibold text-foreground text-xs flex items-center gap-1.5 transition shadow-xs"
            title="Export JSON"
          >
            <FileCode className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Export JSON</span>
          </button>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="p-3 rounded-xl border border-border/80 bg-card shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={language === "ar" ? "ابحث بالاسم أو الرقم المرجعي..." : "Filter by name or reference..."}
            className="w-full ps-9 pe-4 py-1.5 rounded-lg border border-border/80 bg-secondary/40 text-foreground placeholder:text-muted-foreground/70 text-xs focus:outline-none focus:ring-1 focus:ring-primary focus:bg-background transition"
          />
        </div>

        {/* Filter Dropdowns */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-border/80 bg-secondary/40 text-foreground text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">{language === "ar" ? "كل الحالات" : "All Statuses"}</option>
            <option value="needs_review">Needs Review</option>
            <option value="approved">Approved</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-border/80 bg-secondary/40 text-foreground text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">{language === "ar" ? "كل الأنواع" : "All Types"}</option>
            <option value="emirates_id">Emirates ID</option>
            <option value="uae_trade_license">Trade License</option>
            <option value="commercial_invoice">Tax Invoice</option>
          </select>

          {/* Confidence Filter */}
          <select
            value={confidenceFilter}
            onChange={(e) => setConfidenceFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg border border-border/80 bg-secondary/40 text-foreground text-xs font-medium focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">{language === "ar" ? "كل الثقة" : "All Confidence"}</option>
            <option value="high">High (≥ 90%)</option>
            <option value="medium">Medium (75% - 89%)</option>
            <option value="low">Low (&lt; 75%)</option>
          </select>
        </div>
      </div>

      {/* Bulk Actions Header (When Selected) */}
      {selectedIds.length > 0 && (
        <div className="p-2.5 rounded-xl bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 border border-zinc-800 flex items-center justify-between gap-3 text-xs shadow-sm animate-in fade-in">
          <span className="font-semibold px-2">
            {selectedIds.length} {language === "ar" ? "مستندات محددة" : "documents selected"}
          </span>

          <div className="flex items-center gap-2">
            {userRole !== "viewer" && (
              <button
                onClick={() => {
                  bulkApproveDocuments(selectedIds);
                  setSelectedIds([]);
                }}
                className="px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center gap-1.5 text-xs transition"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{language === "ar" ? "اعتماد المحدد" : "Bulk Approve"}</span>
              </button>
            )}

            {userRole === "admin" && (
              <button
                onClick={() => {
                  bulkDeleteDocuments(selectedIds);
                  setSelectedIds([]);
                }}
                className="px-3 py-1 rounded-md bg-rose-600 hover:bg-rose-500 text-white font-semibold flex items-center gap-1.5 text-xs transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{language === "ar" ? "حذف نهائي" : "Hard Delete"}</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Data Table */}
      <div className="rounded-xl border border-border/80 bg-card shadow-xs overflow-hidden text-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-start border-collapse">
            <thead>
              <tr className="border-b border-border/80 bg-secondary/30 text-muted-foreground font-semibold text-[11px] uppercase tracking-wider">
                <th className="p-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === filtered.length && filtered.length > 0}
                    onChange={toggleSelectAll}
                    className="rounded border-border text-primary focus:ring-primary cursor-pointer"
                  />
                </th>
                <th className="p-3 text-start">{language === "ar" ? "المستند" : "Document"}</th>
                <th className="p-3 text-start">{language === "ar" ? "النوع" : "Type"}</th>
                <th className="p-3 text-start">{language === "ar" ? "الحالة" : "Status"}</th>
                <th className="p-3 text-start">{language === "ar" ? "درجة الثقة" : "Confidence"}</th>
                <th className="p-3 text-start">{language === "ar" ? "تاريخ التحميل" : "Ingested Date"}</th>
                <th className="p-3 text-end">{language === "ar" ? "إجراءات" : "Actions"}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-muted-foreground">
                    {language === "ar" ? "لم يتم العثور على أي مستندات تطابق هذا البحث" : "No documents match the current filters"}
                  </td>
                </tr>
              ) : (
                filtered.map((doc) => {
                  const isChecked = selectedIds.includes(doc.id);
                  return (
                    <tr
                      key={doc.id}
                      onClick={() => {
                        setSelectedDocumentId(doc.id);
                        setCurrentScreen("review");
                      }}
                      className={`hover:bg-secondary/40 transition-colors cursor-pointer ${
                        isChecked ? "bg-primary/5" : ""
                      }`}
                    >
                      <td className="p-3 text-center" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleSelectOne(doc.id)}
                          className="rounded border-border text-primary focus:ring-primary cursor-pointer"
                        />
                      </td>
                      <td className="p-3 font-medium text-foreground">
                        <div className="font-semibold text-foreground">{doc.fileName}</div>
                        <div className="text-[10px] text-muted-foreground font-mono">{doc.referenceNumber}</div>
                      </td>
                      <td className="p-3 text-foreground font-medium">
                        {language === "ar" ? doc.documentTypeNameAr : doc.documentTypeNameEn}
                      </td>
                      <td className="p-3">
                        <StatusBadge status={doc.status} />
                      </td>
                      <td className="p-3">
                        <ConfidenceBadge score={doc.overallConfidence} />
                      </td>
                      <td className="p-3 text-muted-foreground font-mono text-[11px]">
                        {formatDateBilingual(doc.uploadedAt, language === "ar")}
                      </td>
                      <td className="p-3 text-end" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => {
                              setSelectedDocumentId(doc.id);
                              setCurrentScreen("review");
                            }}
                            className="px-2.5 py-1 rounded-md border border-border/80 bg-secondary/50 hover:bg-secondary text-foreground font-semibold text-xs transition flex items-center gap-1 shadow-xs"
                          >
                            <Eye className="w-3.5 h-3.5 text-muted-foreground" />
                            <span>{language === "ar" ? "معاينة" : "Review"}</span>
                          </button>

                          {userRole === "admin" && (
                            <button
                              onClick={() => deleteDocument(doc.id)}
                              className="p-1 rounded-md text-muted-foreground hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition"
                              title="Hard Delete"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
