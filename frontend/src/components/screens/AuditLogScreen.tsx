import React, { useState, useMemo } from "react";
import { useApp } from "@/context/AppContext";
import { AuditLogEntry } from "@/types";
import { formatDateBilingual } from "@/lib/utils";
import {
  History,
  Search,
  FileSpreadsheet,
  FileCode,
} from "lucide-react";

export function AuditLogScreen() {
  const { auditLogs, language, showToast } = useApp();

  const [searchTerm, setSearchTerm] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);

  const filteredLogs = useMemo(() => {
    return auditLogs.filter((entry) => {
      const matchSearch =
        !searchTerm ||
        entry.actorName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        entry.actorEmail.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (entry.documentRef && entry.documentRef.toLowerCase().includes(searchTerm.toLowerCase())) ||
        entry.detailsEn.toLowerCase().includes(searchTerm.toLowerCase()) ||
        entry.detailsAr.includes(searchTerm);

      const matchAction = actionFilter === "all" || entry.action === actionFilter;

      return matchSearch && matchAction;
    });
  }, [auditLogs, searchTerm, actionFilter]);

  const handleExportCSV = () => {
    const headers = ["Timestamp", "Actor", "Role", "Action", "DocumentRef", "IPAddress", "Details"];
    const rows = filteredLogs.map((e) => [
      e.timestamp,
      `"${e.actorName}"`,
      e.actorRole,
      e.action,
      `"${e.documentRef || ""}"`,
      `"${e.ipAddress}"`,
      `"${e.detailsEn}"`,
    ]);

    const csv = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const link = document.createElement("a");
    link.href = encodeURI(csv);
    link.download = `uae_sovereign_audit_trail_${Date.now()}.csv`;
    link.click();
    link.remove();
    showToast("success", "Exported Audit Trail (CSV)!", "تم تصدير سجل التدقيق بنجاح!");
  };

  const handleExportJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(filteredLogs, null, 2));
    const link = document.createElement("a");
    link.href = dataStr;
    link.download = `uae_sovereign_audit_trail_${Date.now()}.json`;
    link.click();
    link.remove();
    showToast("success", "Exported Audit Trail (JSON)!", "تم تصدير سجل التدقيق بصيغة JSON!");
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="p-5 rounded-2xl border border-border bg-card shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs">
        <div>
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-primary" />
            <h1 className="text-base font-extrabold text-foreground">
              {language === "ar" ? "سجل التدقيق والامتثال الرقابي غير القابل للتعديل" : "Immutable Sovereign Audit Trail"}
            </h1>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            {language === "ar"
              ? "سجل محمي ضد التلاعب لجميع عمليات الاستعراض والتعديل والاعتماد طبقاً للمرسوم الاتحادي 45"
              : "Tamper-evident, write-only logging of every document view, field edit, export, and deletion"}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            className="px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-secondary text-foreground font-bold text-xs flex items-center gap-1.5 shadow-sm transition"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            <span>CSV</span>
          </button>
          <button
            onClick={handleExportJSON}
            className="px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-secondary text-foreground font-bold text-xs flex items-center gap-1.5 shadow-sm transition"
          >
            <FileCode className="w-4 h-4 text-blue-600" />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl border border-border bg-card shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={language === "ar" ? "ابحث في السجل باسم المستخدم أو المستند..." : "Search by user, email, or document..."}
            className="w-full ps-9 pe-4 py-1.5 rounded-lg border border-border bg-secondary/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-border bg-secondary text-foreground text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="all">{language === "ar" ? "كل العمليات" : "All Actions"}</option>
            <option value="DOCUMENT_UPLOAD">Uploads</option>
            <option value="FIELD_CORRECTED">Field Corrections</option>
            <option value="DOCUMENT_APPROVED">Approvals</option>
            <option value="DOCUMENT_REJECTED">Rejections</option>
            <option value="PII_UNMASKED">PII Unmasks</option>
            <option value="DOCUMENT_EXPORTED">Exports</option>
            <option value="DOCUMENT_DELETED">Deletions</option>
          </select>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden text-xs">
        <table className="w-full text-start border-collapse">
          <thead>
            <tr className="border-b border-border bg-secondary/40 text-muted-foreground font-semibold text-[11px] uppercase tracking-wider">
              <th className="p-3 text-start">{language === "ar" ? "الوقت والتاريخ" : "Timestamp (UTC)"}</th>
              <th className="p-3 text-start">{language === "ar" ? "المستخدم" : "Actor"}</th>
              <th className="p-3 text-start">{language === "ar" ? "العملية" : "Action"}</th>
              <th className="p-3 text-start">{language === "ar" ? "المستند" : "Document Ref"}</th>
              <th className="p-3 text-start">{language === "ar" ? "التفاصيل" : "Description"}</th>
              <th className="p-3 text-end">{language === "ar" ? "التفاصيل" : "Diff"}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {filteredLogs.map((entry) => (
              <tr key={entry.id} className="hover:bg-secondary/30 transition-colors">
                <td className="p-3 font-mono text-muted-foreground text-[11px]">
                  {formatDateBilingual(entry.timestamp, language === "ar")}
                </td>
                <td className="p-3 font-semibold text-foreground">
                  <div>{entry.actorName}</div>
                  <div className="text-[10px] text-muted-foreground font-mono">{entry.actorEmail}</div>
                </td>
                <td className="p-3">
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-secondary border border-border text-foreground">
                    {entry.action}
                  </span>
                </td>
                <td className="p-3 font-mono text-foreground font-medium">
                  {entry.documentRef || "—"}
                </td>
                <td className="p-3 text-muted-foreground max-w-sm truncate">
                  {language === "ar" ? entry.detailsAr : entry.detailsEn}
                </td>
                <td className="p-3 text-end">
                  {entry.diff ? (
                    <button
                      onClick={() => setSelectedLog(entry)}
                      className="px-2 py-1 rounded bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 font-bold text-[10px] border border-amber-300 dark:border-amber-800"
                    >
                      View Diff
                    </button>
                  ) : (
                    <span className="text-slate-400 text-[10px]">None</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Diff Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <h3 className="font-bold text-sm text-foreground">Field Modification Diff</h3>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-muted-foreground hover:text-foreground text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 font-mono">
              <div className="p-2.5 rounded bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-300">
                <span className="block text-[10px] uppercase font-bold text-rose-600">Original / Previous:</span>
                <span className="text-xs">{selectedLog.diff?.oldValue}</span>
              </div>

              <div className="p-2.5 rounded bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-300">
                <span className="block text-[10px] uppercase font-bold text-emerald-600">Corrected / Human Verified:</span>
                <span className="text-xs font-bold">{selectedLog.diff?.newValue}</span>
              </div>
            </div>

            <button
              onClick={() => setSelectedLog(null)}
              className="w-full py-2 rounded-lg bg-primary text-primary-foreground font-bold"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
