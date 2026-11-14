import React, { useEffect } from "react";
import { useApp } from "@/context/AppContext";
import { DocumentViewer } from "@/components/common/DocumentViewer";
import { FieldRow } from "@/components/common/FieldRow";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ConfidenceBadge } from "@/components/common/ConfidenceBadge";
import {
  CheckCircle2,
  XCircle,
  RotateCcw,
  AlertTriangle,
  Table as TableIcon,
  ShieldCheck,
  Keyboard,
  ArrowRight,
  ArrowLeft,
  ChevronDown,
} from "lucide-react";

export function ReviewScreen() {
  const {
    selectedDocument,
    selectedDocumentId,
    documents,
    setSelectedDocumentId,
    activeFieldKey,
    setActiveFieldKey,
    updateTableRow,
    approveDocument,
    rejectDocument,
    togglePiiMasked,
    language,
    dir,
    t,
  } = useApp();

  const Arrow = dir === "rtl" ? ArrowLeft : ArrowRight;

  // Keyboard navigation shortcuts [J / K / Enter / M]
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!selectedDocument) return;

      // Avoid capturing when user is typing inside an input
      if (["INPUT", "TEXTAREA"].includes((e.target as HTMLElement).tagName)) {
        return;
      }

      if (e.key === "j" || e.key === "J") {
        // Next field
        const fields = selectedDocument.fields;
        const currentIndex = fields.findIndex((f) => f.key === activeFieldKey);
        const nextIndex = (currentIndex + 1) % fields.length;
        setActiveFieldKey(fields[nextIndex].key);
      } else if (e.key === "k" || e.key === "K") {
        // Prev field
        const fields = selectedDocument.fields;
        const currentIndex = fields.findIndex((f) => f.key === activeFieldKey);
        const prevIndex = (currentIndex - 1 + fields.length) % fields.length;
        setActiveFieldKey(fields[prevIndex].key);
      } else if (e.key === "Enter") {
        // Approve
        approveDocument(selectedDocument.id);
      } else if (e.key === "m" || e.key === "M") {
        // Toggle PII
        togglePiiMasked();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedDocument, activeFieldKey, approveDocument, setActiveFieldKey, togglePiiMasked]);

  if (!selectedDocument) {
    return <div className="p-8 text-center">No document found.</div>;
  }

  // Group fields by section
  const sections: { key: string; titleEn: string; titleAr: string }[] = [
    { key: "identity", titleEn: "Identity & Registration", titleAr: "الهوية والتسجيل" },
    { key: "company", titleEn: "Company & Entity Details", titleAr: "بيانات المنشأة والشركة" },
    { key: "dates", titleEn: "Critical Dates & Validity", titleAr: "التواريخ والصلاحية" },
    { key: "financials", titleEn: "Financials & Tax (AED)", titleAr: "البيانات المالية والضريبية" },
    { key: "general", titleEn: "General Metadata", titleAr: "بيانات عامة" },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-100px)] space-y-3">
      {/* Top Document Switcher & Status Bar */}
      <div className="p-3 bg-card border border-border rounded-xl shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <select
            value={selectedDocumentId}
            onChange={(e) => setSelectedDocumentId(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-border bg-secondary font-bold text-foreground text-xs focus:ring-1 focus:ring-primary"
          >
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.referenceNumber} - {d.fileName} ({d.status.toUpperCase()})
              </option>
            ))}
          </select>

          <span className="text-muted-foreground hidden sm:inline">•</span>
          <span className="font-semibold text-foreground hidden sm:inline">
            {language === "ar" ? selectedDocument.documentTypeNameAr : selectedDocument.documentTypeNameEn}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <StatusBadge status={selectedDocument.status} />
          <ConfidenceBadge score={selectedDocument.overallConfidence} />
        </div>
      </div>

      {/* Main Review Workspace: Two Columns */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
        {/* Left: Document Viewer with Bounding Boxes (7 cols) */}
        <div className="lg:col-span-7 h-full min-h-[460px]">
          <DocumentViewer />
        </div>

        {/* Right: Extracted Fields, Editable Grids, and Validation Panel (5 cols) */}
        <div className="lg:col-span-5 flex flex-col h-full bg-card border border-border rounded-xl shadow-sm overflow-hidden text-xs">
          {/* Header */}
          <div className="px-4 py-3 border-b border-border bg-secondary/30 flex items-center justify-between">
            <h2 className="font-extrabold text-xs text-foreground uppercase tracking-wider">
              {language === "ar" ? "الحقول والبيانات المستخرجة" : "Extracted Fields & Citations"}
            </h2>
            <span className="text-[11px] font-mono text-muted-foreground">
              {selectedDocument.fields.length} {language === "ar" ? "حقول" : "fields"}
            </span>
          </div>

          {/* Scrollable Fields Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            {/* Validation Errors Alert Box */}
            {selectedDocument.validationErrors.length > 0 && (
              <div className="p-3.5 rounded-lg border border-rose-300 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 text-rose-900 dark:text-rose-200 space-y-1.5">
                <div className="flex items-center gap-1.5 font-bold text-xs text-rose-800 dark:text-rose-300">
                  <AlertTriangle className="w-4 h-4" />
                  <span>{language === "ar" ? "تنبيه التحقق الرقابي" : "Validation Engine Flag"}</span>
                </div>
                {selectedDocument.validationErrors.map((err) => (
                  <p key={err.id} className="text-xs leading-relaxed ps-5">
                    {language === "ar" ? err.messageAr : err.messageEn}
                  </p>
                ))}
              </div>
            )}

            {/* Field Groups */}
            {sections.map((section) => {
              const secFields = selectedDocument.fields.filter((f) => f.section === section.key);
              if (secFields.length === 0) return null;

              return (
                <div key={section.key} className="space-y-2">
                  <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                    {language === "ar" ? section.titleAr : section.titleEn}
                  </div>
                  <div className="space-y-2">
                    {secFields.map((field) => (
                      <FieldRow key={field.id} field={field} docId={selectedDocument.id} />
                    ))}
                  </div>
                </div>
              );
            })}

            {/* Editable Table Grid (If Document has Line Items / Invoices) */}
            {selectedDocument.tableData && selectedDocument.tableData.length > 0 && (
              <div className="space-y-2.5 pt-2 border-t border-border">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                    <TableIcon className="w-3.5 h-3.5 text-primary" />
                    <span>{language === "ar" ? "جدول البنود المستخرجة (قابل للتعديل)" : "Extracted Line Items (Editable Grid)"}</span>
                  </div>
                </div>

                <div className="border border-border rounded-lg overflow-x-auto">
                  <table className="w-full text-start text-[11px]">
                    <thead className="bg-secondary text-muted-foreground font-semibold border-b border-border">
                      <tr>
                        <th className="p-2 text-start">Description</th>
                        <th className="p-2 w-16 text-center">Qty</th>
                        <th className="p-2 w-24 text-end">Price (AED)</th>
                        <th className="p-2 w-28 text-end">Total (AED)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {selectedDocument.tableData.map((row) => (
                        <tr key={row.id} className="hover:bg-secondary/30">
                          <td className="p-2 text-foreground font-medium">{row.itemDescription}</td>
                          <td className="p-2 text-center">
                            <input
                              type="number"
                              value={row.quantity}
                              onChange={(e) =>
                                updateTableRow(selectedDocument.id, row.id, "quantity", Number(e.target.value))
                              }
                              className="w-12 text-center py-0.5 rounded border border-border bg-background font-mono text-xs focus:ring-1 focus:ring-primary"
                            />
                          </td>
                          <td className="p-2 text-end">
                            <input
                              type="number"
                              value={row.unitPriceAED}
                              onChange={(e) =>
                                updateTableRow(selectedDocument.id, row.id, "unitPriceAED", Number(e.target.value))
                              }
                              className="w-20 text-end py-0.5 rounded border border-border bg-background font-mono text-xs focus:ring-1 focus:ring-primary"
                            />
                          </td>
                          <td className="p-2 text-end font-mono font-bold text-emerald-800 dark:text-emerald-400">
                            {row.lineTotalAED.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Action Footer Bar */}
          <div className="p-3 border-t border-border bg-secondary/40 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <button
                onClick={() => approveDocument(selectedDocument.id)}
                className="flex-1 py-2 px-3 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs flex items-center justify-center gap-1.5 shadow-sm transition"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{t("actionApprove")} (Enter)</span>
              </button>

              <button
                onClick={() => rejectDocument(selectedDocument.id)}
                className="py-2 px-3 rounded-lg border border-rose-300 dark:border-rose-900 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 font-bold text-xs flex items-center justify-center gap-1 transition"
              >
                <XCircle className="w-4 h-4" />
                <span>{t("actionReject")}</span>
              </button>

              <button
                onClick={() => {
                  setSelectedDocumentId(
                    documents[(documents.findIndex((d) => d.id === selectedDocument.id) + 1) % documents.length].id
                  );
                }}
                className="py-2 px-3 rounded-lg border border-border bg-card hover:bg-secondary font-bold text-xs text-foreground flex items-center justify-center gap-1 transition"
                title="Next Document"
              >
                <span>Next</span>
                <Arrow className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Keyboard Shortcuts Hint */}
            <div className="flex items-center justify-center gap-1 text-[10px] text-muted-foreground font-mono">
              <Keyboard className="w-3 h-3" />
              <span>{t("shortcutHint")}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
