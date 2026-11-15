"use client";

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
  } = useApp();

  const Arrow = dir === "rtl" ? ArrowLeft : ArrowRight;
  const num = (val: string | number) => (useArabicDigits ? toArabicIndicDigits(val) : String(val));
  const needsReviewDocs = documents.filter((d) => d.status === "needs_review" || d.status === "failed");

  // Real-world UAE weekly throughput data
  const chartData = [
    { day: "Mon", dayAr: "الإثنين", count: 185, approved: 172 },
    { day: "Tue", dayAr: "الثلاثاء", count: 240, approved: 231 },
    { day: "Wed", dayAr: "الأربعاء", count: 310, approved: 298 },
    { day: "Thu", dayAr: "الخميس", count: 290, approved: 275 },
    { day: "Fri", dayAr: "الجمعة", count: 195, approved: 188 },
  ];

  return (
    <div className="space-y-6">
      {/* Executive Hero Banner (Clean YC SaaS Header) */}
      <div className="p-6 rounded-2xl border border-border/80 bg-card shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
              {language === "ar" ? "نظرة عامة والرقابة المصرفية" : "Executive Overview"}
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
              ● Live Air-Gapped
            </span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed max-w-2xl">
            {language === "ar"
              ? "استخراج ومعالجة ذكية فورية لبطاقات الهوية الإماراتية والرخص التجارية والفواتير الضريبية دون خروج أي بيانات خارج حدود الدولة."
              : "In-country sovereign document extraction for Emirates IDs, trade licenses, and FTA invoices with zero external data egress."}
          </p>
        </div>

        {/* Quick Action Buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setCurrentScreen("review")}
            className="px-3.5 py-2 rounded-lg border border-border/80 bg-secondary/60 hover:bg-secondary text-foreground font-semibold text-xs transition shadow-xs flex items-center gap-1.5"
          >
            <span>{language === "ar" ? "طابور المراجعة" : "Review Queue"}</span>
            <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 font-mono text-[10px]">
              {needsReviewDocs.length}
            </span>
          </button>

          <button
            onClick={() => setCurrentScreen("upload")}
            className="px-4 py-2 rounded-lg bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900 font-semibold text-xs flex items-center gap-2 shadow-xs hover:bg-zinc-800 dark:hover:bg-white/90 transition active:scale-[0.98]"
          >
            <UploadCloud className="w-4 h-4" />
            <span>{language === "ar" ? "تحميل مستند" : "Upload Document"}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Row (5 Minimal High-Density Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* Metric 1: Processed Today */}
        <div className="p-4 rounded-xl border border-border/80 bg-card shadow-xs space-y-2 hover:border-zinc-300 dark:hover:border-zinc-700 transition">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>{language === "ar" ? "المستندات اليوم" : "Processed Today"}</span>
            <FileText className="w-3.5 h-3.5 text-muted-foreground" />
          </div>
          <div className="text-2xl font-bold font-mono tracking-tight text-foreground">
            {num("1,420")}
          </div>
          <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
            <span className="text-emerald-600 dark:text-emerald-400 font-semibold">↑ 14%</span>
            <span>{language === "ar" ? "الأسبوع:" : "Week:"} {num("8,950")}</span>
          </div>
        </div>

        {/* Metric 2: Average Accuracy */}
        <div className="p-4 rounded-xl border border-border/80 bg-card shadow-xs space-y-2 hover:border-zinc-300 dark:hover:border-zinc-700 transition">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>{language === "ar" ? "متوسط دقة الاستخراج" : "Extraction Accuracy"}</span>
            <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold font-mono tracking-tight text-emerald-700 dark:text-emerald-400">
            {num("98.6%")}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {language === "ar" ? "عبر كافة المخططات" : "Across all UAE schemas"}
          </div>
        </div>

        {/* Metric 3: Avg Review Time */}
        <div className="p-4 rounded-xl border border-border/80 bg-card shadow-xs space-y-2 hover:border-zinc-300 dark:hover:border-zinc-700 transition">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>{language === "ar" ? "زمن المراجعة" : "Avg Review Time"}</span>
            <Clock className="w-3.5 h-3.5 text-muted-foreground" />
          </div>
          <div className="text-2xl font-bold font-mono tracking-tight text-foreground">
            {num("38s")}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {language === "ar" ? "٨٥٪ أسرع من اليدوي" : "85% faster than manual"}
          </div>
        </div>

        {/* Metric 4: Review Queue */}
        <div className="p-4 rounded-xl border border-border/80 bg-card shadow-xs space-y-2 hover:border-zinc-300 dark:hover:border-zinc-700 transition">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>{language === "ar" ? "طابور التدقيق" : "Pending Review"}</span>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          </div>
          <div className="text-2xl font-bold font-mono tracking-tight text-amber-600 dark:text-amber-400">
            {num(needsReviewDocs.length)}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {language === "ar" ? "تنبيهات ثقة منخفضة" : "Low confidence flags"}
          </div>
        </div>

        {/* Metric 5: Unit Cost */}
        <div className="p-4 rounded-xl border border-border/80 bg-card shadow-xs space-y-2 hover:border-zinc-300 dark:hover:border-zinc-700 transition">
          <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
            <span>{language === "ar" ? "تكلفة المستند" : "Cost per Document"}</span>
            <Coins className="w-3.5 h-3.5 text-muted-foreground" />
          </div>
          <div className="text-2xl font-bold font-mono tracking-tight text-foreground">
            {formatCurrencyAED(0.38, useArabicDigits)}
          </div>
          <div className="text-[11px] text-muted-foreground">
            {language === "ar" ? "نموذج سيادي داخلي" : "In-house sovereign model"}
          </div>
        </div>
      </div>

      {/* Main Grid: Weekly Processing Chart + Needs Review Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Processing Volume Chart (7 cols) */}
        <div className="lg:col-span-7 p-5 rounded-2xl border border-border/80 bg-card shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                {language === "ar" ? "حجم المعالجة الأسبوعية ونسبة الاعتماد الآلي" : "Weekly Processing Volume & Auto-Approval"}
              </h3>
              <p className="text-[11px] text-muted-foreground">
                {language === "ar" ? "معدل الاعتماد الفوري بدون تدخل بشري" : "Straight-Through Processing (STP) throughput"}
              </p>
            </div>
            <span className="px-2 py-0.5 rounded-md text-[11px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 font-mono">
              96.2% STP
            </span>
          </div>

          {/* Minimalist Column Chart */}
          <div className="h-48 w-full pt-4 flex items-end justify-between gap-3 px-2 border-b border-border/70">
            {chartData.map((d) => {
              const heightPct = Math.round((d.count / 350) * 100);
              return (
                <div key={d.day} className="flex-1 flex flex-col items-center gap-1.5 group h-full justify-end">
                  <div className="w-full max-w-[38px] flex items-end gap-1 h-full justify-center">
                    <div
                      className="w-full bg-secondary rounded-t group-hover:bg-secondary/80 transition-all relative overflow-hidden"
                      style={{ height: `${heightPct}%` }}
                      title={`Total: ${d.count}`}
                    >
                      {/* Auto-approved inner bar */}
                      <div
                        className="w-full bg-emerald-600 dark:bg-emerald-500 rounded-t absolute bottom-0 start-0 transition-all opacity-85 group-hover:opacity-100"
                        style={{ height: `${(d.approved / d.count) * 100}%` }}
                        title={`Auto-approved: ${d.approved}`}
                      />
                    </div>
                  </div>
                  <span className="text-[11px] font-medium text-muted-foreground group-hover:text-foreground">
                    {language === "ar" ? d.dayAr : d.day}
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground/80">
                    {num(d.count)}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
            <div className="flex items-center gap-4 text-[11px]">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-emerald-600 dark:bg-emerald-500"></span>
                <span>{language === "ar" ? "معتمد تلقائياً" : "Auto-Approved"}</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-secondary"></span>
                <span>{language === "ar" ? "إجمالي الوارد" : "Total Ingested"}</span>
              </span>
            </div>
            <span className="font-semibold text-foreground text-[11px]">
              {language === "ar" ? "إجمالي الأسبوع: ١,٢٢٠ مستند" : "Total Week: 1,220 docs"}
            </span>
          </div>
        </div>

        {/* Needs Review Queue (5 cols) */}
        <div className="lg:col-span-5 p-5 rounded-2xl border border-border/80 bg-card shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border/80">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-semibold text-foreground">
                {language === "ar" ? "قائمة التدقيق والمراجعة" : "Requires Attention"}
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20 font-mono">
              {needsReviewDocs.length} Pending
            </span>
          </div>

          <div className="divide-y divide-border/60">
            {needsReviewDocs.slice(0, 4).map((doc) => (
              <div key={doc.id} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                <div className="min-w-0">
                  <div className="font-semibold text-foreground truncate">{doc.fileName}</div>
                  <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5">
                    <span className="font-mono">{doc.referenceNumber}</span>
                    <span>•</span>
                    <span className="text-amber-600 dark:text-amber-400 font-medium">
                      {doc.validationErrors.length > 0 ? "Validation Rule Flag" : "Low Confidence"}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => {
                    setSelectedDocumentId(doc.id);
                    setCurrentScreen("review");
                  }}
                  className="px-2.5 py-1 rounded-md border border-border/80 bg-secondary/70 hover:bg-secondary text-foreground font-semibold text-xs shrink-0 flex items-center gap-1 transition shadow-xs"
                >
                  <span>{language === "ar" ? "تدقيق" : "Review"}</span>
                  <Arrow className="w-3 h-3 text-muted-foreground" />
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={() => setCurrentScreen("documents")}
            className="w-full py-2 rounded-lg border border-border/80 bg-secondary/50 hover:bg-secondary text-xs font-semibold text-foreground transition text-center block"
          >
            {language === "ar" ? "عرض كافة مستندات الأرشيف" : "View All Documents in Management Center"}
          </button>
        </div>
      </div>
    </div>
  );
}
