import React from "react";
import { useApp } from "@/context/AppContext";
import { toArabicIndicDigits, formatCurrencyAED } from "@/lib/utils";
import {
  FileText,
  Clock,
  AlertTriangle,
  Coins,
  TrendingUp,
  UploadCloud,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";

export function DashboardScreen() {
  const {
    documents,
    setSelectedDocumentId,
    setCurrentScreen,
    useArabicDigits,
    language,
    dir,
    t,
  } = useApp();

  const Arrow = dir === "rtl" ? ArrowLeft : ArrowRight;

  const num = (val: string | number) => (useArabicDigits ? toArabicIndicDigits(val) : String(val));

  const needsReviewDocs = documents.filter((d) => d.status === "needs_review" || d.status === "failed");

  // Chart data for UAE working week (Monday to Friday or Sunday to Thursday)
  const chartData = [
    { day: "Mon", dayAr: "الإثنين", count: 185, approved: 172 },
    { day: "Tue", dayAr: "الثلاثاء", count: 240, approved: 231 },
    { day: "Wed", dayAr: "الأربعاء", count: 310, approved: 298 },
    { day: "Thu", dayAr: "الخميس", count: 290, approved: 275 },
    { day: "Fri", dayAr: "الجمعة", count: 195, approved: 188 },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-emerald-950 via-emerald-900 to-slate-900 text-white shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4 border border-emerald-800/40">
        <div className="space-y-1.5">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-800/80 text-emerald-200 border border-emerald-600/40">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>UAE Sovereign Document Intelligence • Bank Tier 1</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight">
            {language === "ar" ? "لوحة تحكم ذكاء المستندات والرقابة المصرفية" : "Document Intelligence & Compliance Dashboard"}
          </h1>
          <p className="text-xs text-emerald-200/80 leading-relaxed max-w-xl">
            {language === "ar"
              ? "معالجة فورية محلية لبطاقات الهوية الإماراتية والرخص التجارية والفواتير الضريبية دون إخراج أي بيانات خارج الدولة."
              : "In-country real-time extraction for Emirates IDs, trade licenses, and tax invoices with zero external data egress."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentScreen("upload")}
            className="px-4 py-2 rounded-xl bg-gold hover:bg-gold-muted text-slate-950 font-bold text-xs flex items-center gap-2 shadow-md transition"
          >
            <UploadCloud className="w-4 h-4" />
            <span>{t("navUpload")}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Metric 1: Today / Week Volume */}
        <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold">
            <span>{language === "ar" ? "المستندات اليوم" : "Processed Today"}</span>
            <FileText className="w-4 h-4 text-primary" />
          </div>
          <div className="text-2xl font-black font-mono text-foreground">
            {num("1,420")}
          </div>
          <div className="text-[11px] text-muted-foreground flex items-center gap-1">
            <span className="text-emerald-700 dark:text-emerald-400 font-bold">↑ 14%</span>
            <span>{language === "ar" ? "هذا الأسبوع:" : "This week:"} {num("8,950")}</span>
          </div>
        </div>

        {/* Metric 2: Average Accuracy */}
        <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold">
            <span>{language === "ar" ? "متوسط الدقة" : "Avg Extraction Accuracy"}</span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black font-mono text-emerald-800 dark:text-emerald-400">
            {num("98.6%")}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {language === "ar" ? "عبر كافة المخططات" : "Across all UAE schemas"}
          </div>
        </div>

        {/* Metric 3: Avg Review Time */}
        <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold">
            <span>{language === "ar" ? "زمن المراجعة" : "Avg Review Time"}</span>
            <Clock className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black font-mono text-foreground">
            {num("38s")}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {language === "ar" ? "انخفاض ٨٥٪ عن اليدوي" : "85% faster than manual"}
          </div>
        </div>

        {/* Metric 4: Queue Size */}
        <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold">
            <span>{language === "ar" ? "طابور المراجعة" : "Review Queue"}</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-black font-mono text-amber-700 dark:text-amber-400">
            {num(needsReviewDocs.length)}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {language === "ar" ? "حقول ذات ثقة منخفضة" : "Low confidence flags"}
          </div>
        </div>

        {/* Metric 5: Cost per Doc */}
        <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-semibold">
            <span>{language === "ar" ? "تكلفة المستند" : "Cost per Document"}</span>
            <Coins className="w-4 h-4 text-gold" />
          </div>
          <div className="text-2xl font-black font-mono text-foreground">
            {formatCurrencyAED(0.38, useArabicDigits)}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {language === "ar" ? "وفورات بنسبة ٩٠٪" : "Sovereign in-house model"}
          </div>
        </div>
      </div>

      {/* Middle Row: Processing Chart + Quick Triage Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Processing Volume Chart (7 cols) */}
        <div className="lg:col-span-7 p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-foreground">
                {language === "ar" ? "حجم المعالجة الأسبوعية ونسبة الاعتماد" : "Weekly Processing Volume & Auto-Approval"}
              </h3>
              <p className="text-[11px] text-muted-foreground">
                {language === "ar" ? "أداء الأسبوع الحالي لخط الأنابيب السيادي" : "Throughput vs human reviewer intervention"}
              </p>
            </div>
            <span className="text-[11px] font-bold text-emerald-700 dark:text-emerald-400 font-mono">
              96.2% STP Rate
            </span>
          </div>

          {/* Simulated SVG Bar Chart */}
          <div className="h-52 w-full pt-4 flex items-end justify-between gap-3 px-2 border-b border-border">
            {chartData.map((d) => {
              const heightPct = Math.round((d.count / 350) * 100);
              return (
                <div key={d.day} className="flex-1 flex flex-col items-center gap-1.5 group h-full justify-end">
                  <div className="w-full max-w-[42px] flex items-end gap-1 h-full justify-center">
                    {/* Total Bar */}
                    <div
                      className="w-full bg-primary/20 dark:bg-primary/30 rounded-t group-hover:bg-primary/40 transition-all relative"
                      style={{ height: `${heightPct}%` }}
                      title={`Total: ${d.count}`}
                    >
                      {/* Approved Inner Bar */}
                      <div
                        className="w-full bg-primary rounded-t absolute bottom-0 start-0 transition-all"
                        style={{ height: `${(d.approved / d.count) * 100}%` }}
                        title={`Auto-approved: ${d.approved}`}
                      />
                    </div>
                  </div>
                  <span className="text-[11px] font-bold text-muted-foreground group-hover:text-foreground">
                    {language === "ar" ? d.dayAr : d.day}
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {num(d.count)}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-primary"></span>
                <span>{language === "ar" ? "معتمد تلقائياً" : "Auto-Approved"}</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-primary/30"></span>
                <span>{language === "ar" ? "إجمالي الوارد" : "Total Ingested"}</span>
              </span>
            </div>
            <span className="font-semibold text-foreground">
              {language === "ar" ? "إجمالي الأسبوع: ١,٢٢٠ مستند" : "Total Week: 1,220 docs"}
            </span>
          </div>
        </div>

        {/* Needs Review Triage (5 cols) */}
        <div className="lg:col-span-5 p-5 rounded-2xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-bold text-foreground">
                {language === "ar" ? "يتطلب مراجعة بشرية" : "Needs Review Queue"}
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300">
              {needsReviewDocs.length} Pending
            </span>
          </div>

          <div className="divide-y divide-border/60">
            {needsReviewDocs.map((doc) => (
              <div key={doc.id} className="py-3 flex items-center justify-between gap-3 text-xs">
                <div className="min-w-0">
                  <div className="font-bold text-foreground truncate">{doc.fileName}</div>
                  <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5">
                    <span>{doc.referenceNumber}</span>
                    <span>•</span>
                    <span className="text-amber-600 dark:text-amber-400 font-semibold">
                      {doc.validationErrors.length > 0 ? "Validation Warning" : "Low Confidence"}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => {
                    setSelectedDocumentId(doc.id);
                    setCurrentScreen("review");
                  }}
                  className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground font-bold hover:bg-primary/90 text-xs shrink-0 flex items-center gap-1 transition shadow-sm"
                >
                  <span>{language === "ar" ? "تدقيق" : "Review"}</span>
                  <Arrow className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={() => setCurrentScreen("documents")}
            className="w-full py-2 rounded-lg border border-border bg-secondary hover:bg-secondary/80 font-bold text-xs text-foreground transition text-center block"
          >
            {language === "ar" ? "عرض كافة مستندات الأرشيف" : "View All Documents in Archive"}
          </button>
        </div>
      </div>
    </div>
  );
}
